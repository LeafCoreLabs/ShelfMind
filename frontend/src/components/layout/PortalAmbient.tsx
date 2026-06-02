import { useEffect, useRef } from "react";
import gsap from "gsap";
import { useReducedMotion } from "../../hooks/useReducedMotion";
import "./PortalAmbient.css";

interface Props {
  variant: "admin" | "store";
  containerRef: React.RefObject<HTMLElement | null>;
}

export default function PortalAmbient({ variant, containerRef }: Props) {
  const glowRef = useRef<HTMLDivElement>(null);
  const orb1Ref = useRef<HTMLDivElement>(null);
  const orb2Ref = useRef<HTMLDivElement>(null);
  const rafRef = useRef(0);
  const targetRef = useRef({ x: 0, y: 0 });
  const reduced = useReducedMotion();

  useEffect(() => {
    const container = containerRef.current;
    const glow = glowRef.current;
    if (!container || !glow || reduced) return;

    const onMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      targetRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };

    const tick = () => {
      glow.style.setProperty("--mx", `${targetRef.current.x}px`);
      glow.style.setProperty("--my", `${targetRef.current.y}px`);
      rafRef.current = requestAnimationFrame(tick);
    };

    container.addEventListener("mousemove", onMove);
    rafRef.current = requestAnimationFrame(tick);

    const ctx = gsap.context(() => {
      if (orb1Ref.current) {
        gsap.to(orb1Ref.current, { x: 30, y: -20, duration: 8, repeat: -1, yoyo: true, ease: "sine.inOut" });
      }
      if (orb2Ref.current) {
        gsap.to(orb2Ref.current, { x: -25, y: 15, duration: 10, repeat: -1, yoyo: true, ease: "sine.inOut" });
      }
    });

    return () => {
      container.removeEventListener("mousemove", onMove);
      cancelAnimationFrame(rafRef.current);
      ctx.revert();
    };
  }, [containerRef, reduced]);

  return (
    <div className={`portal-ambient portal-ambient-${variant}`} aria-hidden="true">
      <div ref={orb1Ref} className="portal-orb portal-orb-1" />
      <div ref={orb2Ref} className="portal-orb portal-orb-2" />
      <div ref={glowRef} className="portal-cursor-glow" />
    </div>
  );
}
