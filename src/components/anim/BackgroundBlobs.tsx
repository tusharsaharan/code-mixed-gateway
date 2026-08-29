import { motion } from "framer-motion";

export function BackgroundBlobs() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden print:hidden"
    >
      <motion.div
        className="absolute -top-40 -left-40 h-[520px] w-[520px] rounded-full bg-primary/15 blur-3xl"
        animate={{ x: [0, 50, -20, 0], y: [0, 30, -10, 0], scale: [1, 1.08, 0.96, 1] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-1/4 -right-48 h-[560px] w-[560px] rounded-full bg-accent/40 blur-3xl"
        animate={{ x: [0, -40, 20, 0], y: [0, 25, -20, 0], scale: [1, 0.95, 1.06, 1] }}
        transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-0 left-1/4 h-[460px] w-[460px] rounded-full bg-secondary/60 blur-3xl"
        animate={{ x: [0, 30, -30, 0], y: [0, -25, 12, 0], scale: [1, 1.05, 0.97, 1] }}
        transition={{ duration: 24, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
