import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { staggerContainer, staggerItem, viewportOnce } from "./motion";

export function StaggerContainer({
  children,
  className,
  viewport,
}: {
  children: ReactNode;
  className?: string;
  viewport?: typeof viewportOnce;
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="visible"
      viewport={viewport ?? viewportOnce}
      variants={staggerContainer}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div className={className} variants={staggerItem}>
      {children}
    </motion.div>
  );
}
