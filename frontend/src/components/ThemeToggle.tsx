import { ThemeMode, useTheme } from "../context/ThemeContext";
import "./ThemeToggle.css";

const OPTIONS: { mode: ThemeMode; label: string; icon: string }[] = [
  { mode: "dark", label: "Dark", icon: "🌙" },
  { mode: "light", label: "Light", icon: "☀️" },
  { mode: "auto", label: "Auto", icon: "◐" },
];

interface Props {
  compact?: boolean;
}

export default function ThemeToggle({ compact = false }: Props) {
  const { mode, setMode } = useTheme();

  return (
    <div
      className={`theme-toggle${compact ? " theme-toggle-compact" : ""}`}
      role="group"
      aria-label="Theme"
    >
      {OPTIONS.map((opt) => (
        <button
          key={opt.mode}
          type="button"
          className={`theme-toggle-btn${mode === opt.mode ? " active" : ""}`}
          onClick={() => setMode(opt.mode)}
          aria-pressed={mode === opt.mode}
          title={`${opt.label} theme`}
        >
          <span className="theme-toggle-icon" aria-hidden="true">
            {opt.icon}
          </span>
          {!compact && <span className="theme-toggle-label">{opt.label}</span>}
        </button>
      ))}
    </div>
  );
}
