"""Phase 1 LLM agent: conversation history + structured actions + commerce_ops execution."""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commerce import Invoice
from app.models.store import Product, Store, Transaction
from app.services import chat_session
from app.services.commerce_ops import (
    SaleLine,
    adjust_product_stock,
    apply_batch_sale,
    create_customer_record,
    create_invoice_for_customer,
    create_invoice_from_transactions,
    create_vendor_record,
    fuzzy_match_entity,
    record_invoice_payment,
)
from app.services.llm import chat_json_messages

READ_ACTIONS = frozenset({
    "none", "chat", "greeting", "help", "cancel",
    "low_stock", "today_sales", "weekly_sales", "top_sellers",
    "unpaid_invoices", "customers", "vendors", "purchases", "stock_advice",
    "generate_report", "sales_report", "inventory_report", "gst_summary", "revenue_summary",
})

WRITE_ACTIONS = frozenset({
    "create_bill", "record_sale", "pay_invoice", "adjust_stock",
    "add_customer", "add_vendor", "bill_last_sale",
})

SYSTEM_PROMPT = """You are ShelfMind, a friendly store assistant for a neighborhood shop in India.
You help with bills, sales, stock, customers, and stocking advice. Speak naturally and concisely.

Use conversation history and agent_state to understand follow-ups like "add bread too", "bill Rajesh instead", or "2 milk".

Return JSON only with this schema:
{
  "reply": "natural language response to the user",
  "action": "none|chat|greeting|help|cancel|create_bill|record_sale|pay_invoice|adjust_stock|add_customer|add_vendor|bill_last_sale|low_stock|today_sales|weekly_sales|top_sellers|unpaid_invoices|customers|vendors|stock_advice|generate_report",
  "params": {
    "customer_id": null,
    "customer_name": "",
    "lines": [{"product_name": "", "product_id": null, "quantity": 1}],
    "product_name": "",
    "product_id": null,
    "quantity": 1,
    "delta": 0,
    "invoice_id": null,
    "invoice_number": "",
    "method": "cash",
    "name": "",
    "segment": "Regular",
    "vendor_name": "",
    "report_type": "overview|sales|inventory|top_products|customers|invoices|categories|purchases|gst",
    "period": "today|week|month|year|all",
    "days": null,
    "category": ""
  },
  "state": null,
  "status": "complete|needs_input",
  "missing": []
}

Rules:
- action=none or chat for casual conversation (hi, thanks, unclear).
- Use create_bill when user wants an invoice; include customer_name or customer_id and lines with quantity+product_name.
- Default quantity to 1 if user names a product without a number.
- Merge new info into state when status=needs_input; put partial task in state.
- action=cancel clears the task.
- Use read actions (low_stock, today_sales, etc.) for quick queries.
- Use generate_report when user asks for a report, summary, or analytics from store data.
  report_type: sales, inventory, top_products, customers, invoices, categories, purchases, gst, overview.
  period: today, week, month, year, all — or set days for custom range.
- stock_advice for forecasting / what to order questions.
- Do NOT invent product or customer IDs; use names from store context.
- When switching customer mid-flow, update params and state accordingly.
- Keep reply friendly; mention invoice numbers and totals when actions succeed (execution layer adds details)."""


def _store_prompt_context(ctx: Any, session: dict, store_name: str) -> str:
    agent_state = session.get("agent_state")
    return json.dumps(
        {
            "store_name": store_name,
            "customers": [{"id": i, "name": n} for i, n in ctx.customers[:25]],
            "products": [{"id": i, "name": n} for i, n in ctx.products[:25]],
            "vendors": [{"id": i, "name": n} for i, n in ctx.vendors[:15]],
            "agent_state": agent_state,
        },
        indent=2,
    )


def _history_messages(session: dict) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = []
    for turn in (session.get("history") or [])[-8:]:
        role = "assistant" if turn.get("role") == "bot" else "user"
        text = turn.get("text") or ""
        if text:
            msgs.append({"role": role, "content": text})
    return msgs


def _resolve_customer_id(params: dict, ctx: Any) -> tuple[int | None, list[tuple[int, str]]]:
    if params.get("customer_id"):
        try:
            return int(params["customer_id"]), []
        except (TypeError, ValueError):
            pass
    name = (params.get("customer_name") or params.get("name") or "").strip()
    if not name:
        return None, []
    matches = fuzzy_match_entity(name, ctx.customers)
    if len(matches) == 1:
        return matches[0][0], []
    return None, matches


def _resolve_lines(params: dict, ctx: Any, message: str = "") -> list[SaleLine]:
    raw = params.get("lines") or []
    if not raw and params.get("product_name"):
        raw = [{
            "product_name": params.get("product_name"),
            "product_id": params.get("product_id"),
            "quantity": params.get("quantity") or 1,
        }]
    lines: list[SaleLine] = []
    for ln in raw:
        if not isinstance(ln, dict):
            continue
        qty = int(ln.get("quantity") or ln.get("qty") or 1)
        pid = ln.get("product_id")
        if pid:
            lines.append(SaleLine(product_id=int(pid), quantity=max(1, qty)))
            continue
        name = (ln.get("product_name") or ln.get("name") or "").strip()
        if name:
            matches = fuzzy_match_entity(name, ctx.products)
            if matches:
                lines.append(SaleLine(product_id=matches[0][0], quantity=max(1, qty)))
    if not lines and message:
        from app.services.chat_agent import _parse_qty_product_lines

        lines = _parse_qty_product_lines(message, ctx)
    return lines


def _resolve_product_id(params: dict, ctx: Any) -> int | None:
    if params.get("product_id"):
        return int(params["product_id"])
    name = (params.get("product_name") or "").strip()
    if name:
        matches = fuzzy_match_entity(name, ctx.products)
        if matches:
            return matches[0][0]
    return None


async def _resolve_invoice(db: AsyncSession, store_id: int, params: dict) -> Invoice | None:
    if params.get("invoice_id"):
        inv = (
            await db.execute(
                select(Invoice).where(Invoice.id == int(params["invoice_id"]), Invoice.store_id == store_id)
            )
        ).scalar_one_or_none()
        if inv:
            return inv
    num = (params.get("invoice_number") or "").strip()
    if num:
        if not num.upper().startswith("INV"):
            num = f"INV-{num}"
        inv = (
            await db.execute(
                select(Invoice).where(Invoice.store_id == store_id, Invoice.invoice_number.ilike(f"%{num}%"))
            )
        ).scalar_one_or_none()
        return inv
    return None


def _suggestions_for_missing(missing: list[str], ctx: Any, params: dict) -> list[dict]:
    from app.services.chat_agent import _customer_suggestions, _product_suggestions

    if "customer_name" in missing or "customer" in missing:
        name = (params.get("customer_name") or "").strip()
        if name:
            matches = fuzzy_match_entity(name, ctx.customers)
            return [{"label": n, "value": f"customer:{i}", "command": f"bill for {n}"} for i, n in matches[:5]]
        return _customer_suggestions(ctx)
    if "products" in missing or "lines" in missing:
        return [
            {"label": "Bill last sale", "value": "bill_last_sale", "command": "bill last sale"},
            *_product_suggestions(ctx, 5),
        ]
    return _product_suggestions(ctx, 6)


async def _execute_read_action(
    db: AsyncSession,
    store_id: int,
    action: str,
    message: str,
    ctx: Any,
    params: dict | None = None,
    reply: str = "",
) -> Any:
    from datetime import datetime, timedelta, timezone

    from app.services.chat_agent import AgentResponse, _handle_read_intent

    if action in ("low_stock", "today_sales", "weekly_sales", "top_sellers", "unpaid_invoices", "customers", "vendors", "help", "greeting"):
        resp = await _handle_read_intent(db, store_id, action, message, ctx, params or {})
        if resp:
            return resp

    if action in ("generate_report", "sales_report", "inventory_report", "gst_summary", "revenue_summary"):
        from app.services.store_reports import generate_store_report, report_to_agent_data

        report_params = dict(params or {})
        if action == "sales_report" or action == "revenue_summary":
            report_params.setdefault("report_type", "sales")
        elif action == "inventory_report":
            report_params.setdefault("report_type", "inventory")
        elif action == "gst_summary":
            report_params.setdefault("report_type", "gst")

        customer_id, _ = _resolve_customer_id(report_params, ctx)
        report = await generate_store_report(db, store_id, message, report_params, customer_id=customer_id)
        data = report_to_agent_data(report)
        return AgentResponse(
            reply=reply or report.get("summary", "Here's your report."),
            intent="generate_report",
            session_id="",
            data=data,
            actions=[{"label": "Reports", "href": "/store/reports"}],
        )

    if action == "stock_advice":
        from app.services.nl_query import process_nl_query

        result = await process_nl_query(db, message, store_id)
        recs = result.get("recommendations", [])
        summary = "; ".join(f"{r['product_name']}: {r['action']}" for r in recs[:3]) if recs else "No specific recommendations right now."
        return AgentResponse(
            reply=f"Here's my stocking advice: {summary}",
            intent="ai_recommendation",
            session_id="",
            data=result,
            actions=[{"label": "View Demand Planner", "href": "/store/insights"}],
        )

    return None


async def _execute_write_action(
    db: AsyncSession,
    store_id: int,
    action: str,
    params: dict,
    ctx: Any,
    message: str,
) -> tuple[str, str, dict | None]:
    """Returns (intent, reply_suffix, result). Raises HTTPException on hard failures."""

    if action in ("create_bill", "bill_last_sale"):
        customer_id, amb = _resolve_customer_id(params, ctx)
        if amb:
            raise ValueError("ambiguous_customer")
        if action == "bill_last_sale" and customer_id:
            txn = (
                await db.execute(
                    select(Transaction.id)
                    .where(Transaction.store_id == store_id, Transaction.customer_id == customer_id)
                    .order_by(Transaction.sold_at.desc())
                    .limit(5)
                )
            ).scalars().all()
            if not txn:
                raise ValueError("no_recent_sales")
            inv = await create_invoice_from_transactions(db, store_id, list(txn), customer_id)
            return (
                "create_bill",
                f"Created bill {inv.invoice_number} — Rs {inv.total:,.2f} (from recent sales).",
                {"invoice_id": inv.id, "invoice_number": inv.invoice_number, "total": inv.total},
            )
        lines = _resolve_lines(params, ctx, message)
        if not lines:
            raise ValueError("missing_lines")
        result = await create_invoice_for_customer(db, store_id, customer_id, lines)
        cust = next((n for i, n in ctx.customers if i == customer_id), "Walk-in") if customer_id else "Walk-in"
        return (
            "create_bill",
            f"Done! Bill {result['invoice_number']} for {cust} — Rs {result['total']:,.2f} (GST included).",
            result,
        )

    if action == "record_sale":
        customer_id, _ = _resolve_customer_id(params, ctx)
        lines = _resolve_lines(params, ctx, message)
        if not lines:
            raise ValueError("missing_lines")
        txn_ids, total = await apply_batch_sale(db, store_id, lines, customer_id)
        await db.commit()
        return (
            "record_sale",
            f"Sale recorded — Rs {total:,.2f} for {len(lines)} item(s).",
            {"transaction_ids": txn_ids, "total": total},
        )

    if action == "pay_invoice":
        method = (params.get("method") or "cash").lower()
        inv = await _resolve_invoice(db, store_id, params)
        if not inv:
            raise ValueError("missing_invoice")
        result = await record_invoice_payment(db, store_id, inv.id, inv.total, method)
        return (
            "pay_invoice",
            f"Payment recorded for {result['invoice_number']} via {method}. Status: {result['status']}.",
            result,
        )

    if action == "adjust_stock":
        delta = params.get("delta")
        if delta is None:
            m = message.lower()
            add = re.search(r"\b(add|increase)\s+(\d+)", m)
            rem = re.search(r"\b(remove|decrease)\s+(\d+)", m)
            if add:
                delta = int(add.group(2))
            elif rem:
                delta = -int(rem.group(2))
        if delta is None:
            raise ValueError("missing_delta")
        pid = _resolve_product_id(params, ctx)
        if not pid:
            raise ValueError("missing_product")
        result = await adjust_product_stock(db, store_id, pid, int(delta))
        return (
            "adjust_stock",
            f"Updated {result['product_name']} stock to {result['stock_on_hand']} units.",
            result,
        )

    if action == "add_customer":
        name = (params.get("name") or params.get("customer_name") or "").strip()
        if not name:
            raise ValueError("missing_name")
        segment = params.get("segment") or "Regular"
        result = await create_customer_record(db, store_id, name, segment=segment)
        return ("add_customer", f"Added customer {result['name']} ({result['segment']}).", result)

    if action == "add_vendor":
        name = (params.get("vendor_name") or params.get("name") or "").strip()
        if not name:
            raise ValueError("missing_name")
        result = await create_vendor_record(db, store_id, name)
        return ("add_vendor", f"Added vendor {result['name']}.", result)

    raise ValueError("unknown_action")


def _merge_params(params: dict, session: dict) -> dict:
    """Merge persisted agent_state into LLM params for follow-up turns."""
    state = session.get("agent_state")
    if not isinstance(state, dict):
        return dict(params)
    merged = {k: v for k, v in state.items() if k != "task"}
    merged.update(params)
    if state.get("lines") and not params.get("lines"):
        merged["lines"] = state["lines"]
    if state.get("customer_name") and not params.get("customer_name") and not params.get("customer_id"):
        merged["customer_name"] = state["customer_name"]
    if state.get("customer_id") and not params.get("customer_id"):
        merged["customer_id"] = state["customer_id"]
    return merged


async def run_turn(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: Any,
    message: str,
) -> Any | None:
    """Run one LLM agent turn. Returns AgentResponse or None to fall back to rules."""
    from app.config import get_settings
    from app.services.chat_agent import AgentResponse

    if not get_settings().llm_api_key:
        return None

    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    store_name = store.name if store else "your store"

    context_block = _store_prompt_context(ctx, session, store_name)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Store context:\n{context_block}"},
        *_history_messages(session),
        {"role": "user", "content": message},
    ]

    fallback = {"reply": "", "action": "none", "params": {}, "state": session.get("agent_state"), "status": "complete", "missing": []}
    parsed = chat_json_messages(messages, fallback)
    if not parsed.get("reply") and parsed.get("action") in (None, "none", ""):
        return None

    action = (parsed.get("action") or "none").lower().replace("-", "_")
    raw_params = parsed.get("params") or {}
    if not isinstance(raw_params, dict):
        raw_params = {}
    params = _merge_params(raw_params, session)
    status = parsed.get("status") or "complete"
    missing = parsed.get("missing") or []
    state = parsed.get("state")
    reply = (parsed.get("reply") or "").strip()

    if action == "cancel":
        session["agent_state"] = None
        session["pending_action"] = None
        session["slots"] = {}
        chat_session.save_session(store_id, user_id, sid, session)
        return AgentResponse(
            reply=reply or "Cancelled. What would you like to do next?",
            intent="cancel",
            session_id=sid,
            status="complete",
            actions=[{"label": "Help", "command": "help"}],
        )

    if action in READ_ACTIONS:
        read_resp = await _execute_read_action(db, store_id, action, message, ctx, params, reply)
        if read_resp:
            session["agent_state"] = None
            session["pending_action"] = None
            session["slots"] = {}
            read_resp.reply = reply or read_resp.reply
            read_resp.session_id = sid
            chat_session.save_session(store_id, user_id, sid, session)
            return read_resp
        if action in ("none", "chat", "greeting", "help"):
            session["agent_state"] = state if status == "needs_input" else None
            chat_session.save_session(store_id, user_id, sid, session)
            return AgentResponse(
                reply=reply or "How can I help with your store today?",
                intent=action if action != "chat" else "general",
                session_id=sid,
                status=status if status in ("complete", "needs_input") else "complete",
                missing=missing or None,
                actions=[
                    {"label": "Help", "command": "help"},
                    {"label": "Today's sales", "command": "today's sales"},
                    {"label": "Make bill", "command": "make bill for"},
                ],
            )

    if action in WRITE_ACTIONS:
        try:
            intent, exec_reply, result = await _execute_write_action(db, store_id, action, params, ctx, message)
            session["agent_state"] = None
            session["pending_action"] = None
            session["slots"] = {}
            chat_session.save_session(store_id, user_id, sid, session)
            final_reply = reply if reply and result else exec_reply
            if reply and result and reply not in exec_reply:
                final_reply = f"{reply} {exec_reply}"
            actions = [{"label": "View Billing", "href": "/store/billing"}] if intent == "create_bill" else None
            if intent == "record_sale":
                actions = [{"label": "View Sales", "href": "/store/sales"}]
            return AgentResponse(
                reply=final_reply,
                intent=intent,
                session_id=sid,
                status="complete",
                result=result,
                actions=actions,
            )
        except ValueError as e:
            code = str(e)
            if code == "ambiguous_customer":
                _, amb = _resolve_customer_id(params, ctx)
                missing = ["customer_name"]
                status = "needs_input"
                state = {"task": action, **params}
                suggestions = [{"label": n, "value": f"customer:{i}", "command": f"bill for {n}"} for i, n in amb[:5]]
                session["agent_state"] = state
                chat_session.save_session(store_id, user_id, sid, session)
                return AgentResponse(
                    reply=reply or "Which customer did you mean?",
                    intent=action,
                    session_id=sid,
                    status="needs_input",
                    missing=missing,
                    suggestions=suggestions,
                )
            if code in ("missing_lines", "missing_name", "missing_product", "missing_delta", "missing_invoice"):
                missing = code.replace("missing_", "")
                state = {"task": action, **params}
                session["agent_state"] = state
                chat_session.save_session(store_id, user_id, sid, session)
                return AgentResponse(
                    reply=reply or "I need a bit more detail to complete that.",
                    intent=action,
                    session_id=sid,
                    status="needs_input",
                    missing=[missing],
                    suggestions=_suggestions_for_missing([missing], ctx, params),
                )
            if code == "no_recent_sales":
                return AgentResponse(
                    reply=reply or "No recent sales found for that customer to bill.",
                    intent=action,
                    session_id=sid,
                    status="needs_input",
                )
        except HTTPException as exc:
            return AgentResponse(
                reply=reply or str(exc.detail),
                intent=action,
                session_id=sid,
                status="needs_input",
            )

    session["agent_state"] = state if state is not None else {"task": action, **params}
    session["pending_action"] = None
    session["slots"] = {}
    chat_session.save_session(store_id, user_id, sid, session)
    return AgentResponse(
        reply=reply or "Could you share a few more details?",
        intent=action if action not in ("none", "chat") else "general",
        session_id=sid,
        status="needs_input" if status == "needs_input" or missing else "complete",
        missing=missing or None,
        suggestions=_suggestions_for_missing(missing, ctx, params) if missing else None,
    )
