import { ReactNode } from "react";
import { motion } from "framer-motion";
import { tableRow } from "./motionPresets";
import { useReducedMotion } from "../../hooks/useReducedMotion";

interface Props {
  children: ReactNode;
  className?: string;
  dataKey?: string | number;
}

export default function AnimatedTable({ children, className = "admin-table", dataKey }: Props) {
  const reduced = useReducedMotion();

  return (
    <table className={className}>
      {children}
      {!reduced && dataKey !== undefined && (
        <tbody key={String(dataKey)}>
          {/* rows rendered by parent via AnimatedTableBody */}
        </tbody>
      )}
    </table>
  );
}

interface BodyProps {
  children: ReactNode;
  dataKey?: string | number;
}

export function AnimatedTableBody({ children, dataKey }: BodyProps) {
  const reduced = useReducedMotion();

  if (reduced) {
    return <tbody>{children}</tbody>;
  }

  return (
    <motion.tbody key={dataKey} initial="hidden" animate="visible">
      {children}
    </motion.tbody>
  );
}

interface RowProps {
  children: ReactNode;
  index: number;
  className?: string;
}

export function AnimatedTableRow({ children, index, className }: RowProps) {
  const reduced = useReducedMotion();

  if (reduced) {
    return <tr className={className}>{children}</tr>;
  }

  return (
    <motion.tr custom={index} variants={tableRow} className={className}>
      {children}
    </motion.tr>
  );
}
