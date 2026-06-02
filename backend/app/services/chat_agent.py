"""Multi-turn store chat agent: parse intents, fill slots, execute operations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commerce import Customer, Invoice, Payment, PurchaseOrder, Vendor
from app.models.store import Product, Store, Transaction
from app.services import chat_session
from app.services.commerce_ops import (
    SaleLine,
    adjust_product_stock,
    apply_batch_sale,
    apply_sale,
    create_customer_record,
    create_invoice_for_customer,
    create_invoice_from_transactions,
    create_purchase_order,
    create_vendor_record,
    fuzzy_match_entity,
    record_invoice_payment,
    receive_purchase_order,
    update_customer_spend,
)
from app.services.llm import chat_json

ChatStatus = Literal["complete", "needs_input", "confirm"]


@dataclass
class AgentResponse:
    reply: str
    intent: str
    session_id: str
    status: ChatStatus = "complete"
    missing: list[str] | None = None
    suggestions: list[dict] | None = None
    result: dict | None = None
    data: dict | None = None
    actions: list[dict] | None = None


@dataclass
class StoreContext:
    customers: list[tuple[int, str]] = field(default_factory=list)
    products: list[tuple[int, str]] = field(default_factory=list)
    vendors: list[tuple[int, str]] = field(default_factory=list)
    product_map: dict[int, Product] = field(default_factory=dict)


async def load_store_context(db: AsyncSession, store_id: int) -> StoreContext:
    customers = (
        await db.execute(select(Customer.id, Customer.name).where(Customer.store_id == store_id).order_by(Customer.name))
    ).all()
    products = (
        await db.execute(select(Product).where(Product.store_id == store_id).order_by(Product.name))
    ).scalars().all()
    vendors = (
        await db.execute(select(Vendor.id, Vendor.name).where(Vendor.store_id == store_id).order_by(Vendor.name))
    ).all()
    return StoreContext(
        customers=[(c.id, c.name) for c in customers],
        products=[(p.id, p.name) for p in products],
        vendors=[(v.id, v.name) for v in vendors],
        product_map={p.id: p for p in products},
    )


def _append_history(session: dict, role: str, text: str) -> None:
    session["history"] = (session.get("history") or [])[-5:] + [{"role": role, "text": text}]


def _parse_qty_product_lines(text: str, ctx: StoreContext) -> list[SaleLine]:
    """Parse patterns like '2 milk', '2 milk and 1 bread'."""
    lines: list[SaleLine] = []
    parts = re.split(r"\band\b|,|\+", text.lower())
    for part in parts:
        part = part.strip()
        m = re.search(r"(\d+)\s+(.+)", part)
        if not m:
            continue
        qty = int(m.group(1))
        name = m.group(2).strip()
        name = re.sub(r"\s+(for|to)\s+.*$", "", name).strip()
        matches = fuzzy_match_entity(name, ctx.products)
        if matches:
            lines.append(SaleLine(product_id=matches[0][0], quantity=qty))
    return lines


def _resolve_sale_lines(raw_lines: list, message: str, ctx: StoreContext) -> list[SaleLine]:
    """Normalize slot/LLM line dicts into SaleLine objects."""
    resolved: list[SaleLine] = []
    for ln in raw_lines or []:
        if isinstance(ln, SaleLine):
            resolved.append(ln)
            continue
        if not isinstance(ln, dict):
            continue
        qty = int(ln.get("quantity") or ln.get("qty") or 0)
        if qty <= 0:
            continue
        product_id = ln.get("product_id")
        if product_id:
            resolved.append(SaleLine(product_id=int(product_id), quantity=qty))
            continue
        name = ln.get("product_name") or ln.get("name") or ln.get("product")
        if name:
            matches = fuzzy_match_entity(str(name), ctx.products)
            if matches:
                resolved.append(SaleLine(product_id=matches[0][0], quantity=qty))
    if not resolved:
        resolved = _parse_qty_product_lines(message, ctx)
    return resolved


def _parse_intent_rules(msg: str) -> tuple[str, dict[str, Any]]:
    m = msg.lower().strip()

    if m in ("yes", "confirm", "ok", "proceed", "do it"):
        return "confirm", {}
    if m in ("no", "cancel", "stop", "nevermind", "never mind"):
        return "cancel", {}

    if m.startswith("customer:"):
        try:
            return "create_bill", {"customer_id": int(m.split(":", 1)[1])}
        except ValueError:
            pass
    if m.startswith("invoice:"):
        try:
            return "pay_invoice", {"invoice_id": int(m.split(":", 1)[1])}
        except ValueError:
            pass
    if m in ("bill_last_sale", "bill last sale"):
        return "create_bill", {"bill_last_sale": True}

    if any(w in m for w in ["make bill", "create bill", "generate bill", "new bill", "create invoice", "bill for", "bill her", "bill his", "bill their", "bill last sale", "bill recent"]):
        slots = _extract_name_after(msg, ["for", "to"])
        if "bill last sale" in m:
            slots["bill_last_sale"] = True
        return "create_bill", slots

    if any(w in m for w in ["sell ", "record sale", "add sale", "complete sale"]):
        return "record_sale", {}

    if any(w in m for w in ["mark ", "pay ", "record payment", "paid via", "paid with"]):
        return "pay_invoice", {}

    if any(w in m for w in ["add stock", "adjust stock", "stock of", "add to stock", "increase stock", "decrease stock", "remove stock"]):
        return "adjust_stock", {}

    if re.search(r"\b(add|increase|remove|decrease)\s+\d+", m):
        return "adjust_stock", {}

    if any(w in m for w in ["add customer", "new customer", "add regular", "new regular"]):
        return "add_customer", {}

    if any(w in m for w in ["add vendor", "new vendor", "new supplier"]):
        return "add_vendor", {}

    if any(w in m for w in ["receive po", "receive purchase", "receive order"]):
        return "receive_po", {}

    if any(w in m for w in ["purchase order", "create po", "order from", "order "]):
        return "create_po", {}

    if any(w in m for w in ["low stock", "restock", "out of stock", "running low"]):
        return "low_stock", {}

    if any(w in m for w in ["today sale", "today's sale", "sales today", "today revenue"]):
        return "today_sales", {}

    if any(w in m for w in ["weekly sale", "week sale", "this week", "weekly revenue"]):
        return "weekly_sales", {}

    if any(w in m for w in ["top seller", "best seller", "most sold"]):
        return "top_sellers", {}

    if any(w in m for w in ["report", "summary", "analytics"]):
        return "generate_report", {}

    if any(w in m for w in ["sales report", "revenue report"]):
        return "generate_report", {"report_type": "sales"}

    if any(w in m for w in ["inventory report", "stock report"]):
        return "generate_report", {"report_type": "inventory"}

    if any(w in m for w in ["customer report", "regulars report"]):
        return "generate_report", {"report_type": "customers"}

    if any(w in m for w in ["invoice report", "billing report"]):
        return "generate_report", {"report_type": "invoices"}

    if any(w in m for w in ["gst report", "tax report"]):
        return "generate_report", {"report_type": "gst"}

    if any(w in m for w in ["store overview", "business summary", "full report"]):
        return "generate_report", {"report_type": "overview"}

    if any(w in m for w in ["unpaid", "pending bill", "overdue", "outstanding"]):
        return "unpaid_invoices", {}

    if any(w in m for w in ["gst", "tax summary", "cgst", "sgst"]):
        return "gst_summary", {}

    if any(w in m for w in ["revenue", "profit", "earnings", "p&l"]):
        return "revenue_summary", {}

    if any(w in m for w in ["customer", "regulars", "top customer"]):
        return "customers", {}

    if any(w in m for w in ["vendor", "supplier"]):
        return "vendors", {}

    if any(w in m for w in ["purchase orders", "po status"]):
        return "purchases", {}

    if any(w in m for w in ["stock check", "check stock", "inventory level"]):
        return "stock_check", {}

    if any(w in m for w in ["help", "command", "what can you do", "menu"]):
        return "help", {}

    if any(w in m for w in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]):
        return "greeting", {}

    return "general", {}


READ_INTENTS = frozenset({
    "low_stock", "today_sales", "weekly_sales", "top_sellers", "unpaid_invoices",
    "gst_summary", "revenue_summary", "customers", "vendors", "purchases", "stock_check",
    "generate_report", "help", "greeting",
})

WRITE_INTENTS = frozenset({
    "create_bill", "record_sale", "pay_invoice", "adjust_stock",
    "add_customer", "add_vendor", "create_po", "receive_po",
})

SESSION_BREAK_INTENTS = READ_INTENTS | frozenset({"cancel"})


def _is_advice_question(msg: str) -> bool:
    """True only for stocking / demand questions — not greetings or commands."""
    m = msg.lower().strip()
    if m in ("hi", "hello", "hey", "help", "thanks", "thank you", "ok", "okay"):
        return False
    if "?" in msg:
        return True
    advice_kw = [
        "stock for", "should i stock", "what to stock", "what should i",
        "recommend", "forecast", "monsoon", "weekend", "spike", "demand",
        "peer", "compare", "restock", "order more", "need to order",
        "beverages need", "items will", "what to order",
    ]
    return any(k in m for k in advice_kw)


def _clean_slots(slots: dict[str, Any]) -> dict[str, Any]:
    """Drop empty LLM defaults so they don't overwrite saved session slots."""
    cleaned: dict[str, Any] = {}
    for key, val in slots.items():
        if val is None or val == "":
            continue
        if key in ("quantity", "delta", "po_id") and val in (0, "0"):
            continue
        if key == "lines" and isinstance(val, list):
            usable = [
                ln for ln in val
                if isinstance(ln, dict) and (ln.get("product_name") or ln.get("product_id")) and (ln.get("quantity") or ln.get("qty"))
            ]
            if usable:
                cleaned[key] = usable
            continue
        cleaned[key] = val
    return cleaned


def _looks_like_name(text: str) -> bool:
    t = text.strip()
    if not t or len(t) > 60:
        return False
    if re.search(r"\d", t):
        return False
    if re.search(r"\b(sell|bill|stock|invoice|help|cancel|yes|no|sales|unpaid|revenue|vendor|customer|purchase)\b", t, re.I):
        return False
    return len(t.split()) <= 5


def _fill_pending_slots(pending: str, merged: dict[str, Any], message: str, ctx: StoreContext) -> dict[str, Any]:
    """Use plain-text follow-ups to fill missing slots during multi-turn flows."""
    text = message.strip()
    if not text:
        return merged

    if pending == "create_bill":
        if not merged.get("customer_id") and not merged.get("customer_name"):
            if text.lower().startswith("bill for "):
                merged.update(_extract_name_after(message, ["for", "to"]))
            elif _looks_like_name(text):
                merged["customer_name"] = text
        if not merged.get("lines"):
            parsed = _parse_qty_product_lines(message, ctx)
            if parsed:
                merged["lines"] = [{"product_id": ln.product_id, "quantity": ln.quantity} for ln in parsed]

    elif pending == "add_customer" and not merged.get("name") and not merged.get("customer_name"):
        if _looks_like_name(text):
            merged["name"] = text

    elif pending == "add_vendor" and not merged.get("vendor_name") and not merged.get("name"):
        if _looks_like_name(text):
            merged["vendor_name"] = text

    elif pending == "record_sale" and not merged.get("lines"):
        parsed = _parse_qty_product_lines(message, ctx)
        if parsed:
            merged["lines"] = [{"product_id": ln.product_id, "quantity": ln.quantity} for ln in parsed]

    elif pending == "pay_invoice" and not merged.get("invoice_id"):
        if text.lower().startswith("invoice:"):
            try:
                merged["invoice_id"] = int(text.split(":", 1)[1])
            except ValueError:
                pass
        elif re.search(r"inv[-\s]?\d", text, re.I):
            merged["invoice_ref"] = text

    elif pending == "adjust_stock":
        if not merged.get("product_name"):
            for _, name in ctx.products:
                if name.lower() in text.lower():
                    merged["product_name"] = name
                    break

    return merged


def _resolve_intent(
    message: str,
    ctx: StoreContext,
    session: dict,
) -> tuple[str, dict[str, Any]]:
    """Rules first; LLM only when rules return general and not mid-flow slot fill."""
    rule_intent, rule_slots = _parse_intent_rules(message)

    if rule_intent != "general":
        return rule_intent, rule_slots

    if session.get("pending_action"):
        return "general", {}

    llm_parsed = _parse_with_llm(message, ctx, session)
    if llm_parsed and llm_parsed.get("confidence", 0) >= 0.5:
        llm_intent = llm_parsed.get("intent", "general")
        llm_slots = _clean_slots(llm_parsed.get("slots") or {})
        if llm_intent in WRITE_INTENTS | READ_INTENTS | {"confirm", "cancel"}:
            return llm_intent, llm_slots

    return "general", {}


def _apply_pending_context(
    intent: str,
    slots: dict[str, Any],
    message: str,
    session: dict,
    ctx: StoreContext,
) -> tuple[str, dict[str, Any]]:
    """Continue or break multi-turn flows."""
    pending = session.get("pending_action")
    if not pending:
        return intent, _clean_slots(slots)

    rule_intent, rule_slots = _parse_intent_rules(message)
    if rule_intent in SESSION_BREAK_INTENTS:
        session["pending_action"] = None
        session["slots"] = {}
        session["awaiting_confirm"] = False
        return rule_intent, rule_slots

    if rule_intent != "general" and rule_intent != pending and rule_intent in WRITE_INTENTS:
        session["pending_action"] = None
        session["slots"] = {}
        session["awaiting_confirm"] = False
        return rule_intent, rule_slots

    merged = {**session.get("slots", {}), **_clean_slots(slots), **_clean_slots(rule_slots)}
    merged = _fill_pending_slots(pending, merged, message, ctx)
    if message.lower().startswith("bill for "):
        merged.update(_extract_name_after(message, ["for", "to"]))
    if "bill last sale" in message.lower():
        merged["bill_last_sale"] = True

    session["slots"] = merged
    return pending, merged


def _extract_name_after(msg: str, keywords: list[str]) -> dict[str, Any]:
    lower = msg.lower()
    for kw in keywords:
        idx = lower.find(kw)
        if idx >= 0:
            name = msg[idx + len(kw) :].strip()
            name = re.sub(r"[^\w\s'-]", "", name).strip()
            if name:
                return {"customer_name": name}
    return {}


def _parse_with_llm(msg: str, ctx: StoreContext, session: dict) -> dict | None:
    prompt = f"""You are ShelfMind store assistant. Parse the user message into JSON.
User: {msg}
Pending action: {session.get("pending_action")}
Current slots: {json.dumps(session.get("slots") or {})}
Customers: {[n for _, n in ctx.customers[:20]]}
Products: {[n for _, n in ctx.products[:20]]}
Vendors: {[n for _, n in ctx.vendors[:10]]}

Return JSON only:
{{"intent": "create_bill|record_sale|pay_invoice|adjust_stock|add_customer|add_vendor|create_po|receive_po|low_stock|today_sales|weekly_sales|top_sellers|unpaid_invoices|help|greeting|general|confirm|cancel",
 "slots": {{"customer_name":"","product_name":"","quantity":0,"invoice_number":"","method":"cash","delta":0,"vendor_name":"","po_id":0,"lines":[{{"product_name":"","quantity":0}}],"segment":"Regular","bill_last_sale":false}},
 "confidence": 0.0-1.0}}

Use intent=greeting for hi/hello/hey. Use intent=general only for unclear messages."""
    fallback = {"intent": "general", "slots": {}, "confidence": 0}
    result = chat_json(prompt, fallback)
    if result.get("confidence", 0) >= 0.5:
        return result
    return None


def _customer_suggestions(ctx: StoreContext, limit: int = 6) -> list[dict]:
    return [{"label": name, "value": f"customer:{cid}", "command": f"bill for {name}"} for cid, name in ctx.customers[:limit]]


def _product_suggestions(ctx: StoreContext, limit: int = 8) -> list[dict]:
    return [
        {"label": name, "value": f"product:{pid}", "command": f"1 {name}"}
        for pid, name in ctx.products[:limit]
    ]


async def handle_message(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    message: str,
    session_id: str | None,
    fresh: bool = False,
) -> AgentResponse:
    if fresh and session_id:
        chat_session.clear_session(store_id, user_id, session_id)
        session_id = None

    sid = session_id or chat_session.new_session_id()
    session = chat_session.load_session(store_id, user_id, sid) or chat_session.default_session()
    ctx = await load_store_context(db, store_id)
    _append_history(session, "user", message)

    from app.config import get_settings

    if get_settings().llm_api_key:
        from app.services.agent_turn import run_turn

        llm_resp = await run_turn(db, store_id, user_id, sid, session, ctx, message)
        if llm_resp is not None:
            _append_history(session, "bot", llm_resp.reply)
            chat_session.save_session(store_id, user_id, sid, session)
            return llm_resp

    intent, slots = _resolve_intent(message, ctx, session)
    intent, slots = _apply_pending_context(intent, slots, message, session, ctx)

    if intent == "cancel":
        chat_session.clear_session(store_id, user_id, sid)
        return AgentResponse(
            reply="Cancelled. What would you like to do next?",
            intent="cancel",
            session_id=chat_session.new_session_id(),
            status="complete",
            actions=[{"label": "Help", "command": "help"}],
        )

    if intent == "confirm" and session.get("awaiting_confirm"):
        return await _execute_pending(db, store_id, user_id, sid, session, ctx)

    if intent == "create_bill":
        return await _handle_create_bill(db, store_id, user_id, sid, session, ctx, message, slots)

    if intent == "record_sale":
        return await _handle_record_sale(db, store_id, user_id, sid, session, ctx, message, slots)

    if intent == "pay_invoice":
        return await _handle_pay_invoice(db, store_id, user_id, sid, session, ctx, message, slots)

    if intent == "adjust_stock":
        return await _handle_adjust_stock(db, store_id, user_id, sid, session, ctx, message, slots)

    if intent == "add_customer":
        return await _handle_add_customer(db, store_id, user_id, sid, session, ctx, message, slots)

    if intent == "add_vendor":
        return await _handle_add_vendor(db, store_id, user_id, sid, session, ctx, message, slots)

    if intent == "create_po":
        return await _handle_create_po(db, store_id, user_id, sid, session, ctx, message, slots)

    if intent == "receive_po":
        return await _handle_receive_po(db, store_id, user_id, sid, session, ctx, message, slots)

    read_resp = await _handle_read_intent(db, store_id, intent, message, ctx, slots)
    if read_resp:
        if intent in ("greeting", "help"):
            session["pending_action"] = None
            session["slots"] = {}
            session["awaiting_confirm"] = False
            chat_session.save_session(store_id, user_id, sid, session)
            read_resp.session_id = sid
        else:
            read_resp.session_id = sid
            chat_session.save_session(store_id, user_id, sid, session)
        return read_resp

    if intent == "general" and _is_advice_question(message):
        try:
            from app.services.nl_query import process_nl_query

            result = await process_nl_query(db, message, store_id)
            recs = result.get("recommendations", [])
            if recs:
                summary = "; ".join(f"{r['product_name']}: {r['action']}" for r in recs[:3])
                chat_session.save_session(store_id, user_id, sid, session)
                return AgentResponse(
                    reply=f"Here's my stocking advice: {summary}",
                    intent="ai_recommendation",
                    session_id=sid,
                    data=result,
                    actions=[{"label": "View Demand Planner", "href": "/store/insights"}],
                )
        except Exception:
            pass

    chat_session.save_session(store_id, user_id, sid, session)
    return AgentResponse(
        reply="I can create bills, record sales, adjust stock, pay invoices, and answer stocking questions. Try 'help' to see commands.",
        intent="unknown",
        session_id=sid,
        status="needs_input",
        actions=[
            {"label": "Help", "command": "help"},
            {"label": "Today's sales", "command": "today's sales"},
            {"label": "Make bill", "command": "make bill for"},
        ],
    )


async def _handle_create_bill(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: StoreContext,
    message: str,
    slots: dict,
) -> AgentResponse:
    session["pending_action"] = "create_bill"
    merged = {**session.get("slots", {}), **slots}

    if "bill last sale" in message.lower() or merged.get("bill_last_sale"):
        merged["bill_last_sale"] = True

    customer_name = merged.get("customer_name") or merged.get("customer")
    customer_id = merged.get("customer_id")

    if isinstance(customer_id, str) and customer_id.isdigit():
        customer_id = int(customer_id)
        merged["customer_id"] = customer_id

    if customer_name and not customer_id:
        matches = fuzzy_match_entity(str(customer_name), ctx.customers)
        if len(matches) == 1:
            customer_id = matches[0][0]
            merged["customer_id"] = customer_id
            merged.pop("customer_name", None)
        elif len(matches) > 1:
            session["slots"] = merged
            chat_session.save_session(store_id, user_id, sid, session)
            return AgentResponse(
                reply="Which customer did you mean?",
                intent="create_bill",
                session_id=sid,
                status="needs_input",
                missing=["customer_name"],
                suggestions=[{"label": n, "value": f"customer:{i}", "command": f"bill for {n}"} for i, n in matches[:5]],
            )

    if customer_id and not merged.get("customer_id"):
        merged["customer_id"] = customer_id

    if not customer_id and not merged.get("bill_last_sale"):
        session["slots"] = merged
        chat_session.save_session(store_id, user_id, sid, session)
        return AgentResponse(
            reply="Which customer should I bill? Pick one or type their name.",
            intent="create_bill",
            session_id=sid,
            status="needs_input",
            missing=["customer_name"],
            suggestions=_customer_suggestions(ctx),
        )

    lines = _resolve_sale_lines(merged.get("lines") or [], message, ctx)

    if not lines and merged.get("bill_last_sale") and customer_id:
        txn = (
            await db.execute(
                select(Transaction.id)
                .where(Transaction.store_id == store_id, Transaction.customer_id == customer_id)
                .order_by(Transaction.sold_at.desc())
                .limit(5)
            )
        ).scalars().all()
        if txn:
            inv = await create_invoice_from_transactions(db, store_id, list(txn), customer_id)
            await db.commit()
            chat_session.clear_session(store_id, user_id, sid)
            cust_name = next((n for i, n in ctx.customers if i == customer_id), "customer")
            return AgentResponse(
                reply=f"Created bill {inv.invoice_number} for {cust_name} — Rs {inv.total:,.2f} (from recent sales).",
                intent="create_bill",
                session_id=chat_session.new_session_id(),
                status="complete",
                result={"invoice_id": inv.id, "invoice_number": inv.invoice_number, "total": inv.total},
                actions=[{"label": "View Billing", "href": "/store/billing"}],
            )

    if not lines:
        merged["customer_id"] = customer_id
        session["slots"] = merged
        session["pending_action"] = "create_bill"
        chat_session.save_session(store_id, user_id, sid, session)
        cust_label = next((n for i, n in ctx.customers if i == customer_id), "customer") if customer_id else "customer"
        return AgentResponse(
            reply=f"What should I bill for {cust_label}? Example: '2 milk and 1 bread' or say 'bill last sale'.",
            intent="create_bill",
            session_id=sid,
            status="needs_input",
            missing=["products"],
            suggestions=[
                {"label": "Bill last sale", "value": "bill_last_sale", "command": "bill last sale"},
                *_product_suggestions(ctx, 5),
            ],
        )

    sale_lines = lines
    result = await create_invoice_for_customer(db, store_id, customer_id, sale_lines)
    chat_session.clear_session(store_id, user_id, sid)
    cust_name = next((n for i, n in ctx.customers if i == customer_id), "Walk-in") if customer_id else "Walk-in"
    return AgentResponse(
        reply=f"Done! Bill {result['invoice_number']} for {cust_name} — Rs {result['total']:,.2f} (GST included).",
        intent="create_bill",
        session_id=chat_session.new_session_id(),
        status="complete",
        result=result,
        actions=[{"label": "View Billing", "href": "/store/billing"}],
    )


async def _handle_record_sale(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: StoreContext,
    message: str,
    slots: dict,
) -> AgentResponse:
    session["pending_action"] = "record_sale"
    merged = {**session.get("slots", {}), **slots}

    lines = _parse_qty_product_lines(message, ctx)
    if lines:
        customer_id = merged.get("customer_id")
        if merged.get("customer_name") and not customer_id:
            matches = fuzzy_match_entity(str(merged["customer_name"]), ctx.customers)
            if len(matches) == 1:
                customer_id = matches[0][0]

        txn_ids, total = await apply_batch_sale(db, store_id, lines, customer_id)
        await db.commit()
        chat_session.clear_session(store_id, user_id, sid)
        return AgentResponse(
            reply=f"Sale recorded — Rs {total:,.2f} for {len(lines)} item(s).",
            intent="record_sale",
            session_id=chat_session.new_session_id(),
            status="complete",
            result={"transaction_ids": txn_ids, "total": total},
            actions=[{"label": "Make bill", "command": "make bill for customer"}, {"label": "View Sales", "href": "/store/sales"}],
        )

    session["slots"] = merged
    chat_session.save_session(store_id, user_id, sid, session)
    return AgentResponse(
        reply="What should I sell? Example: 'sell 2 milk' or 'sell 1 umbrella to Rajesh'.",
        intent="record_sale",
        session_id=sid,
        status="needs_input",
        missing=["products"],
        suggestions=_product_suggestions(ctx),
    )


async def _handle_pay_invoice(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: StoreContext,
    message: str,
    slots: dict,
) -> AgentResponse:
    m = message.lower()
    method = "cash"
    if "upi" in m:
        method = "upi"
    elif "card" in m:
        method = "card"

    inv_match = re.search(r"inv[-\s]?(\d+[-\s]?\d+)", m, re.I)
    invoice_id = slots.get("invoice_id")
    invoice = None

    if invoice_id and not invoice:
        try:
            invoice_id = int(invoice_id)
        except (TypeError, ValueError):
            invoice_id = None

    if inv_match:
        num = inv_match.group(0).upper().replace(" ", "-")
        if not num.startswith("INV"):
            num = f"INV-{num}"
        invoice = (
            await db.execute(
                select(Invoice).where(Invoice.store_id == store_id, Invoice.invoice_number.ilike(f"%{num}%"))
            )
        ).scalar_one_or_none()

    if not invoice and invoice_id:
        invoice = (
            await db.execute(select(Invoice).where(Invoice.id == invoice_id, Invoice.store_id == store_id))
        ).scalar_one_or_none()

    if not invoice:
        unpaid = (
            await db.execute(
                select(Invoice)
                .where(Invoice.store_id == store_id, Invoice.status.in_(["sent", "overdue", "draft"]))
                .order_by(Invoice.issued_at.desc())
                .limit(5)
            )
        ).scalars().all()
        if not unpaid:
            chat_session.clear_session(store_id, user_id, sid)
            return AgentResponse(reply="No unpaid invoices to mark as paid.", intent="pay_invoice", session_id=chat_session.new_session_id())
        session["pending_action"] = "pay_invoice"
        chat_session.save_session(store_id, user_id, sid, session)
        return AgentResponse(
            reply="Which invoice should I mark as paid?",
            intent="pay_invoice",
            session_id=sid,
            status="needs_input",
            missing=["invoice_number"],
            suggestions=[
                {"label": f"{inv.invoice_number} (Rs {inv.total})", "value": f"invoice:{inv.id}", "command": f"mark {inv.invoice_number} paid via {method}"}
                for inv in unpaid
            ],
        )

    result = await record_invoice_payment(db, store_id, invoice.id, invoice.total, method)
    chat_session.clear_session(store_id, user_id, sid)
    return AgentResponse(
        reply=f"Payment recorded for {result['invoice_number']} via {method}. Status: {result['status']}.",
        intent="pay_invoice",
        session_id=chat_session.new_session_id(),
        status="complete",
        result=result,
        actions=[{"label": "View Billing", "href": "/store/billing"}],
    )


async def _handle_adjust_stock(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: StoreContext,
    message: str,
    slots: dict,
) -> AgentResponse:
    m = message.lower()
    delta = slots.get("delta")
    add_match = re.search(r"(?:add|increase)\s+(\d+)", m)
    remove_match = re.search(r"(?:remove|decrease)\s+(\d+)", m)
    qty_match = re.search(r"(\d+)", m)
    if add_match:
        delta = int(add_match.group(1))
    elif remove_match:
        delta = -int(remove_match.group(1))
    elif qty_match and delta is None:
        delta = int(qty_match.group(1))
        if "remove" in m or "decrease" in m:
            delta = -delta

    product_name = slots.get("product_name")
    if not product_name:
        for _, name in ctx.products:
            if name.lower() in m:
                product_name = name
                break

    if product_name and delta is not None:
        matches = fuzzy_match_entity(str(product_name), ctx.products)
        if matches:
            result = await adjust_product_stock(db, store_id, matches[0][0], int(delta))
            chat_session.clear_session(store_id, user_id, sid)
            return AgentResponse(
                reply=f"Updated {result['product_name']} stock to {result['stock_on_hand']} units.",
                intent="adjust_stock",
                session_id=chat_session.new_session_id(),
                status="complete",
                result=result,
                actions=[{"label": "View Inventory", "href": "/store/inventory"}],
            )

    session["pending_action"] = "adjust_stock"
    chat_session.save_session(store_id, user_id, sid, session)
    return AgentResponse(
        reply="Tell me the product and quantity. Example: 'add 10 milk to stock'.",
        intent="adjust_stock",
        session_id=sid,
        status="needs_input",
        missing=["product", "delta"],
        suggestions=_product_suggestions(ctx),
    )


async def _handle_add_customer(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: StoreContext,
    message: str,
    slots: dict,
) -> AgentResponse:
    m = message.lower()
    name = slots.get("name") or slots.get("customer_name")
    if not name and session.get("pending_action") == "add_customer" and _looks_like_name(message):
        name = message.strip()
    if not name:
        m2 = re.sub(r"^(add|new)\s+(customer|regular)\s+", "", m, flags=re.I).strip()
        if m2 and m2 not in ("customer", "regular"):
            name = message.split(maxsplit=2)[-1] if len(message.split()) >= 3 else None
            if name and name.lower().startswith(("customer", "regular")):
                parts = message.split(None, 2)
                name = parts[2] if len(parts) > 2 else None

    segment = "Regular"
    if "vip" in m:
        segment = "VIP"
    elif "new" in m.split()[-1:]:
        segment = "New"

    if name:
        result = await create_customer_record(db, store_id, name.strip(), segment=segment)
        chat_session.clear_session(store_id, user_id, sid)
        return AgentResponse(
            reply=f"Added customer {result['name']} ({result['segment']}).",
            intent="add_customer",
            session_id=chat_session.new_session_id(),
            status="complete",
            result=result,
            actions=[{"label": "View Regulars", "href": "/store/customers"}],
        )

    session["pending_action"] = "add_customer"
    chat_session.save_session(store_id, user_id, sid, session)
    return AgentResponse(
        reply="What's the customer's name?",
        intent="add_customer",
        session_id=sid,
        status="needs_input",
        missing=["name"],
    )


async def _handle_add_vendor(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: StoreContext,
    message: str,
    slots: dict,
) -> AgentResponse:
    name = slots.get("vendor_name") or slots.get("name")
    if not name:
        parts = re.sub(r"^(add|new)\s+(vendor|supplier)\s+", "", message, flags=re.I).strip()
        if parts:
            name = parts

    if name:
        result = await create_vendor_record(db, store_id, name.strip())
        chat_session.clear_session(store_id, user_id, sid)
        return AgentResponse(
            reply=f"Added vendor {result['name']}.",
            intent="add_vendor",
            session_id=chat_session.new_session_id(),
            status="complete",
            result=result,
            actions=[{"label": "View Purchases", "href": "/store/purchases"}],
        )

    session["pending_action"] = "add_vendor"
    chat_session.save_session(store_id, user_id, sid, session)
    return AgentResponse(
        reply="What's the vendor name?",
        intent="add_vendor",
        session_id=sid,
        status="needs_input",
        missing=["vendor_name"],
    )


async def _handle_create_po(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: StoreContext,
    message: str,
    slots: dict,
) -> AgentResponse:
    session["pending_action"] = "create_po"
    merged = {**session.get("slots", {}), **slots}

    vendor_name = merged.get("vendor_name")
    vendor_id = merged.get("vendor_id")
    if vendor_name and not vendor_id:
        matches = fuzzy_match_entity(str(vendor_name), ctx.vendors)
        if len(matches) == 1:
            vendor_id = matches[0][0]
        elif len(matches) > 1:
            session["slots"] = merged
            chat_session.save_session(store_id, user_id, sid, session)
            return AgentResponse(
                reply="Which vendor?",
                intent="create_po",
                session_id=sid,
                status="needs_input",
                suggestions=[{"label": n, "command": f"order from {n}"} for _, n in matches[:5]],
            )

    lines = _parse_qty_product_lines(message, ctx)
    if vendor_id and lines:
        po_lines = [(ln.product_id, ln.quantity, None) for ln in lines]
        result = await create_purchase_order(db, store_id, vendor_id, po_lines)
        chat_session.clear_session(store_id, user_id, sid)
        return AgentResponse(
            reply=f"Purchase order #{result['id']} created for {result['vendor_name']} — Rs {result['total']:,.2f}.",
            intent="create_po",
            session_id=chat_session.new_session_id(),
            status="complete",
            result=result,
            actions=[{"label": "View Purchases", "href": "/store/purchases"}],
        )

    session["slots"] = merged
    chat_session.save_session(store_id, user_id, sid, session)
    return AgentResponse(
        reply="Tell me vendor and items. Example: 'order 20 milk from Amul vendor'.",
        intent="create_po",
        session_id=sid,
        status="needs_input",
        missing=["vendor", "lines"],
        suggestions=[{"label": n, "command": f"order from {n}"} for _, n in ctx.vendors[:5]],
    )


async def _handle_receive_po(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: StoreContext,
    message: str,
    slots: dict,
) -> AgentResponse:
    po_match = re.search(r"\b(\d+)\b", message)
    if po_match:
        po_id = int(po_match.group(1))
        result = await receive_purchase_order(db, store_id, po_id)
        chat_session.clear_session(store_id, user_id, sid)
        return AgentResponse(
            reply=f"PO #{result['id']} marked received. Stock updated.",
            intent="receive_po",
            session_id=chat_session.new_session_id(),
            status="complete",
            result=result,
            actions=[{"label": "View Purchases", "href": "/store/purchases"}],
        )

    pending = (
        await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.store_id == store_id, PurchaseOrder.status == "ordered")
            .order_by(PurchaseOrder.ordered_at.desc())
            .limit(5)
        )
    ).scalars().all()
    if not pending:
        return AgentResponse(reply="No pending purchase orders to receive.", intent="receive_po", session_id=chat_session.new_session_id())

    session["pending_action"] = "receive_po"
    chat_session.save_session(store_id, user_id, sid, session)
    return AgentResponse(
        reply="Which PO should I receive?",
        intent="receive_po",
        session_id=sid,
        status="needs_input",
        suggestions=[{"label": f"PO #{po.id}", "command": f"receive PO {po.id}"} for po in pending],
    )


async def _execute_pending(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    sid: str,
    session: dict,
    ctx: StoreContext,
) -> AgentResponse:
    action = session.get("pending_action")
    session["awaiting_confirm"] = False
    if action == "create_bill":
        return await _handle_create_bill(db, store_id, user_id, sid, session, ctx, "confirm", session.get("slots", {}))
    chat_session.clear_session(store_id, user_id, sid)
    return AgentResponse(reply="Confirmed.", intent="confirm", session_id=chat_session.new_session_id())


async def _handle_read_intent(
    db: AsyncSession,
    store_id: int,
    intent: str,
    message: str,
    ctx: StoreContext,
    slots: dict | None = None,
) -> AgentResponse | None:
    if intent == "greeting":
        store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
        name = store.name if store else "there"
        return AgentResponse(
            reply=f"Hey! Welcome to {name}. Ask me anything — bills, sales, stock, reports, or stocking advice.",
            intent=intent,
            session_id="",
            actions=[
                {"label": "Help", "command": "help"},
                {"label": "Today's sales", "command": "today's sales"},
                {"label": "Sales report", "command": "sales report this week"},
                {"label": "Store overview", "command": "generate store overview report"},
                {"label": "Low stock", "command": "low stock"},
            ],
        )

    if intent == "help":
        return AgentResponse(
            reply="Here's what I can do — ask in plain language:",
            intent=intent,
            session_id="",
            actions=[
                {"label": "Make bill for customer", "command": "make bill for"},
                {"label": "Sell 2 milk", "command": "sell 2 milk"},
                {"label": "Mark invoice paid", "command": "unpaid invoices"},
                {"label": "Add 10 stock", "command": "add 10 stock"},
                {"label": "Add customer", "command": "add customer"},
                {"label": "Low stock", "command": "low stock"},
                {"label": "Today's sales", "command": "today's sales"},
                {"label": "Top sellers", "command": "top sellers"},
                {"label": "Sales report", "command": "sales report this week"},
                {"label": "Inventory report", "command": "inventory report"},
                {"label": "Store overview", "command": "store overview report"},
            ],
        )

    if intent in ("generate_report", "top_sellers", "gst_summary", "revenue_summary", "stock_check", "purchases"):
        from app.services.store_reports import generate_store_report, report_to_agent_data

        params = dict(slots or {})
        if intent == "top_sellers":
            params.setdefault("report_type", "top_products")
        elif intent == "gst_summary":
            params.setdefault("report_type", "gst")
        elif intent == "revenue_summary":
            params.setdefault("report_type", "sales")
        elif intent == "stock_check":
            params.setdefault("report_type", "inventory")
        elif intent == "purchases":
            params.setdefault("report_type", "purchases")

        report = await generate_store_report(db, store_id, message, params)
        data = report_to_agent_data(report)
        return AgentResponse(
            reply=report.get("summary", "Here's your report."),
            intent="generate_report",
            session_id="",
            data=data,
            actions=[{"label": "Reports", "href": "/store/reports"}],
        )

    if intent == "low_stock":
        rows = (
            await db.execute(
                select(Product)
                .where(Product.store_id == store_id, Product.stock_on_hand <= Product.reorder_level)
                .order_by(Product.stock_on_hand)
            )
        ).scalars().all()
        if not rows:
            return AgentResponse(reply="All products are well stocked.", intent=intent, session_id="")
        items = [{"name": p.name, "stock": p.stock_on_hand} for p in rows[:8]]
        names = ", ".join(p.name for p in rows[:5])
        return AgentResponse(
            reply=f"{len(rows)} items low: {names}.",
            intent=intent,
            session_id="",
            data={"items": items},
            actions=[{"label": "Inventory", "href": "/store/inventory"}],
        )

    if intent == "today_sales":
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        count, total = (
            await db.execute(
                select(func.count(Transaction.id), func.coalesce(func.sum(Transaction.quantity * Transaction.unit_price), 0)).where(
                    Transaction.store_id == store_id, Transaction.sold_at >= today_start
                )
            )
        ).one()
        return AgentResponse(
            reply=f"Today: {count} sale(s), Rs {float(total):,.2f}.",
            intent=intent,
            session_id="",
            data={"count": int(count), "total": round(float(total), 2)},
            actions=[{"label": "Sales", "href": "/store/sales"}],
        )

    if intent == "weekly_sales":
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        count, total = (
            await db.execute(
                select(func.count(Transaction.id), func.coalesce(func.sum(Transaction.quantity * Transaction.unit_price), 0)).where(
                    Transaction.store_id == store_id, Transaction.sold_at >= week_ago
                )
            )
        ).one()
        return AgentResponse(
            reply=f"This week: {count} sales, Rs {float(total):,.2f}.",
            intent=intent,
            session_id="",
            actions=[{"label": "Reports", "href": "/store/reports"}],
        )

    if intent == "unpaid_invoices":
        rows = (
            await db.execute(
                select(Invoice).where(Invoice.store_id == store_id, Invoice.status.in_(["sent", "overdue", "draft"]))
            )
        ).scalars().all()
        total_due = sum(inv.total for inv in rows)
        if not rows:
            return AgentResponse(reply="All bills cleared!", intent=intent, session_id="")
        return AgentResponse(
            reply=f"{len(rows)} unpaid invoice(s), Rs {total_due:,.2f} due.",
            intent=intent,
            session_id="",
            actions=[{"label": "Billing", "href": "/store/billing"}],
        )

    if intent == "customers":
        if not ctx.customers:
            return AgentResponse(reply="No customers yet.", intent=intent, session_id="")
        top = ctx.customers[:5]
        return AgentResponse(
            reply=f"Top customers: {', '.join(n for _, n in top)}.",
            intent=intent,
            session_id="",
            suggestions=_customer_suggestions(ctx),
            actions=[{"label": "Regulars", "href": "/store/customers"}],
        )

    if intent in ("general",):
        return None

    return None


def to_dict(resp: AgentResponse) -> dict:
    return {
        "reply": resp.reply,
        "intent": resp.intent,
        "session_id": resp.session_id,
        "status": resp.status,
        "missing": resp.missing,
        "suggestions": resp.suggestions,
        "result": resp.result,
        "data": resp.data,
        "actions": resp.actions,
    }
