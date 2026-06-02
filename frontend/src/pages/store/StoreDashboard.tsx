import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../../components/layout/AppShell";
import WeatherWidget from "./components/WeatherWidget";
import { storeApi, StoreOverview, StoreWeather } from "../../api/store";
import { STORE_SHELL } from "./storeShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import AnimatedStat from "../../components/motion/AnimatedStat";
import StaggerGrid, { StaggerItem } from "../../components/motion/StaggerGrid";
import "./store-theme.css";

export default function StoreDashboard() {
  const [overview, setOverview] = useState<StoreOverview | null>(null);
  const [weather, setWeather] = useState<StoreWeather | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [aiQuery, setAiQuery] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiTip, setAiTip] = useState<string | null>(null);

  useEffect(() => {
    storeApi.getOverview().then((o) => {
      setOverview(o);
      setWeather(o.weather ?? null);
    });
  }, []);

  const refreshWeather = async () => {
    setWeatherLoading(true);
    try {
      const w = await storeApi.getWeather(true);
      setWeather(w);
    } finally {
      setWeatherLoading(false);
    }
  };

  const quickAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aiQuery.trim()) return;
    setAiLoading(true);
    try {
      const res = await storeApi.chat(aiQuery.trim());
      setAiTip(res.reply);
      setAiQuery("");
    } catch {
      setAiTip("Could not reach store assistant. Try again.");
    } finally {
      setAiLoading(false);
    }
  };

  const topSignal = overview?.top_local_signal;

  return (
    <AppShell {...STORE_SHELL} title="Today" subtitle={overview?.store_location || "Your shop at a glance"}>
      <div className="bento-grid" style={{ marginBottom: "1rem" }}>
        <div className="bento-span-8">
          <AnimatedPanel>
            <div className="admin-card-title">Local weather forecast</div>
            <WeatherWidget weather={weather} onRefresh={refreshWeather} refreshing={weatherLoading} />
          </AnimatedPanel>
        </div>
        <div className="bento-span-4">
          <AnimatedPanel>
            <div className="admin-card-title">Needs attention</div>
            {overview?.urgent_actions.length ? (
              <ul className="urgent-list">
                {overview.urgent_actions.map((a) => (
                  <li key={a.type}>
                    <Link to={a.href}>{a.label}</Link>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="admin-empty-state">All clear — your shop is running smoothly.</div>
            )}
          </AnimatedPanel>
        </div>
      </div>

      {topSignal && (
        <AnimatedPanel className="local-signal-banner" hover={false}>
          <strong>{topSignal.title}</strong>
          <span>{topSignal.description}</span>
        </AnimatedPanel>
      )}

      <AnimatedPanel className="ai-glow-panel admin-card" hover={false} style={{ marginBottom: "1rem" }}>
        <div className="admin-card-title">Ask your store assistant</div>
        <form onSubmit={quickAsk} className="quick-ask-form">
          <input
            className="admin-input"
            placeholder="e.g. Hi, today's sales, or what to stock this weekend"
            value={aiQuery}
            onChange={(e) => setAiQuery(e.target.value)}
            disabled={aiLoading}
          />
          <button type="submit" className="admin-btn admin-btn-primary" disabled={aiLoading}>
            {aiLoading ? "…" : "Ask"}
          </button>
        </form>
        {aiTip && <p className="admin-job-msg">{aiTip}</p>}
        <Link to="/store/ai" className="admin-btn admin-btn-ghost" style={{ marginTop: "0.5rem" }}>
          Open Store Assistant
        </Link>
      </AnimatedPanel>

      <StaggerGrid className="admin-grid-4">
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Items to restock</div>
            <AnimatedStat value={overview?.low_stock_count ?? 0} />
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">This week's sales</div>
            <AnimatedStat value={overview?.weekly_revenue ?? 0} prefix="₹" />
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Unpaid bills</div>
            <AnimatedStat value={overview?.unpaid_invoices ?? 0} />
          </div>
        </StaggerItem>
        <StaggerItem>
          <div className="admin-stat-card">
            <div className="admin-stat-label">Local demand signals</div>
            <AnimatedStat value={overview?.signals_active ?? 0} />
          </div>
        </StaggerItem>
      </StaggerGrid>

      <AnimatedPanel style={{ marginTop: "1rem" }}>
        <div className="admin-card-title">Shop snapshot</div>
        <p style={{ color: "var(--text-muted)", margin: 0 }}>
          {overview?.top_seller
            ? `Top seller this week: ${overview.top_seller}.`
            : "Record sales to see your top sellers."}{" "}
          {overview?.customer_count ?? 0} regulars · {overview?.product_count ?? 0} products in catalog.
        </p>
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
          <Link to="/store/sales" className="admin-btn admin-btn-primary">Record a sale</Link>
          <Link to="/store/inventory" className="admin-btn admin-btn-ghost">Check stock</Link>
          <Link to="/store/insights" className="admin-btn admin-btn-ghost">Demand planner</Link>
        </div>
      </AnimatedPanel>
    </AppShell>
  );
}
