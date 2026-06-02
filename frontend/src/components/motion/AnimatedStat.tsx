import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useReducedMotion } from "../../hooks/useReducedMotion";

interface Props {
  value: number;
  prefix?: string;
  suffix?: string;
  format?: (n: number) => string;
  className?: string;
}

export default function AnimatedStat({ value, prefix = "", suffix = "", format, className = "admin-stat-value" }: Props) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    if (reduced || !Number.isFinite(value)) {
      el.textContent = `${prefix}${format ? format(value) : value.toLocaleString()}${suffix}`;
      return;
    }

    const obj = { val: 0 };
    const tween = gsap.to(obj, {
      val: value,
      duration: 1.1,
      ease: "power2.out",
      onUpdate: () => {
        const n = Math.round(obj.val);
        el.textContent = `${prefix}${format ? format(n) : n.toLocaleString()}${suffix}`;
      },
    });

    return () => {
      tween.kill();
    };
  }, [value, prefix, suffix, format, reduced]);

  return <span ref={ref} className={className}>0</span>;
}
