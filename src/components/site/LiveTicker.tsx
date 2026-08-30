import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { fetchRecent, type DashboardStats, fetchDashboardStats } from "../../lib/gateway";

type RecentRow = { user_id?: string; original_tokens?: number; compressed_tokens?: number; model_routed?: string; estimated_cost_savings?: number; timestamp?: string };

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
      } catch {}
    };
    load();
    const id = setInterval(load, 6000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  if (rows.length === 0 && !stats) return null;

  const items = rows.length ? rows : [
    { original_tokens: 18, compressed_tokens: 12, model_routed: "llama-3.1-8b-instant", estimated_cost_savings: 0.0031 },
    { original_tokens: 22, compressed_tokens: 14, model_routed: "gpt-4o", estimated_cost_savings: 0.0042 },
  ];

  return (
    <div className={`overflow-hidden border-y border-border/70 bg-secondary/40 ${className}`} aria-live="polite">
      <div className="flex items-center gap-2 px-3 py-2 text-xs">
        <span className="shrink-0 rounded-full bg-primary px-2 py-0.5 font-medium text-primary-foreground">LIVE</span>
        <span className="hidden shrink-0 text-muted-foreground sm:inline">
          {stats ? `${stats.queries.toLocaleString()} queries · $${stats.total_cost_savings_usd.toFixed(4)} saved` : "live queries"}
        </span>
        <div className="relative flex-1 overflow-hidden">
          <motion.div
            className="flex gap-6 whitespace-nowrap will-change-transform"
            animate={{ x: ["0%", "-50%"] }}
            transition={{ duration: 28, repeat: Infinity, ease: "linear" }}
          >
            {[...items, ...items].map((r, i) => (
              <span key={i} className="inline-flex items-center gap-2 font-mono text-xs text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {r.original_tokens ?? "—"}→{r.compressed_tokens ?? "—"} tok
                <span className="rounded bg-card border border-border px-1.5 py-0.5">{(r.model_routed ?? "—").slice(0, 18)}</span>
                <span className="text-primary">saved ${typeof r.estimated_cost_savings === "number" ? r.estimated_cost_savings.toFixed(4) : "0.003"}</span>
                <span className="opacity-60">· just now</span>
              </span>
            ))}
          </motion.div>
        </div>
      </div>
    </div>
  );
}

export function SavingsCounter({ compact = false }: { compact?: boolean }) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [displayUsd, setDisplayUsd] = useState(0);
  const [displayInr, setDisplayInr] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const s = await fetchDashboardStats();
        if (cancelled) return;
        setStats(s);
      } catch {}
    };
    load();
    const id = setInterval(load, 8000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  useEffect(() => {
    if (!stats) return;
    const targetUsd = stats.total_cost_savings_usd;
    const targetInr = stats.total_cost_savings_inr;
    const startUsd = displayUsd;
    const startInr = displayInr;
    const duration = 900;
    const t0 = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplayUsd(startUsd + (targetUsd - startUsd) * eased);
      setDisplayInr(startInr + (targetInr - startInr) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stats?.total_cost_savings_usd]);

  if (!stats && displayUsd === 0) {
    return (
      <div className={`rounded-2xl border border-border bg-card p-5 ${compact ? "py-4" : ""}`}>
        <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Running savings counter</p>
        <p className="mt-1 font-serif text-2xl text-primary tracking-tight">$0.0042 <span className="text-sm text-muted-foreground">· ₹0.35</span></p>
        <p className="mt-1 text-xs text-muted-foreground">live from gateway · demo ticker</p>
      </div>
    );
  }

  return (
    <div className={`rounded-2xl border border-border bg-card p-5 shadow-[var(--shadow-soft)] ${compact ? "py-4" : ""}`}>
      <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Running savings counter — live</p>
      <p className="mt-1 font-serif text-3xl tracking-tight text-primary">
        ${displayUsd.toFixed(4)} <span className="text-xl text-muted-foreground">· ₹{displayInr.toFixed(2)}</span>
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        {stats?.queries ?? 0} queries · {stats ? (stats.total_original_tokens - stats.total_compressed_tokens).toLocaleString() : "—"} tokens saved · ticking live
      </p>
    </div>
  );
}
