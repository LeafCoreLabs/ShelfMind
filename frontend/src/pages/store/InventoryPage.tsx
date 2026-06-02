import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppShell from "../../components/layout/AppShell";
import { storeApi, ProductRow } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import { AnimatedTableBody, AnimatedTableRow } from "../../components/motion/AnimatedTable";
import "./store-theme.css";

export default function InventoryPage() {
  const [products, setProducts] = useState<ProductRow[]>([]);
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [adjusting, setAdjusting] = useState<number | null>(null);

  const load = async () => {
    if (lowStockOnly) {
      const r = await storeApi.getLowStock();
      setProducts(r.products);
    } else {
      const r = await storeApi.getProducts();
      setProducts(r.products);
    }
  };

  useEffect(() => {
    load();
  }, [lowStockOnly]);

  const adjust = async (id: number, delta: number) => {
    setAdjusting(id);
    try {
      await storeApi.adjustStock(id, delta);
      await load();
    } finally {
      setAdjusting(null);
    }
  };

  const reorderHint = (p: ProductRow) => {
    if (!p.low_stock) return null;
    const need = Math.max(0, p.reorder_level - p.stock_on_hand + 5);
    return `Order ~${need} more units`;
  };

  return (
    <AppShell {...STORE_SHELL} title="Stock" subtitle="What's on your shelf and what needs reordering">
      <div className="tab-bar" style={{ marginBottom: "1rem" }}>
        {[
          { id: false, label: "All products" },
          { id: true, label: "Low stock only" },
        ].map((tab) => (
          <button
            key={String(tab.id)}
            type="button"
            className={`tab-bar-item${lowStockOnly === tab.id ? " active" : ""}`}
            onClick={() => setLowStockOnly(tab.id)}
          >
            {lowStockOnly === tab.id && (
              <motion.span layoutId="stock-filter" className="tab-indicator" transition={{ type: "spring", stiffness: 380, damping: 30 }} />
            )}
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatedPanel className="admin-card store-table-wrap" style={{ padding: 0 }}>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Category</th>
              <th>On hand</th>
              <th>Reorder at</th>
              <th>Price</th>
              <th>Hint</th>
              <th>Adjust</th>
            </tr>
          </thead>
          <AnimatedTableBody dataKey={`${lowStockOnly}-${products.length}`}>
            {products.map((p, i) => (
              <AnimatedTableRow key={p.id} index={i} className={p.low_stock ? "row-warning" : undefined}>
                <td>{p.name}</td>
                <td>{p.category}</td>
                <td>{p.stock_on_hand}</td>
                <td>{p.reorder_level}</td>
                <td>₹{p.list_price}</td>
                <td className="reorder-hint">{reorderHint(p) ?? "—"}</td>
                <td>
                  <button type="button" className="admin-btn admin-btn-sm" disabled={adjusting === p.id} onClick={() => adjust(p.id, 10)}>
                    +10
                  </button>
                  <button
                    type="button"
                    className="admin-btn admin-btn-sm admin-btn-ghost"
                    disabled={adjusting === p.id || p.stock_on_hand <= 0}
                    onClick={() => adjust(p.id, -1)}
                    style={{ marginLeft: 4 }}
                  >
                    −1
                  </button>
                </td>
              </AnimatedTableRow>
            ))}
          </AnimatedTableBody>
        </table>
        {products.length === 0 && <div className="admin-empty-state">No products match this filter.</div>}
      </AnimatedPanel>
    </AppShell>
  );
}
