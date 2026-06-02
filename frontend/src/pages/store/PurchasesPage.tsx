import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppShell from "../../components/layout/AppShell";
import { storeApi, VendorRow, PurchaseRow, ProductRow } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import "./store-theme.css";

interface CartLine {
  product_id: number;
  qty: number;
  unit_cost?: number;
}

export default function PurchasesPage() {
  const [vendors, setVendors] = useState<VendorRow[]>([]);
  const [purchases, setPurchases] = useState<PurchaseRow[]>([]);
  const [products, setProducts] = useState<ProductRow[]>([]);
  const [vendorName, setVendorName] = useState("");
  const [vendorGstin, setVendorGstin] = useState("");
  const [selectedVendor, setSelectedVendor] = useState<number | "">("");
  const [lines, setLines] = useState<CartLine[]>([{ product_id: 0, qty: 10 }]);
  const [msg, setMsg] = useState<string | null>(null);
  const [receiving, setReceiving] = useState<number | null>(null);

  const load = () => {
    storeApi.getVendors().then((r) => setVendors(r.vendors));
    storeApi.getPurchases().then((r) => setPurchases(r.purchases));
    storeApi.getProducts().then((r) => setProducts(r.products));
  };

  useEffect(() => {
    load();
  }, []);

  const addVendor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!vendorName.trim()) return;
    await storeApi.createVendor({ name: vendorName, gstin: vendorGstin || undefined });
    setVendorName("");
    setVendorGstin("");
    load();
  };

  const createPo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedVendor) return;
    const validLines = lines.filter((l) => l.product_id && l.qty > 0);
    if (!validLines.length) return;
    try {
      const res = await storeApi.createPurchase({
        vendor_id: Number(selectedVendor),
        lines: validLines.map((l) => ({ product_id: l.product_id, qty: l.qty })),
      });
      setMsg(`Purchase order created — ₹${res.total}`);
      setLines([{ product_id: 0, qty: 10 }]);
      load();
    } catch {
      setMsg("Could not create purchase order.");
    }
  };

  const receive = async (id: number) => {
    setReceiving(id);
    try {
      await storeApi.receivePurchase(id);
      setMsg("Stock received and updated.");
      load();
    } catch {
      setMsg("Receive failed.");
    } finally {
      setReceiving(null);
    }
  };

  const productName = (id: number) => products.find((p) => p.id === id)?.name ?? `#${id}`;

  return (
    <AppShell {...STORE_SHELL} title="Purchases" subtitle="Vendor orders and stock receiving">
      <div style={{ marginBottom: "1rem" }}>
      <StaggerGrid className="admin-grid-2">
        <StaggerItem>
        <AnimatedPanel>
          <div className="admin-card-title">Add vendor</div>
          <form onSubmit={addVendor} className="admin-form-grid">
            <label>
              Vendor name
              <input className="admin-input" placeholder="Vendor name" value={vendorName} onChange={(e) => setVendorName(e.target.value)} />
            </label>
            <label>
              GSTIN (optional)
              <input className="admin-input gst-mono" placeholder="27AABCU9603R1ZM" value={vendorGstin} onChange={(e) => setVendorGstin(e.target.value)} />
            </label>
            <button type="submit" className="admin-btn admin-btn-primary">Add vendor</button>
          </form>
          <ul className="admin-recent-list" style={{ marginTop: "0.75rem" }}>
            {vendors.map((v) => (
              <li key={v.id}>{v.name}{v.gstin ? ` — ${v.gstin}` : ""}</li>
            ))}
          </ul>
        </AnimatedPanel>
        </StaggerItem>

        <StaggerItem>
        <AnimatedPanel>
          <div className="admin-card-title">New purchase order</div>
          <form onSubmit={createPo} className="pos-form">
            <label>
              Vendor
              <select className="admin-input" value={selectedVendor} onChange={(e) => setSelectedVendor(Number(e.target.value) || "")}>
                <option value="">Select vendor</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </label>
            {lines.map((line, idx) => (
              <div key={idx} className="pos-cart-row">
                <select
                  className="admin-input"
                  value={line.product_id || ""}
                  onChange={(e) => {
                    const next = [...lines];
                    next[idx] = { ...next[idx], product_id: Number(e.target.value) };
                    setLines(next);
                  }}
                  aria-label={`Product line ${idx + 1}`}
                >
                  <option value="">Product</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
                <input
                  className="admin-input"
                  type="number"
                  min={1}
                  value={line.qty}
                  onChange={(e) => {
                    const next = [...lines];
                    next[idx] = { ...next[idx], qty: Number(e.target.value) };
                    setLines(next);
                  }}
                  aria-label={`Quantity line ${idx + 1}`}
                />
              </div>
            ))}
            <button type="button" className="admin-btn admin-btn-ghost" onClick={() => setLines([...lines, { product_id: 0, qty: 10 }])}>
              + Add line
            </button>
            <button type="submit" className="admin-btn admin-btn-primary">Create PO</button>
          </form>
          {msg && <p className="admin-job-msg">{msg}</p>}
        </AnimatedPanel>
        </StaggerItem>
      </StaggerGrid>
      </div>

      <AnimatedPanel className="admin-card store-table-wrap">
        <div className="admin-card-title">Purchase orders</div>
        <table className="admin-table admin-table-modern">
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Status</th>
              <th>Total</th>
              <th>Ordered</th>
              <th>Items</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {purchases.map((po) => (
              <tr key={po.id}>
                <td>{po.vendor_name}</td>
                <td>
                  <span className={`admin-badge admin-badge-${po.status === "received" ? "active" : "warning"}`}>
                    {po.status}
                  </span>
                </td>
                <td>₹{po.total}</td>
                <td>{new Date(po.ordered_at).toLocaleDateString()}</td>
                <td className="cell-wrap">{po.lines.map((l) => `${productName(l.product_id)} ×${l.qty}`).join(", ")}</td>
                <td>
                  {po.status !== "received" && (
                    <motion.button
                      type="button"
                      className="admin-btn admin-btn-sm"
                      disabled={receiving === po.id}
                      onClick={() => receive(po.id)}
                      whileTap={{ scale: 0.96 }}
                    >
                      Receive stock
                    </motion.button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {purchases.length === 0 && <div className="admin-empty-state">No purchase orders yet.</div>}
      </AnimatedPanel>
    </AppShell>
  );
}
