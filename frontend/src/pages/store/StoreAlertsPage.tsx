import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppShell from "../../components/layout/AppShell";
import { storeApi } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import AnimatedStat from "../../components/motion/AnimatedStat";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import "./store-theme.css";

interface AlertRow {
  id: number;
  severity: string;
  title: string;
  message: string;
  acknowledged: boolean;
}

export default function StoreAlertsPage() {
  const [alerts, setAlerts] = useState<AlertRow[]>([]);

  const load = () => storeApi.getAlerts().then((r) => setAlerts(r.alerts));

  useEffect(() => {
    load();
  }, []);

  const ack = async (id: number) => {
    await storeApi.acknowledgeAlert(id);
    await load();
  };

  const pending = alerts.filter((a) => !a.acknowledged);

  return (
    <AppShell {...STORE_SHELL} title="Alerts" subtitle="Urgent stock and demand warnings for your shop">
      <div className="admin-stat-card" style={{ marginBottom: "1rem", maxWidth: 280 }}>
        <div className="admin-stat-label">Unacknowledged</div>
        <AnimatedStat value={pending.length} />
      </div>

      {alerts.length === 0 ? (
        <div className="admin-card admin-empty-state">No alerts for your store.</div>
      ) : (
        <StaggerGrid>
          {alerts.map((a) => (
            <StaggerItem key={a.id}>
              <motion.div
                className={`alert-card admin-card${a.severity === "critical" ? " critical" : " warning"}`}
                whileHover={{ x: 4 }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <strong>{a.title}</strong>
                    <span className={`admin-badge admin-badge-${a.severity === "critical" ? "inactive" : "warning"}`} style={{ marginLeft: 8 }}>
                      {a.severity}
                    </span>
                    <p style={{ marginTop: "0.35rem", color: "var(--text-muted)" }}>{a.message}</p>
                  </div>
                  {!a.acknowledged && (
                    <motion.button type="button" className="admin-btn admin-btn-sm" onClick={() => ack(a.id)} whileTap={{ scale: 0.95 }}>
                      Acknowledge
                    </motion.button>
                  )}
                </div>
              </motion.div>
            </StaggerItem>
          ))}
        </StaggerGrid>
      )}
    </AppShell>
  );
}
