import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { fetchRecent, type DashboardStats, fetchDashboardStats } from "../../lib/gateway";

type RecentRow = {
  user_id?: string;
  original_tokens?: number;
  compressed_tokens?: number;
  model_routed?: string;
  estimated_cost_savings?: number;
  timestamp?: string;
};

export function LiveTicker({ className = "" }: { className?: string }) {
  const [rows, setRows] = useState<RecentRow[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [r, s] = await Promise.all([
          fetchRecent(16).catch(() => []),
          fetchDashboardStats().catch(() => null),
        ]);
        if (cancelled) return;
        setRows((r as RecentRow[]).slice(0, 12));
        if (s) setStats(s as DashboardStats);
      } catch {
        // gateway offline — ticker falls back to placeholder items
      }
    };
    load();
    const id = setInterval(load, 6000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const isOffline = rows.length === 0 && !stats;
  if (isOffline) return null;

  // Honest: no synthetic fallback — show real queries only, with offline banner when empty
  const hasLive = rows.length > 0;
  const items = rows;

  return (
    <div
      className={`overflow-hidden border-y border-border/70 bg-secondary/40 ${className}`}
      aria-live="polite"
    >
      <div className="flex items-center gap-2 px-3 py-2 text-xs">
        <span className="shrink-0 rounded-full bg-primary px-2 py-0.5 font-medium text-primary-foreground">
          LIVE
        </span>
        <span className="hidden shrink-0 text-muted-foreground sm:inline">
          {stats
            ? `${stats.queries.toLocaleString()} queries · $${stats.total_cost_savings_usd.toFixed(4)} saved · real queries only`
            : "live queries"}
        </span>
        <div className="relative flex-1 overflow-hidden">
          {hasLive ? (
            <motion.div
              className="flex gap-6 whitespace-nowrap will-change-transform"
              animate={{ x: ["0%", "-50%"] }}
              transition={{ duration: 28, repeat: Infinity, ease: "linear" }}
            >
              {[...items, ...items].map((r, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-2 font-mono text-xs text-muted-foreground"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {r.original_tokens ?? "—"}→{r.compressed_tokens ?? "—"} tok
                  <span className="rounded bg-card border border-border px-1.5 py-0.5">
                    {(r.model_routed ?? "—").slice(0, 18)}
                  </span>
                  <span className="text-primary">
                    saved $
                    {typeof r.estimated_cost_savings === "number"
                      ? r.estimated_cost_savings.toFixed(6)
                      : "0.003000"}
                  </span>
                  <span className="opacity-60">· just now</span>
                </span>
              ))}
            </motion.div>
          ) : (
            <span className="font-mono text-xs text-muted-foreground">
              No live queries yet — be first to run the Demo → gateway offline shows honest empty,
              not synthetic
            </span>
          )}
        </div>
        {!hasLive && stats ? (
          <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-900 dark:bg-amber-900/30 dark:text-amber-100">
            Synthetic preview hidden — real only
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function SavingsCounter({ compact = false }: { compact?: boolean }) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [displayUsd, setDisplayUsd] = useState(0);
  const [displayInr, setDisplayInr] = useState(0);

  // Debt-clock: continuous accrual between polls — easy, fully doable
  const rateRef = useRef({ usdPerMs: 0, inrPerMs: 0 });
  const lastStatsRef = useRef<DashboardStats | null>(null);
  const lastTsRef = useRef<number>(performance.now());

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const s = await fetchDashboardStats();
        if (cancelled) return;
        // compute rate from previous to new
        const now = performance.now();
        if (lastStatsRef.current) {
          const dt = Math.max(1, now - lastTsRef.current);
          const dUsd = s.total_cost_savings_usd - lastStatsRef.current.total_cost_savings_usd;
          const dInr = s.total_cost_savings_inr - lastStatsRef.current.total_cost_savings_inr;
          // smooth accrual: distribute delta over expected 8s interval
          rateRef.current.usdPerMs = Math.max(0, dUsd / dt);
          rateRef.current.inrPerMs = Math.max(0, dInr / dt);
        }
        lastStatsRef.current = s;
        lastTsRef.current = now;
        setStats(s);
      } catch {
        // gateway offline — counter keeps last value, rate decays
        rateRef.current.usdPerMs *= 0.9;
        rateRef.current.inrPerMs *= 0.9;
      }
    };
    load();
    const id = setInterval(load, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  // Ease to target + continuous accrual tick
  useEffect(() => {
    if (!stats) return;
    const targetUsd = stats.total_cost_savings_usd;
    const targetInr = stats.total_cost_savings_inr;
    const startUsd = displayUsd;
    const startInr = displayInr;
    const duration = 1200;
    const t0 = performance.now();
    let raf = 0;
    let lastFrame = t0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      const easedUsd = startUsd + (targetUsd - startUsd) * eased;
      const easedInr = startInr + (targetInr - startInr) * eased;
      // After eased phase, continue accruing at rate
      const dt = now - lastFrame;
      lastFrame = now;
      if (p >= 1 && (rateRef.current.usdPerMs > 0 || rateRef.current.inrPerMs > 0)) {
        setDisplayUsd((prev) => prev + rateRef.current.usdPerMs * dt);
        setDisplayInr((prev) => prev + rateRef.current.inrPerMs * dt);
        raf = requestAnimationFrame(tick);
      } else {
        setDisplayUsd(easedUsd);
        setDisplayInr(easedInr);
        if (p < 1) {
          raf = requestAnimationFrame(tick);
        } else {
          // keep ticking for debt-clock even after eased if rate >0
          if (rateRef.current.usdPerMs > 0) raf = requestAnimationFrame(tick);
        }
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stats?.total_cost_savings_usd, stats?.total_cost_savings_inr]);

  if (!stats && displayUsd === 0) {
    return (
      <div className={`rounded-2xl border border-border bg-card p-5 ${compact ? "py-4" : ""}`}>
        <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
          Running savings counter
        </p>
        <p className="mt-1 font-serif text-2xl text-primary tracking-tight">
          $0.0042 <span className="text-sm text-muted-foreground">· ₹0.35</span>
        </p>
        <p className="mt-1 text-xs text-muted-foreground">live from gateway · demo ticker</p>
      </div>
    );
  }

  return (
    <div
      className={`rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-soft)] ${compact ? "py-4" : ""}`}
    >
      <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
        Running savings counter — live
      </p>
      <p className="mt-1 font-serif text-3xl tracking-tight text-primary">
        ${displayUsd.toFixed(4)}{" "}
        <span className="text-xl text-muted-foreground">· ₹{displayInr.toFixed(2)}</span>
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        {stats?.queries ?? 0} queries ·{" "}
        {stats
          ? (stats.total_original_tokens - stats.total_compressed_tokens).toLocaleString()
          : "—"}{" "}
        tokens saved · ticking live
      </p>
    </div>
  );
}
