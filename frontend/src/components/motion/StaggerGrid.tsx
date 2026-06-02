import { ReactNode } from "react";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "./motionPresets";
import { useReducedMotion } from "../../hooks/useReducedMotion";

interface Props {
  children: ReactNode;
  className?: string;
}

export default function StaggerGrid({ children, className = "" }: Props) {
  const reduced = useReducedMotion();

  if (reduced) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className = "" }: Props) {
  const reduced = useReducedMotion();

  if (reduced) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div className={className} variants={staggerItem}>
      {children}
    </motion.div>
  );
}
