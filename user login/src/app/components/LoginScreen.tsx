import { useState } from "react";

const TOKENS = {
  bg: "#0B1020",
  bgAlt: "#0E1426",
  text: "#E7EBF5",
  textMuted: "#9AA3B8",
  accent: "#6B93FF",
  accentGlow: "rgba(107,147,255,0.40)",
  surface: "rgba(255,255,255,0.05)",
  glassBorder: "rgba(255,255,255,0.10)",
  glassHighlight: "rgba(255,255,255,0.06)",
  danger: "#F87171",
};

const glassCard = {
  background: "rgba(255,255,255,0.05)",
  border: "1px solid rgba(255,255,255,0.10)",
  borderRadius: "16px",
  backdropFilter: "blur(18px)",
  WebkitBackdropFilter: "blur(18px)",
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 32px rgba(0,0,0,0.45)",
};

const skeuoBadge = {
  width: 40,
  height: 40,
  borderRadius: 12,
  background: "linear-gradient(145deg, rgba(255,255,255,0.12), rgba(255,255,255,0.03))",
  border: "1px solid rgba(255,255,255,0.10)",
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 12px rgba(0,0,0,0.35)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: 18,
  flexShrink: 0,
};

const gradientText = {
  background: "linear-gradient(120deg, #6B93FF, #A78BFA 60%, #22D3EE)",
  WebkitBackgroundClip: "text",
  WebkitTextFillColor: "transparent",
  backgroundClip: "text",
};

type Role = "admin" | "owner";

function FeatureCard({ icon, title, sub }: { icon: string; title: string; sub: string }) {
  return (
    <div
      style={{
        ...glassCard,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        gap: 14,
      }}
    >
      <div style={skeuoBadge}>{icon}</div>
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: TOKENS.text, marginBottom: 2 }}>{title}</div>
        <div style={{ fontSize: 12, color: TOKENS.textMuted, lineHeight: 1.5 }}>{sub}</div>
      </div>
    </div>
  );
}

function StatPill({ value, label }: { value: string; label: string }) {
  return (
    <div
      style={{
        ...glassCard,
        flex: 1,
        padding: "14px 10px",
        textAlign: "center",
      }}
    >
      <div style={{ ...gradientText, fontSize: 20, fontWeight: 700, marginBottom: 4 }}>{value}</div>
      <div style={{ fontSize: 11, color: TOKENS.textMuted, lineHeight: 1.4 }}>{label}</div>
    </div>
  );
}

function InputField({
  type = "text",
  placeholder,
}: {
  type?: string;
  placeholder: string;
}) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      style={{
        width: "100%",
        height: 42,
        padding: "10px 14px",
        borderRadius: 10,
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.10)",
        backdropFilter: "blur(8px)",
        WebkitBackdropFilter: "blur(8px)",
        color: TOKENS.text,
        fontSize: 14,
        outline: "none",
        fontFamily: "DM Sans, sans-serif",
        boxSizing: "border-box",
      }}
    />
  );
}

function RoleCard({
  role,
  icon,
  title,
  subtitle,
  hint,
  selected,
  emailPlaceholder,
  onSelect,
}: {
  role: Role;
  icon: string;
  title: string;
  subtitle: string;
  hint: string;
  selected: boolean;
  emailPlaceholder: string;
  onSelect: () => void;
}) {
  return (
    <div
      onClick={!selected ? onSelect : undefined}
      style={{
        ...glassCard,
        padding: 20,
        border: selected
          ? "2px solid #6B93FF"
          : "1px solid rgba(255,255,255,0.10)",
        boxShadow: selected
          ? "inset 0 1px 0 rgba(255,255,255,0.06), 0 8px 32px rgba(107,147,255,0.40)"
          : glassCard.boxShadow,
        cursor: selected ? "default" : "pointer",
        transition: "all 0.25s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div style={skeuoBadge}>{icon}</div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 600, color: TOKENS.text }}>{title}</div>
          <div style={{ fontSize: 13, color: TOKENS.textMuted, marginTop: 2 }}>{subtitle}</div>
        </div>
      </div>

      {selected ? (
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          <InputField type="email" placeholder={emailPlaceholder} />
          <InputField type="password" placeholder="Password" />
          <button
            style={{
              width: "100%",
              height: 42,
              padding: "10px 20px",
              borderRadius: 12,
              background: "linear-gradient(180deg, #7BA0FF, #6B93FF)",
              color: TOKENS.bg,
              fontSize: 14,
              fontWeight: 600,
              border: "none",
              cursor: "pointer",
              fontFamily: "DM Sans, sans-serif",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,0.35), 0 6px 20px rgba(107,147,255,0.40)",
              transition: "opacity 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.9")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
          >
            Sign in
          </button>
        </div>
      ) : (
        <div
          style={{
            marginTop: 12,
            textAlign: "center",
            fontSize: 12,
            color: TOKENS.textMuted,
          }}
        >
          {hint}
        </div>
      )}
    </div>
  );
}

export function LoginScreen() {
  const [selectedRole, setSelectedRole] = useState<Role>("admin");
  console.log("LoginScreen rendering, selected role:", selectedRole);

  return (
    <div
      style={{
        width: 1440,
        height: 900,
        display: "flex",
        fontFamily: "DM Sans, sans-serif",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* LEFT PANEL */}
      <div
        style={{
          width: 720,
          height: 900,
          background: "linear-gradient(160deg, #0D1430 0%, #0A0F22 55%, #0B0A1C 100%)",
          padding: "48px 40px",
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Aurora blob 1 */}
        <div
          style={{
            position: "absolute",
            top: "-8%",
            left: "-6%",
            width: 360,
            height: 360,
            borderRadius: "50%",
            background: "radial-gradient(circle, #4F7CFF, transparent 70%)",
            filter: "blur(90px)",
            opacity: 0.55,
            pointerEvents: "none",
          }}
        />
        {/* Aurora blob 2 */}
        <div
          style={{
            position: "absolute",
            bottom: "5%",
            right: "5%",
            width: 300,
            height: 300,
            borderRadius: "50%",
            background: "radial-gradient(circle, #8B5CF6, transparent 70%)",
            filter: "blur(90px)",
            opacity: 0.55,
            pointerEvents: "none",
          }}
        />
        {/* Aurora blob 3 */}
        <div
          style={{
            position: "absolute",
            top: "40%",
            right: "8%",
            width: 240,
            height: 240,
            borderRadius: "50%",
            background: "radial-gradient(circle, #22D3EE, transparent 70%)",
            filter: "blur(90px)",
            opacity: 0.35,
            pointerEvents: "none",
          }}
        />
        {/* Dot grid overlay */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px)",
            backgroundSize: "26px 26px",
            WebkitMaskImage: "radial-gradient(ellipse 70% 70% at center, black 0%, transparent 100%)",
            maskImage: "radial-gradient(ellipse 70% 70% at center, black 0%, transparent 100%)",
            pointerEvents: "none",
          }}
        />

        {/* Content */}
        <div style={{ maxWidth: 460, width: "100%", position: "relative", zIndex: 1 }}>
          {/* A: Logo lockup */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}>
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: 16,
                background: "linear-gradient(135deg, #6B93FF, #8B5CF6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: TOKENS.bg,
                fontWeight: 800,
                fontSize: 17,
                letterSpacing: "-0.02em",
                boxShadow: "0 8px 28px rgba(107,147,255,0.40)",
                flexShrink: 0,
              }}
            >
              SM
            </div>
            <span
              style={{
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                color: TOKENS.text,
              }}
            >
              SelfMind
            </span>
          </div>

          {/* B: Headline */}
          <div style={{ marginBottom: 28 }}>
            <h1
              style={{
                fontSize: 34,
                fontWeight: 700,
                lineHeight: 1.15,
                letterSpacing: "-0.03em",
                color: TOKENS.text,
                margin: 0,
              }}
            >
              Your next week's{" "}
              <span style={gradientText}>bestseller</span>
              {", "}predicted today
            </h1>
          </div>

          {/* C: Description */}
          <p
            style={{
              fontSize: 15,
              fontWeight: 400,
              lineHeight: 1.65,
              color: TOKENS.textMuted,
              margin: 0,
              marginBottom: 28,
            }}
          >
            Hyperlocal demand prediction for retail and D2C — fusing transaction history, weather, local events, and social trends into precise stocking calls.
          </p>

          {/* D: Feature cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 28 }}>
            <FeatureCard icon="🎯" title="SKU-level predictions" sub="Exact stocking recommendations with confidence scores" />
            <FeatureCard icon="📊" title="Buying-trend heatmaps" sub="Peak purchase windows animated by category" />
            <FeatureCard icon="💬" title="Natural-language queries" sub="Ask what to stock — AI answers with rationale" />
          </div>

          {/* E: Stat pills */}
          <div style={{ display: "flex", gap: 12, marginBottom: 28 }}>
            <StatPill value="340%" label="demand lift detected" />
            <StatPill value="SKU" label="level forecasts" />
            <StatPill value="AI" label="powered queries" />
          </div>

          {/* F: Badge pill */}
          <div style={{ display: "flex" }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "6px 14px",
                borderRadius: 999,
                fontSize: 12,
                color: TOKENS.textMuted,
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.10)",
                backdropFilter: "blur(10px)",
                WebkitBackdropFilter: "blur(10px)",
              }}
            >
              Team Toxicos.exe
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT PANEL */}
      <div
        style={{
          width: 720,
          height: 900,
          background: TOKENS.bgAlt,
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 32,
          boxSizing: "border-box",
          overflow: "hidden",
        }}
      >
        {/* Radial glow */}
        <div
          style={{
            position: "absolute",
            top: "20%",
            left: "70%",
            transform: "translate(-50%, -50%)",
            width: 500,
            height: 500,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(107,147,255,0.10) 0%, transparent 55%)",
            pointerEvents: "none",
          }}
        />

        <div style={{ width: "100%", maxWidth: 420, position: "relative", zIndex: 1 }}>
          {/* Header */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: TOKENS.text, marginBottom: 6 }}>
              Welcome back
            </div>
            <div style={{ fontSize: 14, color: TOKENS.textMuted }}>
              Select your role and sign in
            </div>
          </div>

          {/* Role cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 380 }}>
            <RoleCard
              role="admin"
              icon="⚙️"
              title="Admin"
              subtitle="Platform management & onboarding"
              hint="Click to sign in as admin"
              selected={selectedRole === "admin"}
              emailPlaceholder="Email"
              onSelect={() => setSelectedRole("admin")}
            />
            <RoleCard
              role="owner"
              icon="🏪"
              title="Store Owner"
              subtitle="Dashboard, forecasts & inventory"
              hint="Click to sign in as store owner"
              selected={selectedRole === "owner"}
              emailPlaceholder="owner@shelfmind.com"
              onSelect={() => setSelectedRole("owner")}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
