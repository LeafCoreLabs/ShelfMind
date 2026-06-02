import { useEffect, useRef } from "react";
import { motion, useSpring, useTransform } from "framer-motion";
import "./KpiCard.css";

interface Props {
  label: string;
  value: number | string;
  icon?: string;
  suffix?: string;
  animate?: boolean;
  delay?: number;
}

export default function KpiCard({ label, value, icon, suffix = "", animate = true, delay = 0 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const numValue = typeof value === "number" ? value : parseFloat(String(value)) || 0;
  const isNumeric = typeof value === "number" || !isNaN(numValue);

  const spring = useSpring(0, { stiffness: 60, damping: 20 });
  const display = useTransform(spring, (v) =>
    isNumeric ? Math.round(v).toLocaleString() + suffix : String(value)
  );

  useEffect(() => {
    if (animate && isNumeric) {
      const t = setTimeout(() => spring.set(numValue), delay * 100);
      return () => clearTimeout(t);
    }
  }, [numValue, animate, isNumeric, spring, delay]);

  useEffect(() => {
    if (!ref.current || !animate) return;
    import("gsap").then(({ gsap }) => {
      gsap.from(ref.current, {
        y: 30,
        opacity: 0,
        duration: 0.5,
        delay: delay * 0.1,
        ease: "power2.out",
      });
    });
  }, [animate, delay]);

  return (
    <div ref={ref} className="kpi-card glass-card">
      <div className="kpi-card-header">
        {icon && <span className="skeuo-badge">{icon}</span>}
        <span className="kpi-label">{label}</span>
      </div>
      {isNumeric && animate ? (
        <motion.span className="kpi-value">{display}</motion.span>
      ) : (
        <span className="kpi-value">{value}{suffix}</span>
      )}
    </div>
  );
}
