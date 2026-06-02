import { motion } from "framer-motion";
import { StoreWeather } from "../../../api/store";
import "./WeatherWidget.css";

interface Props {
  weather: StoreWeather | null;
  onRefresh?: () => void;
  refreshing?: boolean;
  compact?: boolean;
}

function formatDay(dateStr: string) {
  const d = new Date(dateStr + "T12:00:00");
  return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric" });
}

export default function WeatherWidget({ weather, onRefresh, refreshing, compact }: Props) {
  if (!weather) {
    return <p className="weather-empty">Loading local weather…</p>;
  }

  const { current, daily, source, location } = weather;

  if (compact) {
    return (
      <motion.div className="weather-compact" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <span className="weather-temp">{Math.round(current.temp_c ?? 0)}°C</span>
        <span className="weather-cond">{current.condition}</span>
        <span className="weather-meta">{location} · {source === "open-meteo" ? "Open-Meteo" : source === "openweather" ? "OpenWeather" : "demo"}</span>
      </motion.div>
    );
  }

  return (
    <motion.div className="weather-widget" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className="weather-current">
        <div>
          <div className="weather-temp-lg">{Math.round(current.temp_c ?? 0)}°C</div>
          <div className="weather-cond">{current.condition}</div>
          <div className="weather-meta">
            {location}
            {current.humidity_pct != null && ` · ${current.humidity_pct}% humidity`}
          </div>
        </div>
        {onRefresh && (
          <motion.button
            type="button"
            className="admin-btn admin-btn-sm admin-btn-ghost"
            onClick={onRefresh}
            disabled={refreshing}
            animate={refreshing ? { rotate: 360 } : { rotate: 0 }}
            transition={refreshing ? { repeat: Infinity, duration: 1, ease: "linear" } : {}}
          >
            {refreshing ? "Updating…" : "Refresh"}
          </motion.button>
        )}
      </div>

      <div className="weather-daily">
        {daily.slice(0, 5).map((d, i) => (
          <motion.div
            key={d.date}
            className="weather-day"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <span className="weather-day-name">{formatDay(d.date)}</span>
            <span className="weather-day-cond">{d.condition}</span>
            <span className="weather-day-temp">
              {Math.round(d.temp_max_c ?? 0)}° / {Math.round(d.temp_min_c ?? 0)}°
            </span>
            {(d.precip_mm ?? 0) > 0 && <span className="weather-rain">{d.precip_mm}mm rain</span>}
          </motion.div>
        ))}
      </div>

      {weather.retail_signals.length > 0 && (
        <div className="weather-retail-hints">
          {weather.retail_signals.map((s) => (
            <div key={s.category} className="weather-hint">
              <strong>{s.category}</strong> — {s.description}
            </div>
          ))}
        </div>
      )}

      <p className="weather-source">
        Live forecast via {source === "open-meteo" ? "Open-Meteo" : source === "openweather" ? "OpenWeather" : "demo data"}
        {weather.fetched_at && ` · updated ${new Date(weather.fetched_at).toLocaleTimeString()}`}
      </p>
    </motion.div>
  );
}
