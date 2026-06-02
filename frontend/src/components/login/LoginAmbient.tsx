import { useEffect, useRef } from "react";
import "./LoginAmbient.css";

interface Props {
  containerRef: React.RefObject<HTMLElement | null>;
}

export default function LoginAmbient({ containerRef }: Props) {
  const glowRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);
  const targetRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const container = containerRef.current;
    const glow = glowRef.current;
    if (!container || !glow) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) return;

    const onMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      targetRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
    };

    const onEnter = () => glow.classList.add("active");
    const onLeave = () => glow.classList.remove("active");

    const tick = () => {
      glow.style.setProperty("--mx", `${targetRef.current.x}px`);
      glow.style.setProperty("--my", `${targetRef.current.y}px`);
      rafRef.current = requestAnimationFrame(tick);
    };

    container.addEventListener("mousemove", onMove);
    container.addEventListener("mouseenter", onEnter);
    container.addEventListener("mouseleave", onLeave);
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      container.removeEventListener("mousemove", onMove);
      container.removeEventListener("mouseenter", onEnter);
      container.removeEventListener("mouseleave", onLeave);
      cancelAnimationFrame(rafRef.current);
    };
  }, [containerRef]);

  return (
    <div className="login-ambient" aria-hidden="true">
      <div ref={glowRef} className="login-ambient-glow" />
    </div>
  );
}
