import { useEffect, useState } from "react";
import AppShell from "../../components/layout/AppShell";
import AnomalyCard from "../../components/admin/AnomalyCard";
import StoreHeatmap from "./components/StoreHeatmap";
import WeatherWidget from "./components/WeatherWidget";
import { storeApi, AdminAnomaly, StoreWeather } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import AnimatedStat from "../../components/motion/AnimatedStat";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import { AnimatedTableBody, AnimatedTableRow } from "../../components/motion/AnimatedTable";
import "./store-theme.css";
import "../../components/admin/AdminComponents.css";

interface ForecastRow {
  sku: string;
  product_name: string;
  date: string;
  predicted_qty: number;
  confidence: number;
}

interface BenchmarkRow {
  sku: string;
  local_avg_daily: number;
  peer_avg_daily: number;
  lift_pct: number;
}

export default function MLInsightsPage() {
  const [forecasts, setForecasts] = useState<ForecastRow[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkRow[]>([]);
  const [signals, setSignals] = useState<{ title: string; description: string; category: string }[]>([]);
  const [anomalies, setAnomalies] = useState<AdminAnomaly[]>([]);
  const [accuracy, setAccuracy] = useState<Record<string, unknown> | null>(null);
  const [storeLocation, setStoreLocation] = useState("");
  const [weather, setWeather] = useState<StoreWeather | null>(null);
  const [explaining, setExplaining] = useState<string | null>(null);
  const [explanations, setExplanations] = useState<Record<string, { explanation: string; recommended_action: string }>>({});

  useEffect(() => {
    storeApi.getForecasts().then((r) => setForecasts((r.forecasts as unknown as ForecastRow[]).slice(0, 15)));
    storeApi.getBenchmarks().then((r) => setBenchmarks((r.benchmarks as unknown as BenchmarkRow[]).slice(0, 10)));
    storeApi.getSignals().then((r) => {
      setSignals(r.signals.slice(0, 8) as { title: string; description: string; category: string }[]);
      setStoreLocation(String(r.store_location ?? ""));
      setWeather((r.weather as StoreWeather | null) ?? null);
    });
    storeApi.getAnomalies().then((r) => setAnomalies(r.anomalies));
    storeApi.getAccuracy().then(setAccuracy);
  }, []);

  const explain = async (id: string, title: string, detail: string) => {
    setExplaining(id);
    try {
      const result = await storeApi.explain({ title, detail, insight_type: "anomaly" });
      setExplanations((prev) => ({ ...prev, [id]: result }));
    } finally {
      setExplaining(null);
    }
  };

  return (
    <AppShell {...STORE_SHELL} title="Demand Planner" subtitle="Forecasts, local signals, and how you compare to nearby shops">
      {storeLocation && (
        <AnimatedPanel className="local-signal-banner" hover={false}>
          Planning demand for <strong>{storeLocation}</strong>
        </AnimatedPanel>
      )}

      <AnimatedPanel style={{ marginBottom: "1rem" }}>
        <div className="admin-card-title">Live weather at your shop</div>
        <WeatherWidget weather={weather} />
      </AnimatedPanel>

      <div style={{ marginBottom: "1rem" }}>
      <StaggerGrid className="admin-grid-4">
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Upcoming forecasts</div>
            <AnimatedStat value={forecasts.length} />
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Unusual demand</div>
            <AnimatedStat value={anomalies.length} />
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Local signals</div>
            <AnimatedStat value={signals.length} />
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Forecast accuracy</div>
            {accuracy?.mape != null ? (
              <AnimatedStat value={Number(accuracy.mape)} suffix="%" />
            ) : (
              <div className="admin-stat-value">—</div>
            )}
          </div>
        </StaggerItem>
      </StaggerGrid>
      </div>

      <AnimatedPanel style={{ marginBottom: "1rem" }}>
        <div className="admin-card-title">What customers buy when</div>
        <StoreHeatmap />
      </AnimatedPanel>

      <StaggerGrid className="admin-grid-2">
        <StaggerItem>
        <AnimatedPanel className="store-table-wrap">
          <div className="admin-card-title">What to stock next</div>
          <table className="admin-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Date</th>
                <th>Expected qty</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <AnimatedTableBody dataKey={forecasts.length}>
              {forecasts.map((f, i) => (
                <AnimatedTableRow key={i} index={i}>
                  <td>{f.product_name ?? f.sku}</td>
                  <td>{f.date}</td>
                  <td>{Math.round(f.predicted_qty)}</td>
                  <td>{`${Math.round(f.confidence * 100)}%`}</td>
                </AnimatedTableRow>
              ))}
            </AnimatedTableBody>
          </table>
        </AnimatedPanel>
        </StaggerItem>

        <StaggerItem>
        <AnimatedPanel className="store-table-wrap">
          <div className="admin-card-title">How you compare to nearby shops</div>
          <table className="admin-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Your daily avg</th>
                <th>Peer avg</th>
                <th>Lift</th>
              </tr>
            </thead>
            <AnimatedTableBody dataKey={benchmarks.length}>
              {benchmarks.map((b, i) => (
                <AnimatedTableRow key={i} index={i}>
                  <td>{b.sku}</td>
                  <td>{b.local_avg_daily}</td>
                  <td>{b.peer_avg_daily}</td>
                  <td className={b.lift_pct >= 0 ? "up" : "down"}>{b.lift_pct}%</td>
                </AnimatedTableRow>
              ))}
            </AnimatedTableBody>
          </table>
        </AnimatedPanel>
        </StaggerItem>
      </StaggerGrid>

      <div style={{ marginTop: "1rem" }}>
      <StaggerGrid className="admin-grid-2">
        <StaggerItem>
        <AnimatedPanel>
          <div className="admin-card-title">Local demand signals</div>
          {signals.length === 0 ? (
            <div className="admin-empty-state">No local signals right now.</div>
          ) : (
            signals.map((s, i) => (
              <div key={i} className="admin-recent-item">
                <div>
                  <strong>{s.title}</strong>
                  <small>{s.description}</small>
                </div>
                <span className="admin-badge admin-badge-active">{s.category || "local"}</span>
              </div>
            ))
          )}
        </AnimatedPanel>
        </StaggerItem>

        <StaggerItem>
        <AnimatedPanel>
          <div className="admin-card-title">Unusual demand this week</div>
          {anomalies.length === 0 ? (
            <div className="admin-empty-state">Sales look normal for your shop.</div>
          ) : (
            anomalies.slice(0, 5).map((a) => (
              <div key={a.id}>
                <AnomalyCard anomaly={a} />
                <button
                  type="button"
                  className="admin-btn admin-btn-sm admin-btn-ghost"
                  style={{ marginBottom: "0.75rem" }}
                  disabled={explaining === a.id}
                  onClick={() => explain(a.id, a.title, a.signal_cause || a.recommended_action || "")}
                >
                  {explaining === a.id ? "Explaining…" : "Explain with AI"}
                </button>
                {explanations[a.id] && (
                  <div className="admin-explain-box">
                    <p>{explanations[a.id].explanation}</p>
                    <p style={{ color: "var(--success)" }}>→ {explanations[a.id].recommended_action}</p>
                  </div>
                )}
              </div>
            ))
          )}
        </AnimatedPanel>
        </StaggerItem>
      </StaggerGrid>
      </div>
    </AppShell>
  );
}
