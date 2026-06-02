import { ReactNode, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import gsap from "gsap";
import { useAuth } from "../../context/AuthContext";
import ShelfMindLogo from "../login/ShelfMindLogo";
import AdminNavIconSvg from "./AdminNavIcon";
import AnimatedNavItem from "./AnimatedNavItem";
import PortalAmbient from "./PortalAmbient";
import PageTransition from "../motion/PageTransition";
import { AdminNavItem } from "../../pages/admin/adminNav";
import { StoreNavSection } from "../../pages/store/storeNav";
import { useReducedMotion } from "../../hooks/useReducedMotion";
import { useBodyScrollLock } from "../../hooks/useBodyScrollLock";
import ThemeToggle from "../ThemeToggle";
import "../../styles/portal-admin.css";
import "../../styles/portal-store.css";
import "./AppShell.css";

type ShellNavItem = { to: string; label: string; icon?: string } | AdminNavItem;

interface Props {
  children: ReactNode;
  nav?: ShellNavItem[];
  navSections?: StoreNavSection[];
  title: string;
  subtitle?: string;
  action?: ReactNode;
  variant?: "default" | "admin" | "store";
}

function isAdminNavItem(item: ShellNavItem): item is AdminNavItem {
  return (
    "icon" in item &&
    typeof item.icon === "string" &&
    ["dashboard", "stores", "onboard", "users", "system"].includes(item.icon)
  );
}

export default function AppShell({ children, nav = [], navSections, title, subtitle, action, variant = "default" }: Props) {
  const { user, logout } = useAuth();
  const isAdmin = variant === "admin";
  const isStore = variant === "store";
  const useModernNav = isAdmin || isStore;
  const reduced = useReducedMotion();
  const [drawerOpen, setDrawerOpen] = useState(false);
  useBodyScrollLock(drawerOpen);
  const mainRef = useRef<HTMLElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const brandRef = useRef<HTMLDivElement>(null);
  const footerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (reduced || !sidebarRef.current) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(sidebarRef.current, { x: -24, opacity: 0 }, { x: 0, opacity: 1, duration: 0.55, ease: "power3.out" });
      if (brandRef.current) {
        gsap.fromTo(brandRef.current, { opacity: 0, y: -8 }, { opacity: 1, y: 0, duration: 0.4, delay: 0.1 });
      }
      gsap.from(".sidebar-nav .admin-nav-item", {
        opacity: 0,
        y: 10,
        stagger: 0.04,
        duration: 0.35,
        delay: 0.15,
        ease: "power2.out",
      });
      if (footerRef.current) {
        gsap.fromTo(footerRef.current, { opacity: 0 }, { opacity: 1, duration: 0.4, delay: 0.45 });
      }
    }, sidebarRef);
    return () => ctx.revert();
  }, [reduced]);

  const portalClass = isAdmin ? " portal-admin" : isStore ? " portal-store" : "";
  const layoutId = isAdmin ? "admin-nav-pill" : "store-nav-pill";

  const sidebarContent = (
    <>
      <div className="sidebar-brand" ref={brandRef}>
        {useModernNav ? <ShelfMindLogo compact /> : (
          <>
            <span className="brand-logo">SM</span>
            <div><strong>ShelfMind</strong><small>Local commerce platform</small></div>
          </>
        )}
      </div>
      <nav className="sidebar-nav">
        {navSections
          ? navSections.map((section) => (
              <div key={section.title} className="nav-section">
                <div className="nav-section-title">{section.title}</div>
                {section.items.map((item) => (
                  <AnimatedNavItem
                    key={item.to}
                    to={item.to}
                    end={item.to === "/store"}
                    layoutId={layoutId}
                    onNavigate={() => setDrawerOpen(false)}
                  >
                    <span className="nav-emoji">{item.icon}</span>
                    {item.label}
                  </AnimatedNavItem>
                ))}
              </div>
            ))
          : nav.map((item) => (
              <AnimatedNavItem
                key={item.to}
                to={item.to}
                end={item.to === "/admin" || item.to === "/store" || item.to === "/dashboard"}
                layoutId={layoutId}
                onNavigate={() => setDrawerOpen(false)}
              >
                {isAdmin && isAdminNavItem(item) ? (
                  <AdminNavIconSvg icon={item.icon} />
                ) : (
                  <span className="nav-emoji">{"icon" in item ? item.icon : ""}</span>
                )}
                {item.label}
              </AnimatedNavItem>
            ))}
      </nav>
      <div className="sidebar-footer" ref={footerRef}>
        <div className="user-chip glass-card">
          <span className="user-avatar">{user?.full_name?.[0] || "?"}</span>
          <div>
            <strong>{user?.full_name}</strong>
            <small>{user?.role === "user" ? "store owner" : user?.role}</small>
          </div>
        </div>
        <button
          className={useModernNav ? "admin-btn admin-btn-ghost logout-btn" : "skeuo-btn skeuo-btn-ghost logout-btn"}
          onClick={logout}
        >
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <div className={`app-shell${isAdmin ? " app-shell-admin" : ""}${isStore ? " app-shell-store" : ""}${portalClass}`}>
      <aside ref={sidebarRef} className={`sidebar glass-panel sidebar-desktop${isAdmin ? " sidebar-admin" : ""}${isStore ? " sidebar-store" : ""}`}>
        {sidebarContent}
      </aside>

      <AnimatePresence>
        {drawerOpen && (
          <>
            <motion.div
              className="sidebar-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDrawerOpen(false)}
            />
            <motion.aside
              className={`sidebar glass-panel sidebar-drawer${portalClass}`}
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 340, damping: 32 }}
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <main ref={mainRef} className="main-content">
        {useModernNav && <PortalAmbient variant={isAdmin ? "admin" : "store"} containerRef={mainRef} />}
        <header className={`top-bar glass-panel${useModernNav ? " top-bar-admin" : ""}`}>
          <div className="top-bar-left">
            {useModernNav && (
              <button type="button" className="mobile-menu-btn" onClick={() => setDrawerOpen(true)} aria-label="Open menu">
                <span /><span /><span />
              </button>
            )}
            <motion.div key={title} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
              <h1>{title}</h1>
              {subtitle && <p className="top-subtitle">{subtitle}</p>}
            </motion.div>
          </div>
          <div className="top-bar-right">
            <ThemeToggle compact />
            {action}
            <span className="top-date-chip">
              {new Date().toLocaleDateString("en-IN", { weekday: "long", month: "long", day: "numeric" })}
            </span>
          </div>
        </header>
        <div className="page-content">
          <PageTransition>{children}</PageTransition>
        </div>
      </main>
    </div>
  );
}
