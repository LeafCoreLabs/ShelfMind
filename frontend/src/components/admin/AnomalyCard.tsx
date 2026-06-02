import "./AdminComponents.css";

interface Anomaly {
  id: string;
  severity: string;
  title: string;
  delta_pct?: number;
  store_name?: string;
  category?: string;
  signal_cause?: string;
  recommended_action?: string;
}

export default function AnomalyCard({ anomaly }: { anomaly: Anomaly }) {
  return (
    <div className={`anomaly-card glass-card severity-${anomaly.severity}`}>
      <div className="anomaly-card-header">
        <span className={`severity-pill ${anomaly.severity}`}>{anomaly.severity}</span>
        {anomaly.delta_pct != null && (
          <strong className={anomaly.delta_pct >= 0 ? "up" : "down"}>
            {anomaly.delta_pct > 0 ? "+" : ""}{anomaly.delta_pct}%
          </strong>
        )}
      </div>
      <h4>{anomaly.title}</h4>
      {anomaly.signal_cause && <p className="anomaly-cause">{anomaly.signal_cause}</p>}
      {anomaly.recommended_action && (
        <p className="anomaly-action">→ {anomaly.recommended_action}</p>
      )}
    </div>
  );
}
