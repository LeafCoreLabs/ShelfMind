import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import AppShell from "../../components/layout/AppShell";
import { storeApi, InvoiceRow, CustomerRow, InvoiceDetail } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import AnimatedStat from "../../components/motion/AnimatedStat";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock";
import "./store-theme.css";

export default function BillingPage() {
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [customers, setCustomers] = useState<CustomerRow[]>([]);
  const [storeGstin, setStoreGstin] = useState<string | null>(null);
  const [paying, setPaying] = useState<number | null>(null);
  const [payMethod, setPayMethod] = useState<Record<number, string>>({});
  const [viewInvoice, setViewInvoice] = useState<InvoiceDetail | null>(null);

  useBodyScrollLock(!!viewInvoice);

  const load = () => {
    storeApi.getInvoices().then((r) => {
      setInvoices(r.invoices);
      setStoreGstin(r.store_gstin ?? null);
    });
    storeApi.getCustomers().then((r) => setCustomers(r.customers));
  };

  useEffect(() => {
    load();
  }, []);

  const pay = async (inv: InvoiceRow) => {
    setPaying(inv.id);
    try {
      const method = payMethod[inv.id] || "upi";
      await storeApi.payInvoice(inv.id, inv.total, method);
      await load();
      if (viewInvoice?.id === inv.id) setViewInvoice(null);
    } finally {
      setPaying(null);
    }
  };

  const openInvoice = async (id: number) => {
    const detail = await storeApi.getInvoice(id);
    setViewInvoice(detail);
  };

  const customerName = (id: number | null) => {
    if (!id) return "Walk-in";
    return customers.find((c) => c.id === id)?.name ?? `#${id}`;
  };

  const outstanding = invoices.filter((i) => i.status !== "paid");

  return (
    <AppShell {...STORE_SHELL} title="Bills & GST" subtitle="Tax invoices, CGST/SGST split, and payments">
      <div style={{ marginBottom: "1rem" }}>
      <StaggerGrid className="admin-grid-2">
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Store GSTIN</div>
            <div className="admin-stat-value gst-mono">{storeGstin || "Not set"}</div>
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Outstanding</div>
            <AnimatedStat value={outstanding.length} />
          </div>
        </StaggerItem>
      </StaggerGrid>
      </div>

      <AnimatePresence>
        {viewInvoice && (
          <>
            <motion.div className="slide-over-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setViewInvoice(null)} />
            <motion.div
              className="slide-over-panel tax-invoice-print"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 320, damping: 32 }}
            >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div className="admin-card-title">Tax Invoice</div>
              <p style={{ margin: "0.25rem 0", color: "var(--text-muted)" }}>{viewInvoice.invoice_number}</p>
            </div>
            <button type="button" className="admin-btn admin-btn-ghost" onClick={() => setViewInvoice(null)}>Close</button>
          </div>
          <div className="admin-grid-2" style={{ marginTop: "1rem", fontSize: "0.9rem" }}>
            <div>
              <strong>{viewInvoice.store_name}</strong><br />
              {viewInvoice.store_location}<br />
              <span className="gst-mono">GSTIN: {viewInvoice.gstin || "—"}</span>
            </div>
            <div style={{ textAlign: "right" }}>
              Bill to: {viewInvoice.customer_name}<br />
              Place of supply: {viewInvoice.place_of_supply || "—"}<br />
              Date: {new Date(viewInvoice.issued_at).toLocaleDateString()}
            </div>
          </div>
          <div className="store-table-wrap">
          <table className="admin-table admin-table-modern" style={{ marginTop: "1rem" }}>
            <thead>
              <tr>
                <th>Item</th>
                <th>HSN</th>
                <th>Qty</th>
                <th>Rate</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {viewInvoice.lines.map((ln, i) => (
                <tr key={i}>
                  <td>{ln.description}</td>
                  <td>{ln.hsn_code || "—"}</td>
                  <td>{ln.quantity}</td>
                  <td>₹{ln.unit_price}</td>
                  <td>₹{ln.line_total}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <div className="tax-invoice-totals">
            <div>Subtotal: ₹{viewInvoice.subtotal}</div>
            <div>CGST (9%): ₹{viewInvoice.cgst_amount ?? 0}</div>
            <div>SGST (9%): ₹{viewInvoice.sgst_amount ?? 0}</div>
            {(viewInvoice.igst_amount ?? 0) > 0 && <div>IGST (18%): ₹{viewInvoice.igst_amount}</div>}
            <div><strong>Total: ₹{viewInvoice.total}</strong></div>
          </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <AnimatedPanel className="admin-card store-table-wrap">
        <table className="admin-table admin-table-modern">
          <thead>
            <tr>
              <th>Bill #</th>
              <th>Regular</th>
              <th>Status</th>
              <th>Subtotal</th>
              <th>CGST</th>
              <th>SGST</th>
              <th>Total</th>
              <th>Issued</th>
              <th className="billing-actions-col"></th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id}>
                <td>
                  <button type="button" className="admin-btn admin-btn-ghost admin-btn-sm" onClick={() => openInvoice(inv.id)}>
                    {inv.invoice_number}
                  </button>
                </td>
                <td>{customerName(inv.customer_id)}</td>
                <td>
                  <span className={`admin-badge admin-badge-${inv.status === "paid" ? "active" : "warning"}`}>
                    {inv.status}
                  </span>
                </td>
                <td className="gst-mono">₹{inv.subtotal}</td>
                <td className="gst-mono">₹{inv.cgst_amount ?? 0}</td>
                <td className="gst-mono">₹{inv.sgst_amount ?? 0}</td>
                <td className="gst-mono">₹{inv.total}</td>
                <td>{new Date(inv.issued_at).toLocaleDateString()}</td>
                <td className="billing-actions-col">
                  {inv.status !== "paid" && (
                    <div className="billing-actions-row">
                      <select
                        className="admin-input admin-input-compact"
                        value={payMethod[inv.id] || "upi"}
                        onChange={(e) => setPayMethod((p) => ({ ...p, [inv.id]: e.target.value }))}
                      >
                        <option value="cash">Cash</option>
                        <option value="upi">UPI</option>
                        <option value="card">Card</option>
                      </select>
                      <button
                        type="button"
                        className="admin-btn admin-btn-sm"
                        disabled={paying === inv.id}
                        onClick={() => pay(inv)}
                      >
                        Record payment
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {invoices.length === 0 && <div className="admin-empty-state">No bills yet. Generate one from a sale.</div>}
      </AnimatedPanel>
    </AppShell>
  );
}
