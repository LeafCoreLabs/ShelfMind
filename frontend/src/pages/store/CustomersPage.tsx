import { Fragment, useEffect, useState } from "react";
import AppShell from "../../components/layout/AppShell";
import { storeApi, CustomerRow, SaleRow } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import { AnimatedTableBody, AnimatedTableRow } from "../../components/motion/AnimatedTable";
import "./store-theme.css";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<CustomerRow[]>([]);
  const [sales, setSales] = useState<SaleRow[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: "", email: "", segment: "Regular" });
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [segment, setSegment] = useState("Regular");

  const load = () => {
    storeApi.getCustomers().then((r) => setCustomers(r.customers));
    storeApi.getSales().then((r) => setSales(r.sales));
  };

  useEffect(() => {
    load();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await storeApi.createCustomer({ name, email: email || undefined, segment });
    setName("");
    setEmail("");
    await load();
  };

  const startEdit = (c: CustomerRow) => {
    setEditing(c.id);
    setEditForm({ name: c.name, email: c.email ?? "", segment: c.segment });
  };

  const saveEdit = async (id: number) => {
    await storeApi.updateCustomer(id, editForm);
    setEditing(null);
    await load();
  };

  const remove = async (id: number) => {
    await storeApi.deleteCustomer(id);
    await load();
  };

  const customerSales = (id: number) => sales.filter((s) => s.customer_id === id).slice(0, 5);

  return (
    <AppShell {...STORE_SHELL} title="Regulars" subtitle="Neighborhood customers and their purchase history">
      <AnimatedPanel style={{ marginBottom: "1rem" }}>
        <div className="admin-card-title">Add regular</div>
        <form onSubmit={create} className="customer-add-row">
          <label>
            Name
            <input className="admin-input" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label>
            Email
            <input className="admin-input" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Segment
            <select className="admin-input" value={segment} onChange={(e) => setSegment(e.target.value)}>
              <option>Regular</option>
              <option>VIP</option>
              <option>New</option>
            </select>
          </label>
          <button type="submit" className="admin-btn admin-btn-primary">Add</button>
        </form>
      </AnimatedPanel>

      <AnimatedPanel className="admin-card store-table-wrap">
        <table className="admin-table admin-table-modern">
          <thead>
            <tr>
              <th>Name</th>
              <th>Segment</th>
              <th>Total spent</th>
              <th>Last visit</th>
              <th></th>
            </tr>
          </thead>
          <AnimatedTableBody dataKey={customers.length}>
            {customers.map((c, i) => (
              <Fragment key={c.id}>
                <AnimatedTableRow index={i}>
                  <td>
                    {editing === c.id ? (
                      <input className="admin-input admin-input-compact" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                    ) : (
                      <button type="button" className="link-btn" onClick={() => setExpanded(expanded === c.id ? null : c.id)}>
                        {c.name}
                      </button>
                    )}
                  </td>
                  <td>
                    {editing === c.id ? (
                      <select className="admin-input admin-input-compact" value={editForm.segment} onChange={(e) => setEditForm({ ...editForm, segment: e.target.value })}>
                        <option>Regular</option>
                        <option>VIP</option>
                        <option>New</option>
                      </select>
                    ) : (
                      <span className="admin-badge admin-badge-active">{c.segment}</span>
                    )}
                  </td>
                  <td>₹{c.total_spent.toLocaleString()}</td>
                  <td>{c.last_purchase_at ? new Date(c.last_purchase_at).toLocaleDateString() : "—"}</td>
                  <td>
                    {editing === c.id ? (
                      <>
                        <button type="button" className="admin-btn admin-btn-sm" onClick={() => saveEdit(c.id)}>Save</button>
                        <button type="button" className="admin-btn admin-btn-sm admin-btn-ghost" onClick={() => setEditing(null)}>Cancel</button>
                      </>
                    ) : (
                      <>
                        <button type="button" className="admin-btn admin-btn-sm admin-btn-ghost" onClick={() => startEdit(c)}>Edit</button>
                        <button type="button" className="admin-btn admin-btn-sm admin-btn-ghost" onClick={() => remove(c.id)}>Delete</button>
                      </>
                    )}
                  </td>
                </AnimatedTableRow>
                {expanded === c.id && (
                  <tr key={`${c.id}-history`}>
                    <td colSpan={5}>
                      <div className="purchase-history">
                        <strong>Recent purchases</strong>
                        {customerSales(c.id).length === 0 ? (
                          <p>No linked sales yet.</p>
                        ) : (
                          <ul>
                            {customerSales(c.id).map((s) => (
                              <li key={s.id}>
                                {new Date(s.sold_at).toLocaleDateString()} — {s.product_name} × {s.quantity} (₹{s.total})
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </AnimatedTableBody>
        </table>
        {customers.length === 0 && <div className="admin-empty-state">No regulars yet.</div>}
      </AnimatedPanel>
    </AppShell>
  );
}
