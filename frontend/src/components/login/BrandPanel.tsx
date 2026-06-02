import { motion } from "framer-motion";
import ShelfMindLogo from "./ShelfMindLogo";
import "./BrandPanel.css";

const SUITE_STEPS = [
  {
    icon: "🏪",
    title: "Run the counter",
    desc: "Stock, sales, purchases, bills & regulars — one daily flow",
  },
  {
    icon: "🌦️",
    title: "Read local demand",
    desc: "Live weather, neighborhood signals, and SKU forecasts",
  },
  {
    icon: "✨",
    title: "Stock with clarity",
    desc: "Ask what to order — AI answers with plain-language rationale",
  },
];

const HIGHLIGHTS = [
  "Business suite for local shops",
  "GST-aware billing",
  "Demand intelligence built in",
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.09, delayChildren: 0.05 },
  },
};

const logoVariants = {
  hidden: { opacity: 1, y: 8, scale: 0.92 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 260, damping: 24 },
  },
};

const itemVariants = {
  hidden: { opacity: 0.6, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 220, damping: 22 },
  },
};

export default function BrandPanel() {
  return (
    <div className="brand-panel">
      <div className="brand-particles" aria-hidden="true">
        {Array.from({ length: 8 }).map((_, i) => (
          <span key={i} className={`brand-particle brand-particle-${i + 1}`} />
        ))}
      </div>

      <div className="aurora aurora-1" />
      <div className="aurora aurora-2" />
      <div className="aurora aurora-3" />
      <div className="brand-grid" />

      <motion.div
        className="brand-content"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={logoVariants} className="brand-lockup">
          <ShelfMindLogo />
          <p className="brand-tagline">Business suite + intelligence for neighborhood shops</p>
        </motion.div>

        <motion.div variants={itemVariants} className="brand-headline-wrap">
          <h1 className="brand-headline">
            Run your shop. <span className="grad">Know what to stock.</span>
          </h1>
        </motion.div>

        <motion.p variants={itemVariants} className="brand-desc">
          ShelfMind combines counter operations — inventory, POS, GST bills, and reports — with live weather, demand forecasts, and a conversational store assistant for local retail.
        </motion.p>

        <motion.div variants={itemVariants} className="brand-suite-rail">
          <div className="brand-suite-line" aria-hidden="true" />
          {SUITE_STEPS.map((step, i) => (
            <motion.div
              key={step.title}
              className="suite-step glass-card"
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.35 + i * 0.1, duration: 0.4 }}
            >
              <span className="suite-step-icon">{step.icon}</span>
              <div className="suite-step-text">
                <strong>{step.title}</strong>
                <small>{step.desc}</small>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <motion.div variants={itemVariants} className="brand-highlights">
          {HIGHLIGHTS.map((label) => (
            <span key={label} className="brand-highlight-chip">
              {label}
            </span>
          ))}
        </motion.div>
      </motion.div>
    </div>
  );
}
