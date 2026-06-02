import "./ShelfMindLogo.css";

interface Props {
  compact?: boolean;
}

export default function ShelfMindLogo({ compact = false }: Props) {
  return (
    <div className={`shelfmind-logo${compact ? " shelfmind-logo-compact" : ""}`}>
      <div className="shelfmind-logo-mark">
        <div className="shelfmind-logo-ring" aria-hidden="true" />
        <div className="shelfmind-logo-chip">
          <svg
            className="shelfmind-logo-svg"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <rect x="5" y="8" width="22" height="3" rx="1" fill="url(#shelfGrad)" opacity="0.9" />
            <rect x="5" y="14" width="22" height="3" rx="1" fill="url(#shelfGrad)" opacity="0.75" />
            <rect x="5" y="20" width="22" height="3" rx="1" fill="url(#shelfGrad)" opacity="0.6" />
            <rect x="7" y="5" width="4" height="5" rx="1" fill="#6B93FF" />
            <rect x="14" y="11" width="4" height="5" rx="1" fill="#A78BFA" />
            <rect x="21" y="17" width="4" height="5" rx="1" fill="#22D3EE" />
            <path
              d="M8 26 L16 22 L24 26"
              stroke="url(#shelfGrad)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <defs>
              <linearGradient id="shelfGrad" x1="5" y1="8" x2="27" y2="26" gradientUnits="userSpaceOnUse">
                <stop stopColor="#6B93FF" />
                <stop offset="0.5" stopColor="#A78BFA" />
                <stop offset="1" stopColor="#22D3EE" />
              </linearGradient>
            </defs>
          </svg>
        </div>
      </div>
      <span className="shelfmind-logo-wordmark">ShelfMind</span>
    </div>
  );
}
