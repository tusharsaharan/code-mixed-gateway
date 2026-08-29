import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect } from "react";

import { EASE } from "./motion";

const defaultFormat = (v: number) => Math.round(v).toLocaleString();

export function AnimatedNumber({
  value,
  format = defaultFormat,
  duration = 1.2,
  className,
}: {
  value: number;
  format?: (v: number) => string;
  duration?: number;
  className?: string;
}) {
  const mv = useMotionValue(0);
  const display = useTransform(mv, format);

  useEffect(() => {
    const controls = animate(mv, value, { duration, ease: EASE });
    return () => controls.stop();
  }, [value, duration, mv]);

  return <motion.span className={className}>{display}</motion.span>;
}
