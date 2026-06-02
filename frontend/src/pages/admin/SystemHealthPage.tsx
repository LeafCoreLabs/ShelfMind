import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import AppShell from "../../components/layout/AppShell";
import { adminApi } from "../../api/admin";
import { ADMIN_SHELL } from "./adminShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import "./admin-theme.css";

interface HealthCheck {
  name: string;
  status: string;
  latency_ms: number;
  detail: Record<string, unknown> | string;
}

export default function SystemHealthPage() {
  const [health, setHealth] = useState<{ overall: string; checked_at: string; checks: HealthCheck[] } | null>(null);
  const [jobMsg, setJobMsg] = useState<string | null>(null);

  const load = () => adminApi.getSystemHealth().then(setHealth);

  useEffect(() => {
    load();
  }, []);

  const runJob = async (job: "forecasts" | "signals" | "benchmarks") => {
    const res = await adminApi.triggerJob(job);
    setJobMsg(`${job} queued (${res.task_id.slice(0, 8)}…)`);
  };

  return (
    <AppShell {...ADMIN_SHELL} title="System Health" subtitle="Tech stack, database, and ML pipeline status">
      <div style={{ marginBottom: "1rem" }}>
        <button type="button" className="admin-btn admin-btn-primary" onClick={load}>
          Refresh health check
        </button>
      </div>

      {health && (
        <>
          <motion.div
            className="admin-explainer"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.35 }}
            style={{ marginBottom: "1rem" }}
          >
            <h2>
              <span className={`health-pulse ${health.overall === "healthy" ? "healthy" : "unhealthy"}`} />
              Platform {health.overall}
            </h2>
            <p>Last checked {new Date(health.checked_at).toLocaleString()}</p>
          </motion.div>

          <StaggerGrid className="admin-store-grid">
            {health.checks.map((c) => (
              <StaggerItem key={c.name}>
                <AnimatedPanel className="admin-store-card" hover>
                  <div>
                    <strong>{c.name}</strong>
                    <span className={`admin-badge admin-badge-${c.status === "healthy" ? "active" : "inactive"}`} style={{ marginLeft: 8 }}>
                      {c.status}
                    </span>
                    <div className="admin-store-card-meta">
                      <span>{c.latency_ms} ms</span>
                      <span>{typeof c.detail === "object" ? JSON.stringify(c.detail) : c.detail}</span>
                    </div>
                  </div>
                </AnimatedPanel>
              </StaggerItem>
            ))}
          </StaggerGrid>
        </>
      )}

      <AnimatedPanel style={{ marginTop: "1rem" }}>
        <div className="admin-card-title">Platform maintenance jobs</div>
        <div className="admin-job-list">
          <div className="admin-job-item">
            <div>
              <strong>Refresh demand forecasts for all shops</strong>
              <small>Retrain models using latest sales data</small>
            </div>
            <button type="button" className="admin-btn admin-btn-sm" onClick={() => runJob("forecasts")}>Run</button>
          </div>
          <div className="admin-job-item">
            <div>
              <strong>Refresh local demand signals</strong>
              <small>Weather, events, and trends for all cities</small>
            </div>
            <button type="button" className="admin-btn admin-btn-sm" onClick={() => runJob("signals")}>Run</button>
          </div>
          <div className="admin-job-item">
            <div>
              <strong>Update shop comparison benchmarks</strong>
              <small>Recalculate peer averages across the network</small>
            </div>
            <button type="button" className="admin-btn admin-btn-sm" onClick={() => runJob("benchmarks")}>Run</button>
          </div>
        </div>
        {jobMsg && <p className="admin-job-msg">{jobMsg}</p>}
      </AnimatedPanel>
    </AppShell>
  );
}
