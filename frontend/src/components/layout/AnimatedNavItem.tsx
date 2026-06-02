import { ReactNode, useRef } from "react";
import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import gsap from "gsap";
import { useReducedMotion } from "../../hooks/useReducedMotion";

interface Props {
  to: string;
  end?: boolean;
  layoutId: string;
  className?: string;
  children: ReactNode;
  onNavigate?: () => void;
}

export default function AnimatedNavItem({ to, end, layoutId, className = "admin-nav-item", children, onNavigate }: Props) {
  const ref = useRef<HTMLAnchorElement>(null);
  const reduced = useReducedMotion();

  const onEnter = () => {
    if (reduced || !ref.current) return;
    gsap.to(ref.current, { y: -1, duration: 0.2, ease: "power2.out" });
  };

  const onLeave = () => {
    if (reduced || !ref.current) return;
    gsap.to(ref.current, { y: 0, duration: 0.2, ease: "power2.out" });
  };

  return (
    <NavLink
      ref={ref}
      to={to}
      end={end}
      className={({ isActive }) => `${className}${isActive ? " active" : ""}`}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onClick={onNavigate}
    >
      {({ isActive }) => (
        <>
          {isActive && !reduced && (
            <motion.span
              layoutId={layoutId}
              className="nav-active-pill"
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
            />
          )}
          <span className="nav-item-content">{children}</span>
        </>
      )}
    </NavLink>
  );
}
