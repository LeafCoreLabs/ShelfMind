import { useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../context/AuthContext";
import BrandPanel from "../components/login/BrandPanel";
import RoleSelector from "../components/login/RoleSelector";
import LoginAmbient from "../components/login/LoginAmbient";
import ThemeToggle from "../components/ThemeToggle";
import "../styles/glass.css";
import "../styles/skeuo.css";
import "./LoginPage.css";

function LoginSkeleton() {
  return (
    <div className="login-page login-skeleton">
      <div className="login-skeleton-left">
        <div className="login-skeleton-logo" />
        <div className="login-skeleton-line lg" />
        <div className="login-skeleton-line md" />
        <div className="login-skeleton-card" />
        <div className="login-skeleton-card" />
      </div>
      <div className="login-skeleton-right">
        <div className="login-skeleton-line sm" />
        <div className="login-skeleton-line xs" />
        <div className="login-skeleton-role" />
      </div>
    </div>
  );
}

export default function LoginPage() {
  const { user, loading } = useAuth();
  const rightPanelRef = useRef<HTMLDivElement>(null);

  if (loading) return <LoginSkeleton />;
  if (user) return <Navigate to={user.role === "admin" ? "/admin" : "/store"} replace />;

  return (
    <motion.div
      className="login-page"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <div className="login-theme-toggle">
        <ThemeToggle />
      </div>
      <BrandPanel />
      <div className="login-right" ref={rightPanelRef}>
        <div className="login-right-glow" aria-hidden="true" />
        <LoginAmbient containerRef={rightPanelRef} />
        <div className="login-right-inner">
          <motion.div
            className="login-right-header"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: 0.1 }}
          >
            <h2>Welcome back</h2>
            <p className="login-sub">Select your role and sign in</p>
          </motion.div>
          <RoleSelector />
        </div>
      </div>
    </motion.div>
  );
}
