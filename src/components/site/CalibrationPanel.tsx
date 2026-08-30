import { useEffect, useState } from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { Card } from "./SiteChrome";
import { fetchCalibrationMetrics, type CalibrationMetrics } from "../../lib/gateway";

export function CalibrationPanel() {
  const [m, setM] = useState<CalibrationMetrics | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true); setErr(null);
    try {
      const r = await fetchCalibrationMetrics();
      setM(r);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  if (loading) return <Card className="bg-secondary/40"><p className="text-sm text-muted-foreground">Loading calibration…</p></Card>;
  if (err || !m) return <Card className="border-destructive/30 bg-destructive/10"><p className="text-sm text-destructive">Calibration unreachable: {err}</p><button onClick={load} className="mt-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs">Retry</button></Card>;

  const reliable = m.reliability ?? [];
  const ecePct = (m.ece * 100).toFixed(2);
  const failIfWrong = Math.round((m.error_bound) * 100);
  const challengeN = 100;
  const maxFails = Math.round(m.error_bound * challengeN);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-primary/20 bg-primary/[0.04] p-5">
        <p className="text-xs uppercase tracking-[0.16em] text-primary">Falsifiability panel — invite scrutiny, not marketing</p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          <strong className="text-foreground">Claim:</strong> cascade error rate ≤ <span className="font-mono font-medium text-foreground">{m.error_bound.toFixed(4)}</span> at 95% confidence (Hoeffding LTT, grid 200, δ=0.05), threshold τ={m.threshold.toFixed(3)}, n={m.n} ({m.bench_n ?? 0} bench + {m.pad_n ?? 0} pad), ECE {ecePct}%.
          <br /><strong className="text-foreground">Falsifiable prediction:</strong> In the next {challengeN} routed queries you should see ≤ <strong className="text-foreground">{maxFails} failures</strong> (≈{failIfWrong}%); if you see more, the bound is broken — report it as a break.
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-card border border-border px-2.5 py-1">risk̂ {m.risk_hat.toFixed(4)}</span>
          <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">bound {m.error_bound.toFixed(4)}</span>
          <span className="rounded-full bg-card border border-border px-2.5 py-1">ECE {ecePct}%</span>
          <span className={`rounded-full px-2.5 py-1 ${m.is_real ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900"}`}>{m.is_real ? "real calibration" : "synthetic pad"}</span>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Reliability diagram — predicted vs empirical accuracy per bin</p>
          <div className="mt-4 h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={reliable} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="bin" tick={{ fontSize: 11 }} label={{ value: "confidence bin", position: "insideBottom", offset: -4, fontSize: 11 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12 }} />
                <Legend />
                <Bar dataKey="accuracy" name="Empirical" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
                <Bar dataKey="confidence" name="Predicted" fill="hsl(var(--muted-foreground))" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">Perfect calibration = bars match. Gap = ECE contribution (|acc−conf|×count/n). Hover for bin counts.</p>
        </Card>
        <Card className="lg:col-span-2">
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Bound anatomy</p>
          <div className="mt-3 space-y-3 text-sm">
            <div className="flex justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2.5"><span className="text-muted-foreground">α (target error)</span><span className="font-mono font-medium">{m.alpha.toFixed(3)}</span></div>
            <div className="flex justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2.5"><span className="text-muted-foreground">risk̂</span><span className="font-mono">{m.risk_hat.toFixed(4)}</span></div>
            <div className="flex justify-between rounded-xl border border-primary/30 bg-primary/[0.04] px-3 py-2.5"><span className="font-medium">Hoeffding bound</span><span className="font-mono font-medium text-primary">{m.error_bound_hoeffding.toFixed(4)}</span></div>
            <div className="flex justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2.5"><span className="text-muted-foreground">Simple 1/(n+1) bound</span><span className="font-mono">{m.error_bound_simple.toFixed(4)}</span></div>
            <div className="flex justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2.5"><span className="text-muted-foreground">Threshold τ</span><span className="font-mono">{m.threshold.toFixed(4)}</span></div>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            Try to <a href="/demo" className="font-medium text-primary hover:underline">break the bound in the Demo</a> — send Hinglish edge cases that should be cheap but fail, or premium-worthy but routed cheap.
          </p>
        </Card>
      </div>
    </div>
  );
}
