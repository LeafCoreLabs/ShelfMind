export type AdminNavIcon = "dashboard" | "stores" | "onboard" | "users" | "system";

export interface AdminNavItem {
  to: string;
  label: string;
  icon: AdminNavIcon;
}

export const ADMIN_NAV: AdminNavItem[] = [
  { to: "/admin", label: "Dashboard", icon: "dashboard" },
  { to: "/admin/stores", label: "Stores", icon: "stores" },
  { to: "/admin/onboarding", label: "Onboard", icon: "onboard" },
  { to: "/admin/users", label: "Users", icon: "users" },
  { to: "/admin/system", label: "System Health", icon: "system" },
];
