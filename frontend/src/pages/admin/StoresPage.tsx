import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import AppShell from "../../components/layout/AppShell";
import ConfirmDialog from "../../components/admin/ConfirmDialog";
import StoreEditModal from "../../components/admin/StoreEditModal";
import { adminApi, StoreRow } from "../../api/admin";
import { ADMIN_SHELL } from "./adminShell";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import "./admin-theme.css";

type Filter = "all" | "active" | "inactive";

export default function StoresPage() {
  const [stores, setStores] = useState<StoreRow[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [editStore, setEditStore] = useState<StoreRow | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<StoreRow | null>(null);

  const load = () => adminApi.getStores().then((r) => setStores(r.stores));

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    return stores.filter((s) => {
      if (filter === "active" && !s.is_active) return false;
      if (filter === "inactive" && s.is_active) return false;
      if (search) {
        const q = search.toLowerCase();
        return s.name.toLowerCase().includes(q) || s.location.toLowerCase().includes(q);
      }
      return true;
    });
  }, [stores, filter, search]);

  const handleDeactivate = async () => {
    if (!deactivateTarget) return;
    await adminApi.deactivateStore(deactivateTarget.id);
    setDeactivateTarget(null);
    load();
  };

  return (
    <AppShell
      {...ADMIN_SHELL}
      title="Onboarded stores"
      subtitle="Manage all retail stores on the platform"
      action={
        <Link to="/admin/onboarding" className="admin-btn admin-btn-primary">
          Add store
        </Link>
      }
    >
      <div className="admin-search-row">
        <input
          className="admin-input"
          placeholder="Search by name or location…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="tab-bar">
        {(["all", "active", "inactive"] as Filter[]).map((f) => (
          <button
            key={f}
            type="button"
            className={`tab-bar-item${filter === f ? " active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {filter === f && (
              <motion.span layoutId="stores-filter" className="tab-indicator" transition={{ type: "spring", stiffness: 380, damping: 30 }} />
            )}
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f === "all" && ` (${stores.length})`}
            {f === "active" && ` (${stores.filter((s) => s.is_active).length})`}
            {f === "inactive" && ` (${stores.filter((s) => !s.is_active).length})`}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="admin-card admin-empty-state">
          {stores.length === 0 ? (
            <>
              <p>No stores onboarded yet.</p>
              <Link to="/admin/onboarding" className="admin-btn admin-btn-primary" style={{ marginTop: "1rem" }}>
                Onboard your first store
              </Link>
            </>
          ) : (
            <p>No stores match your search or filter.</p>
          )}
        </div>
      ) : (
        <StaggerGrid className="admin-store-grid">
          {filtered.map((s) => (
            <StaggerItem key={s.id}>
              <motion.div className="admin-store-card" whileHover={{ borderColor: "rgba(107, 147, 255, 0.35)" }}>
                <div className="admin-store-card-main">
                  <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", marginBottom: "0.25rem" }}>
                    <strong>{s.name}</strong>
                    <span className={`admin-badge ${s.is_active ? "admin-badge-active" : "admin-badge-inactive"}`}>
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  <small style={{ color: "var(--text-muted)" }}>{s.location}</small>
                  <div className="admin-store-card-meta">
                    <span>{s.owner_count} owner{s.owner_count !== 1 ? "s" : ""}</span>
                    <span>{s.transaction_count.toLocaleString()} transactions</span>
                    <span>₹{s.revenue.toLocaleString()} revenue</span>
                  </div>
                </div>
                <div className="admin-store-card-actions">
                  <button type="button" className="admin-btn admin-btn-sm" onClick={() => setEditStore(s)}>
                    Edit
                  </button>
                  {s.is_active && (
                    <button
                      type="button"
                      className="admin-btn admin-btn-sm admin-btn-danger"
                      onClick={() => setDeactivateTarget(s)}
                    >
                      Deactivate
                    </button>
                  )}
                </div>
              </motion.div>
            </StaggerItem>
          ))}
        </StaggerGrid>
      )}

      <StoreEditModal store={editStore} onClose={() => setEditStore(null)} onSaved={load} />

      <ConfirmDialog
        open={!!deactivateTarget}
        title="Deactivate store?"
        message={`"${deactivateTarget?.name}" will be hidden from active operations. Sales data is kept for history. You can reactivate it later from Edit.`}
        confirmLabel="Deactivate"
        danger
        onConfirm={handleDeactivate}
        onCancel={() => setDeactivateTarget(null)}
      />
    </AppShell>
  );
}
