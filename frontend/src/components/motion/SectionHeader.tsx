import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useReducedMotion } from "../../hooks/useReducedMotion";

interface Props {
  title: string;
  subtitle?: string;
}

export default function SectionHeader({ title, subtitle }: Props) {
  const lineRef = useRef<HTMLSpanElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    if (reduced || !lineRef.current) return;
    gsap.fromTo(lineRef.current, { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power2.out", transformOrigin: "left" });
  }, [title, reduced]);

  return (
    <div className="section-header">
      <h2 className="section-header-title">{title}</h2>
      {subtitle && <p className="section-header-sub">{subtitle}</p>}
      <span ref={lineRef} className="section-header-line" aria-hidden="true" />
    </div>
  );
}
