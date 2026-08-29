import { motion } from "framer-motion";
import type { ReactNode } from "react";

import { fadeUp, viewportOnce } from "./motion";

export function AnimatedSection({
  children,
  className,
  delay,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      variants={fadeUp}
      {...(delay !== undefined ? { transition: { delay } } : {})}
    >
      {children}
    </motion.div>
  );
}
