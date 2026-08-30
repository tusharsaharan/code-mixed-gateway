import { motion, AnimatePresence } from "framer-motion";

export function Shred({ original, compressed, active = true }: { original: string; compressed: string; active?: boolean }) {
  const cSet = new Set(compressed.split(/\s+/));
  const parts = original.split(/(\s+)/);
  // Map each word token to kept/dropped
  let wIdx = 0;
  return (
    <p className="font-mono text-sm leading-relaxed">
      <AnimatePresence initial={false}>
        {parts.map((p, i) => {
          const isSpace = /^\s+$/.test(p);
          if (isSpace) return <span key={i}>{p}</span>;
          const kept = cSet.has(p);
          const word = p;
          wIdx++;
          if (kept) {
            return (
              <motion.span
                key={`${i}-${word}`}
                initial={{ opacity: 0.6 }}
                animate={{ opacity: 1 }}
                className="inline-block"
              >
                {word}
              </motion.span>
            );
          }
          // Dropped — shred falls
          return (
            <motion.span
              key={`${i}-${word}-drop`}
              initial={active ? { y: 0, rotate: 0, opacity: 1 } : { y: 18, rotate: 8, opacity: 0.35 }}
              animate={active ? { y: 18, rotate: 8 + (wIdx % 3) * 4, opacity: 0.35 } : { y: 18, rotate: 8, opacity: 0.35 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.55, delay: (wIdx % 7) * 0.04, ease: [0.22, 1, 0.36, 1] }}
              className="mr-1 inline-block rounded bg-amber-100 px-1 py-0.5 text-amber-900 line-through decoration-amber-600/60 dark:bg-amber-900/30 dark:text-amber-100"
            >
              {word}
            </motion.span>
          );
        })}
      </AnimatePresence>
    </p>
  );
}
