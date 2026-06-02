import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import AppShell from "../../components/layout/AppShell";
import AnimatedPanel from "../../components/motion/AnimatedPanel";
import { adminApi } from "../../api/admin";
import { ADMIN_SHELL } from "./adminShell";
import "./admin-theme.css";
import "./AdminPages.css";

const STEPS = ["Account", "Store Profile", "Location", "Inventory", "Preferences"];
const CATEGORIES = ["Beverages", "Snacks", "Rain Gear", "Dairy", "Bakery", "Produce"];

export default function OnboardingWizard() {
  const [draftId, setDraftId] = useState<number | null>(null);
  const [step, setStep] = useState(1);
  const [done, setDone] = useState(false);
  const [result, setResult] = useState<{ email: string; store_id: number } | null>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const [s1, setS1] = useState({ email: "", password: "", full_name: "" });
  const [s2, setS2] = useState({ store_name: "", business_type: "Retail", phone: "" });
  const [s3, setS3] = useState({ location: "Mumbai, IN", lat: "19.0760", lon: "72.8777", salary_cycle_day: "1", timezone: "Asia/Kolkata" });
  const [s4csv, setS4csv] = useState("");
  const [s5, setS5] = useState({ categories: [] as string[], notification_email: "", forecast_horizon_days: "7" });

  useEffect(() => {
    adminApi.startOnboarding().then((r) => setDraftId(r.draft_id));
  }, []);

  useEffect(() => {
    if (progressRef.current) {
      import("gsap").then(({ gsap }) => {
        gsap.to(progressRef.current, { width: `${(step / 5) * 100}%`, duration: 0.4, ease: "power2.out" });
      });
    }
  }, [step]);

  const saveAndNext = async () => {
    if (!draftId) return;
    const payloads: Record<number, Record<string, unknown>> = {
      1: s1,
      2: s2,
      3: { ...s3, lat: parseFloat(s3.lat), lon: parseFloat(s3.lon), salary_cycle_day: parseInt(s3.salary_cycle_day) },
      4: s4csv ? { csv_content: s4csv } : { skipped: true },
      5: { ...s5, forecast_horizon_days: parseInt(s5.forecast_horizon_days) },
    };
    await adminApi.saveOnboardingStep(draftId, step, payloads[step]);
    if (step < 5) setStep(step + 1);
  };

  const complete = async () => {
    if (!draftId) return;
    await adminApi.saveOnboardingStep(draftId, 5, {
      categories: s5.categories,
      notification_email: s5.notification_email || s1.email,
      forecast_horizon_days: parseInt(s5.forecast_horizon_days),
    });
    const res = await adminApi.completeOnboarding(draftId);
    setResult({ email: res.email, store_id: res.store_id });
    setDone(true);
  };

  const handleCsvFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => setS4csv(String(reader.result));
    reader.readAsText(file);
  };

  const toggleCategory = (cat: string) => {
    setS5((prev) => ({
      ...prev,
      categories: prev.categories.includes(cat)
        ? prev.categories.filter((c) => c !== cat)
        : [...prev.categories, cat],
    }));
  };

  if (done && result) {
    return (
      <AppShell {...ADMIN_SHELL} title="Onboard a local shop">
        <AnimatedPanel className="wizard-success" hover={false}>
          <h2>Store onboarded successfully</h2>
          <p style={{ color: "var(--text-muted)", margin: "0.5rem 0 1rem" }}>
            Account <strong>{result.email}</strong> created for store #{result.store_id}
          </p>
          <button className="admin-btn admin-btn-primary" onClick={() => navigate("/admin/stores")}>
            View stores
          </button>
        </AnimatedPanel>
      </AppShell>
    );
  }

  return (
    <AppShell {...ADMIN_SHELL} title="Onboard a local shop" subtitle="Add a neighborhood store and shopkeeper account">
      <AnimatedPanel hover={false}>
        <div className="wizard-progress">
          <div ref={progressRef} className="wizard-progress-bar" style={{ width: `${(step / 5) * 100}%` }} />
        </div>

        <div className="wizard-steps">
          {STEPS.map((label, i) => (
            <span key={label} className={`wizard-step-dot${i + 1 === step ? " active" : ""}${i + 1 < step ? " done" : ""}`}>
              {i + 1}. {label}
            </span>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ x: 40, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -40, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="wizard-form"
          >
            {step === 1 && (
              <>
                <label>Full name<input className="admin-input" value={s1.full_name} onChange={(e) => setS1({ ...s1, full_name: e.target.value })} /></label>
                <label>Email<input className="admin-input" type="email" value={s1.email} onChange={(e) => setS1({ ...s1, email: e.target.value })} /></label>
                <label>Password<input className="admin-input" type="password" value={s1.password} onChange={(e) => setS1({ ...s1, password: e.target.value })} /></label>
              </>
            )}
            {step === 2 && (
              <>
                <label>Store name<input className="admin-input" value={s2.store_name} onChange={(e) => setS2({ ...s2, store_name: e.target.value })} /></label>
                <label>Business type<input className="admin-input" value={s2.business_type} onChange={(e) => setS2({ ...s2, business_type: e.target.value })} /></label>
                <label>Phone<input className="admin-input" value={s2.phone} onChange={(e) => setS2({ ...s2, phone: e.target.value })} /></label>
              </>
            )}
            {step === 3 && (
              <>
                <label>Location<input className="admin-input" value={s3.location} onChange={(e) => setS3({ ...s3, location: e.target.value })} /></label>
                <label>Latitude<input className="admin-input" value={s3.lat} onChange={(e) => setS3({ ...s3, lat: e.target.value })} /></label>
                <label>Longitude<input className="admin-input" value={s3.lon} onChange={(e) => setS3({ ...s3, lon: e.target.value })} /></label>
                <label>Salary cycle day<input className="admin-input" type="number" value={s3.salary_cycle_day} onChange={(e) => setS3({ ...s3, salary_cycle_day: e.target.value })} /></label>
              </>
            )}
            {step === 4 && (
              <>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Optional: upload POS CSV to seed inventory</p>
                <input type="file" accept=".csv" onChange={(e) => e.target.files?.[0] && handleCsvFile(e.target.files[0])} />
                {s4csv && <p style={{ color: "var(--success)", fontSize: "0.85rem" }}>CSV loaded ({s4csv.split("\n").length - 1} rows)</p>}
              </>
            )}
            {step === 5 && (
              <>
                <label>Categories</label>
                <div className="category-chips">
                  {CATEGORIES.map((cat) => (
                    <button key={cat} type="button" className={`category-chip${s5.categories.includes(cat) ? " selected" : ""}`} onClick={() => toggleCategory(cat)}>
                      {cat}
                    </button>
                  ))}
                </div>
                <label>Notification email<input className="admin-input" value={s5.notification_email} onChange={(e) => setS5({ ...s5, notification_email: e.target.value })} placeholder={s1.email} /></label>
                <label>Forecast horizon (days)<input className="admin-input" type="number" value={s5.forecast_horizon_days} onChange={(e) => setS5({ ...s5, forecast_horizon_days: e.target.value })} /></label>
              </>
            )}
          </motion.div>
        </AnimatePresence>

        <div className="wizard-actions">
          <button type="button" className="admin-btn admin-btn-ghost" disabled={step === 1} onClick={() => setStep(step - 1)}>Back</button>
          {step < 5 ? (
            <button type="button" className="admin-btn admin-btn-primary" onClick={saveAndNext}>Next</button>
          ) : (
            <button type="button" className="admin-btn admin-btn-primary" onClick={complete}>Complete onboarding</button>
          )}
        </div>
      </AnimatedPanel>
    </AppShell>
  );
}
