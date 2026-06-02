export interface StoreNavItem {
  to: string;
  label: string;
  icon: string;
}

export interface StoreNavSection {
  title: string;
  items: StoreNavItem[];
}

export const STORE_NAV_SECTIONS: StoreNavSection[] = [
  {
    title: "Business Suite",
    items: [
      { to: "/store", label: "Today", icon: "📊" },
      { to: "/store/inventory", label: "Stock", icon: "📦" },
      { to: "/store/purchases", label: "Purchases", icon: "🛒" },
      { to: "/store/sales", label: "Sales & POS", icon: "🧾" },
      { to: "/store/customers", label: "Regulars", icon: "👥" },
      { to: "/store/billing", label: "Bills & GST", icon: "💳" },
      { to: "/store/reports", label: "Reports", icon: "📋" },
      { to: "/store/settings", label: "Shop Profile", icon: "⚙️" },
    ],
  },
  {
    title: "Intelligence Suite",
    items: [
      { to: "/store/alerts", label: "Alerts", icon: "🔔" },
      { to: "/store/insights", label: "Demand Planner", icon: "📈" },
      { to: "/store/ai", label: "Store Assistant", icon: "🤖" },
    ],
  },
];

export const STORE_NAV = STORE_NAV_SECTIONS.flatMap((s) => s.items);
