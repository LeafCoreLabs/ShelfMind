import { useCallback, useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import "./RoleSelector.css";

type Role = "admin" | "user";

const ROLES: {
  id: Role;
  title: string;
  subtitle: string;
  panelTitle: string;
  panelDesc: string;
  icon: string;
  email: string;
  emailPlaceholder: string;
  password: string;
}[] = [
  {
    id: "admin",
    title: "Admin",
    subtitle: "Platform ops",
    panelTitle: "Admin sign in",
    panelDesc: "Manage users, stores, and onboarding",
    icon: "⚙️",
    email: "admin@shelfmind.com",
    emailPlaceholder: "Email",
    password: "admin123",
  },
  {
    id: "user",
    title: "Store Owner",
    subtitle: "Your dashboard",
    panelTitle: "Store owner sign in",
    panelDesc: "Run your local shop — stock, sales, bills, and your AI store assistant",
    icon: "🏪",
    email: "owner@shelfmind.com",
    emailPlaceholder: "owner@shelfmind.com",
    password: "user123",
  },
];

function getRoleData(role: Role) {
  return ROLES.find((r) => r.id === role)!;
}

export default function RoleSelector() {
  const [selected, setSelected] = useState<Role>("admin");
  const [email, setEmail] = useState(getRoleData("admin").email);
  const [password, setPassword] = useState(getRoleData("admin").password);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const tabsRef = useRef<HTMLDivElement>(null);
  const indicatorRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const fieldRefs = useRef<(HTMLDivElement | null)[]>([]);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  const switchingRef = useRef(false);
  const navigate = useNavigate();
  const { login, clearSession } = useAuth();

  const activeRole = getRoleData(selected);
  const reducedMotion = useRef(
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  const moveIndicator = useCallback((index: number, animate = true) => {
    const tab = tabRefs.current[index];
    const tabs = tabsRef.current;
    const indicator = indicatorRef.current;
    if (!tab || !tabs || !indicator) return;

    const tabsRect = tabs.getBoundingClientRect();
    const tabRect = tab.getBoundingClientRect();
    const x = tabRect.left - tabsRect.left;
    const width = tabRect.width;

    if (reducedMotion.current || !animate) {
      gsap.set(indicator, { x, width });
      return;
    }

    gsap.to(indicator, {
      x,
      width,
      duration: 0.55,
      ease: "power3.inOut",
    });
  }, []);

  const animateFormIn = useCallback(() => {
    const fields = fieldRefs.current.filter(Boolean);
    const targets = [...fields, submitRef.current].filter(Boolean);

    if (reducedMotion.current) {
      gsap.set(targets, { opacity: 1, y: 0, scale: 1 });
      return;
    }

    gsap.fromTo(
      targets,
      { opacity: 0, y: 18, scale: 0.97 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.45,
        stagger: 0.07,
        ease: "power3.out",
        overwrite: "auto",
      }
    );
  }, []);

  const handleTabSelect = (role: Role, index: number) => {
    if (role === selected || switchingRef.current) return;
    switchingRef.current = true;
    setError(null);
    moveIndicator(index);

    const roleData = getRoleData(role);

    if (reducedMotion.current) {
      setSelected(role);
      setEmail(roleData.email);
      setPassword(roleData.password);
      switchingRef.current = false;
      return;
    }

    const tl = gsap.timeline({
      onComplete: () => {
        switchingRef.current = false;
      },
    });

    tl.to([panelRef.current, headerRef.current], {
      opacity: 0.5,
      y: 10,
      duration: 0.22,
      ease: "power2.in",
    })
      .call(() => {
        setSelected(role);
        setEmail(roleData.email);
        setPassword(roleData.password);
      })
      .to([panelRef.current, headerRef.current], {
        opacity: 1,
        y: 0,
        duration: 0.38,
        ease: "power3.out",
      })
      .call(animateFormIn, undefined, "-=0.12");
  };

  useEffect(() => {
    moveIndicator(0, false);

    const ctx = gsap.context(() => {
      if (reducedMotion.current) {
        gsap.set([containerRef.current, panelRef.current], { opacity: 1, y: 0 });
        return;
      }

      gsap.from(containerRef.current, {
        opacity: 0,
        y: 28,
        duration: 0.65,
        ease: "power3.out",
      });

      gsap.from(panelRef.current, {
        opacity: 0,
        y: 32,
        scale: 0.96,
        duration: 0.7,
        delay: 0.15,
        ease: "power3.out",
      });

      gsap.from(tabRefs.current, {
        opacity: 0,
        x: 24,
        duration: 0.5,
        stagger: 0.1,
        delay: 0.08,
        ease: "power2.out",
      });

      animateFormIn();
    }, containerRef);

    return () => ctx.revert();
  }, [animateFormIn, moveIndicator]);

  useEffect(() => {
    const cleanups: Array<() => void> = [];

    tabRefs.current.forEach((tab, i) => {
      if (!tab) return;
      const onEnter = () => {
        if (ROLES[i].id === selected || reducedMotion.current) return;
        gsap.to(tab, { y: -2, duration: 0.25, ease: "power2.out" });
      };
      const onLeave = () => {
        gsap.to(tab, { y: 0, duration: 0.25, ease: "power2.out" });
      };
      tab.addEventListener("mouseenter", onEnter);
      tab.addEventListener("mouseleave", onLeave);
      cleanups.push(() => {
        tab.removeEventListener("mouseenter", onEnter);
        tab.removeEventListener("mouseleave", onLeave);
      });
    });

    return () => cleanups.forEach((fn) => fn());
  }, [selected]);

  useEffect(() => {
    if (!error || !errorRef.current || reducedMotion.current) return;
    gsap.fromTo(
      errorRef.current,
      { opacity: 0, x: -8 },
      { opacity: 1, x: 0, duration: 0.4, ease: "power2.out" }
    );
  }, [error]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    if (!reducedMotion.current && submitRef.current) {
      gsap.to(submitRef.current, { scale: 0.97, duration: 0.12, yoyo: true, repeat: 1 });
    }

    try {
      const user = await login(email, password);
      if (user.role !== selected) {
        clearSession();
        setError(`This account is not a ${selected}. Try the other role.`);
        setLoading(false);
        return;
      }
      if (!reducedMotion.current && panelRef.current) {
        await gsap.to(panelRef.current, {
          opacity: 0,
          y: -12,
          scale: 1.02,
          duration: 0.35,
          ease: "power2.in",
        });
      }
      navigate(user.role === "admin" ? "/admin" : "/dashboard");
    } catch {
      setError("Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div ref={containerRef} className="role-selector">
      <div ref={tabsRef} className="role-tabs">
        <div ref={indicatorRef} className="role-tab-indicator" aria-hidden="true" />
        {ROLES.map((role, index) => (
          <button
            key={role.id}
            ref={(el) => {
              tabRefs.current[index] = el;
            }}
            type="button"
            className={`role-tab${selected === role.id ? " active" : ""}`}
            onClick={() => handleTabSelect(role.id, index)}
            aria-pressed={selected === role.id}
          >
            <span className="role-tab-icon">{role.icon}</span>
            <span className="role-tab-text">
              <strong>{role.title}</strong>
              <small>{role.subtitle}</small>
            </span>
          </button>
        ))}
      </div>

      <div ref={panelRef} className="role-panel glass-card">
        <div ref={headerRef} className="role-panel-header">
          <h3>{activeRole.panelTitle}</h3>
          <p>{activeRole.panelDesc}</p>
        </div>

        <form className="role-form" onSubmit={handleSubmit}>
          <div
            ref={(el) => {
              fieldRefs.current[0] = el;
            }}
            className="role-field"
          >
            <input
              className="glass-input"
              type="email"
              placeholder={activeRole.emailPlaceholder}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div
            ref={(el) => {
              fieldRefs.current[1] = el;
            }}
            className="role-field"
          >
            <input
              className="glass-input"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && (
            <p ref={errorRef} className="role-error">
              {error}
            </p>
          )}
          <button
            ref={submitRef}
            type="submit"
            className="skeuo-btn skeuo-btn-primary role-submit"
            disabled={loading}
          >
            {loading && <span className="role-spinner" aria-hidden="true" />}
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
