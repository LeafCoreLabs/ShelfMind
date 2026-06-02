import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import AppShell from "../../components/layout/AppShell";
import { storeApi, SaleRow, ProductRow, CustomerRow } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import { AnimatedTableBody, AnimatedTableRow } from "../../components/motion/AnimatedTable";
import "./store-theme.css";

interface CartLine {
  product_id: number;
  quantity: number;
}

export default function SalesPage() {
  const [sales, setSales] = useState<SaleRow[]>([]);
  const [products, setProducts] = useState<ProductRow[]>([]);
  const [customers, setCustomers] = useState<CustomerRow[]>([]);
  const [customerId, setCustomerId] = useState<number | "">("");
  const [cart, setCart] = useState<CartLine[]>([{ product_id: 0, quantity: 1 }]);
  const [msg, setMsg] = useState<string | null>(null);
  const [lastTxnIds, setLastTxnIds] = useState<number[]>([]);
  const [lastInvoice, setLastInvoice] = useState<string | null>(null);
  const [billing, setBilling] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const load = () => storeApi.getSales().then((r) => setSales(r.sales));

  useEffect(() => {
    load();
    storeApi.getProducts().then((r) => setProducts(r.products));
    storeApi.getCustomers().then((r) => setCustomers(r.customers));
  }, []);

  const cartTotal = cart.reduce((sum, line) => {
    const p = products.find((x) => x.id === line.product_id);
    return sum + (p ? p.list_price * line.quantity : 0);
  }, 0);

  const recordSale = async (e: React.FormEvent) => {
    e.preventDefault();
    const validLines = cart.filter((l) => l.product_id && l.quantity > 0);
    if (!validLines.length) return;
    setSubmitting(true);
    setLastTxnIds([]);
    setLastInvoice(null);
    try {
      const res = await storeApi.createBatchSale({
        lines: validLines.map((l) => ({ product_id: l.product_id, quantity: l.quantity })),
        customer_id: customerId ? Number(customerId) : undefined,
      });
      setMsg(`Sale recorded — ₹${res.total} (${validLines.length} item${validLines.length > 1 ? "s" : ""})`);
      setLastTxnIds(res.transaction_ids);
      setCart([{ product_id: 0, quantity: 1 }]);
      await load();
    } catch {
      setMsg("Sale failed — check stock.");
    } finally {
      setSubmitting(false);
    }
  };

  const generateBill = async () => {
    if (!lastTxnIds.length) return;
    setBilling(true);
    try {
      const inv = await storeApi.createInvoiceFromSales(lastTxnIds);
      setLastInvoice(inv.invoice_number);
      setMsg(`GST bill ${inv.invoice_number} created — ₹${inv.total}`);
    } catch {
      setMsg("Could not generate bill.");
    } finally {
      setBilling(false);
    }
  };

  return (
    <AppShell {...STORE_SHELL} title="Sales & POS" subtitle="Multi-item counter sales and GST bills">
      <AnimatedPanel className="admin-card pos-cart-sticky" style={{ marginBottom: "1rem" }}>
        <div className="admin-card-title">POS cart</div>
        <form onSubmit={recordSale} className="pos-form">
          <label>
            Regular (optional)
            <select className="admin-input" value={customerId} onChange={(e) => setCustomerId(Number(e.target.value) || "")}>
              <option value="">Walk-in</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </label>
          {cart.map((line, idx) => (
            <div key={idx} className="pos-cart-row">
              <select
                className="admin-input"
                value={line.product_id || ""}
                onChange={(e) => {
                  const next = [...cart];
                  next[idx] = { ...next[idx], product_id: Number(e.target.value) };
                  setCart(next);
                }}
                aria-label={`Product line ${idx + 1}`}
              >
                <option value="">Select product</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>{p.name} · {p.stock_on_hand} in stock · ₹{p.list_price}</option>
                ))}
              </select>
              <input
                className="admin-input"
                type="number"
                min={1}
                value={line.quantity}
                onChange={(e) => {
                  const next = [...cart];
                  next[idx] = { ...next[idx], quantity: Number(e.target.value) };
                  setCart(next);
                }}
                aria-label={`Quantity line ${idx + 1}`}
              />
              {cart.length > 1 && (
                <button
                  type="button"
                  className="admin-btn admin-btn-ghost admin-btn-sm"
                  onClick={() => setCart(cart.filter((_, i) => i !== idx))}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <div className="pos-cart-actions">
            <button type="button" className="admin-btn admin-btn-ghost" onClick={() => setCart([...cart, { product_id: 0, quantity: 1 }])}>
              + Add another item
            </button>
            <motion.span key={Math.round(cartTotal)} style={{ color: "var(--text-muted)" }} initial={{ opacity: 0.6 }} animate={{ opacity: 1 }}>
              Cart total: ₹{cartTotal.toFixed(2)}
            </motion.span>
            <button type="submit" className="admin-btn admin-btn-primary" disabled={submitting}>
              Complete sale
            </button>
          </div>
        </form>
        {msg && <p className="admin-job-msg">{msg}</p>}
        {lastTxnIds.length > 0 && !lastInvoice && (
          <button type="button" className="admin-btn admin-btn-sm" disabled={billing} onClick={generateBill} style={{ marginTop: 8 }}>
            Generate GST bill
          </button>
        )}
        {lastInvoice && (
          <Link to="/store/billing" className="admin-btn admin-btn-ghost" style={{ marginTop: 8, marginLeft: 8 }}>
            View in Bills & GST →
          </Link>
        )}
      </AnimatedPanel>

      <AnimatedPanel className="admin-card store-table-wrap">
        <table className="admin-table admin-table-modern">
          <thead>
            <tr>
              <th>Date</th>
              <th>Product</th>
              <th>Qty</th>
              <th>Total</th>
              <th>Regular</th>
            </tr>
          </thead>
          <AnimatedTableBody dataKey={sales.length}>
            {sales.map((s, i) => (
              <AnimatedTableRow key={s.id} index={i}>
                <td>{new Date(s.sold_at).toLocaleString()}</td>
                <td>{s.product_name}</td>
                <td>{s.quantity}</td>
                <td>₹{s.total}</td>
                <td>{s.customer_id ? customers.find((c) => c.id === s.customer_id)?.name ?? `#${s.customer_id}` : "—"}</td>
              </AnimatedTableRow>
            ))}
          </AnimatedTableBody>
        </table>
      </AnimatedPanel>
    </AppShell>
  );
}
