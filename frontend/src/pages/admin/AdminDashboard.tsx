import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../../components/layout/AppShell";
import { adminApi, PlatformStats, StoreRow } from "../../api/admin";
import { ADMIN_SHELL } from "./adminShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import AnimatedStat from "../../components/motion/AnimatedStat";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import "./admin-theme.css";

export default function AdminDashboard() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [stores, setStores] = useState<StoreRow[]>([]);
  const [healthOverall, setHealthOverall] = useState<string>("unknown");

  useEffect(() => {
    adminApi.getStats().then(setStats);
    adminApi.getStores().then((r) => setStores(r.stores));
    adminApi.getSystemHealth().then((h) => setHealthOverall(h.overall));
  }, []);

  const activeStores = stores.filter((s) => s.is_active).length;
  const recentStores = stores.slice(0, 5);

  return (
    <AppShell {...ADMIN_SHELL} title="Platform Dashboard" subtitle="Operate stores and monitor infrastructure">
      <AnimatedPanel className="admin-explainer" hover={false}>
        <h2>Neighborhood store network</h2>
        <p>
          You onboard local shops across the network. Each shopkeeper runs their own ShelfMind workspace for stock,
          sales, bills, and your AI store assistant.
        </p>
      </AnimatedPanel>

      <StaggerGrid className="admin-grid-4">
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Active stores</div>
            <AnimatedStat value={activeStores} />
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Store owners</div>
            <AnimatedStat value={stats?.active_users ?? 0} />
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Platform transactions</div>
            <AnimatedStat value={stats?.total_transactions ?? 0} />
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Platform revenue</div>
            <AnimatedStat value={stats?.platform_revenue ?? 0} prefix="₹" />
          </div>
        </StaggerItem>
      </StaggerGrid>

      <div style={{ marginTop: "1rem" }}>
      <StaggerGrid className="admin-grid-2">
        <StaggerItem>
          <AnimatedPanel>
            <div className="admin-card-title">Recent stores</div>
            {recentStores.length === 0 ? (
              <div className="admin-empty-state">No stores onboarded yet.</div>
            ) : (
              <div className="admin-recent-list">
                {recentStores.map((s) => (
                  <div key={s.id} className="admin-recent-item">
                    <div>
                      <strong>{s.name}</strong>
                      <small>{s.location}</small>
                    </div>
                    <span className={`admin-badge ${s.is_active ? "admin-badge-active" : "admin-badge-inactive"}`}>
                      {s.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                ))}
              </div>
            )}
            <Link to="/admin/stores" className="admin-btn admin-btn-ghost" style={{ marginTop: "0.75rem" }}>
              Manage stores
            </Link>
          </AnimatedPanel>
        </StaggerItem>

        <StaggerItem>
          <AnimatedPanel>
            <div className="admin-card-title">System health</div>
            <div className="admin-recent-item">
              <div>
                <strong>
                  <span className={`health-pulse ${healthOverall === "healthy" ? "healthy" : "unhealthy"}`} />
                  Overall status
                </strong>
                <small>Postgres, Redis, MinIO, Celery, Groq AI</small>
              </div>
              <span className={`admin-badge admin-badge-${healthOverall === "healthy" ? "active" : "warning"}`}>
                {healthOverall}
              </span>
            </div>
            <Link to="/admin/system" className="admin-btn admin-btn-primary" style={{ marginTop: "0.75rem" }}>
              Open system health
            </Link>
          </AnimatedPanel>
        </StaggerItem>
      </StaggerGrid>
      </div>
    </AppShell>
  );
}
