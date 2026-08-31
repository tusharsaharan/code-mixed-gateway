import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { fetchChallenges, type ChallengesResp } from "../../lib/gateway";

export function ChallengeTicker({ className = "" }: { className?: string }) {
  const [board, setBoard] = useState<ChallengesResp | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const b = await fetchChallenges(10);
        if (!cancelled) setBoard(b);
      } catch {
        // offline
      }
    };
    load();
    const id = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (!board || board.recent.length === 0) return null;

  const breaks = board.recent_breaks.length > 0 ? board.recent_breaks : board.recent.slice(0, 6);
  if (breaks.length === 0) return null;

  return (
    <div
      className={`overflow-hidden border-y border-red-200/60 bg-red-50/60 dark:bg-red-950/20 dark:border-red-900/40 ${className}`}
      aria-live="polite"
    >
      <div className="flex items-center gap-2 px-3 py-2 text-xs">
        <span className="shrink-0 rounded-full bg-red-600 px-2 py-0.5 font-medium text-white">
          RED TEAM
        </span>
        <span className="hidden shrink-0 text-muted-foreground sm:inline">
          {board.breaks_recent} breaks · {board.total_attempts} attempts · live
        </span>
        <div className="relative flex-1 overflow-hidden">
          <motion.div
            className="flex gap-6 whitespace-nowrap will-change-transform"
            animate={{ x: ["0%", "-50%"] }}
            transition={{ duration: 32, repeat: Infinity, ease: "linear" }}
          >
            {[...breaks, ...breaks].map((r, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-2 font-mono text-xs text-muted-foreground"
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${r.verdict === "break" ? "bg-red-500" : "bg-emerald-500"}`}
                />
                <span className="max-w-[260px] truncate text-foreground">
                  {r.text.slice(0, 60)}
                </span>
                <span
                  className={`rounded px-1.5 py-0.5 text-[11px] ${r.verdict === "break" ? "bg-red-100 text-red-900 dark:bg-red-900/30 dark:text-red-100" : "bg-emerald-100 text-emerald-900"}`}
                >
                  {r.verdict === "break" ? `${r.break_type}` : "safe"}
                </span>
                <span className="opacity-60">· {r.method}</span>
              </span>
            ))}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
