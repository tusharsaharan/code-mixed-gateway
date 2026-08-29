import { motion, useMotionValue, useTransform } from "framer-motion";
import type { MouseEvent, ReactNode } from "react";

export function GlowCard({
  children,
  className = "",
  accent = false,
}: {
  children: ReactNode;
  className?: string;
  accent?: boolean;
}) {
  const mx = useMotionValue(50);
  const my = useMotionValue(50);
  const mxPct = useTransform(mx, (v) => `${v}%`);
  const myPct = useTransform(my, (v) => `${v}%`);

  function onMove(e: MouseEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    mx.set(((e.clientX - r.left) / r.width) * 100);
    my.set(((e.clientY - r.top) / r.height) * 100);
  }

  return (
    <motion.div
      onMouseMove={onMove}
      style={{ "--mx": mxPct, "--my": myPct } as unknown as Record<string, unknown>}
      whileHover={{ y: -4, transition: { duration: 0.22, ease: [0.22, 1, 0.36, 1] } }}
      whileTap={{ scale: 0.995 }}
      className={`group relative overflow-hidden rounded-2xl border bg-card p-6 shadow-[var(--shadow-soft)] transition-shadow duration-300 hover:shadow-[0_2px_4px_oklch(0.35_0.03_80/6%),0_24px_48px_oklch(0.35_0.03_80/10%)] ${
        accent ? "border-primary/30 hover:border-primary/50" : "border-border"
      } ${className}`}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 z-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        style={{
          background:
            "radial-gradient(640px circle at var(--mx,50%) var(--my,50%), oklch(0.52 0.062 190 / 7%), transparent 42%)",
        }}
      />
      <div className="relative z-10">{children}</div>
    </motion.div>
  );
}
