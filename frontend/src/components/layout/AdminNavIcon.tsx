import { AdminNavIcon as IconType } from "../../pages/admin/adminNav";
import "./AdminNavIcon.css";

const PATHS: Record<IconType, React.ReactNode> = {
  dashboard: (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="2" width="7" height="7" rx="1.5" />
      <rect x="11" y="2" width="7" height="7" rx="1.5" />
      <rect x="2" y="11" width="7" height="7" rx="1.5" />
      <rect x="11" y="11" width="7" height="7" rx="1.5" />
    </svg>
  ),
  stores: (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M3 8l7-5 7 5v9H3V8z" strokeLinejoin="round" />
      <path d="M7 17v-5h6v5" />
    </svg>
  ),
  onboard: (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="10" cy="10" r="7" />
      <path d="M10 6v8M6 10h8" strokeLinecap="round" />
    </svg>
  ),
  users: (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="6" r="3" />
      <path d="M2 17c0-3.3 2.7-5 6-5s6 1.7 6 5" strokeLinecap="round" />
      <circle cx="14" cy="7" r="2" />
      <path d="M16 17c0-2-1.2-3.5-3-3.5" strokeLinecap="round" />
    </svg>
  ),
  system: (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="3" y="4" width="14" height="12" rx="2" />
      <path d="M7 8h6M7 12h4" strokeLinecap="round" />
    </svg>
  ),
};

export default function AdminNavIconSvg({ icon }: { icon: IconType }) {
  return <span className="admin-nav-icon">{PATHS[icon]}</span>;
}
