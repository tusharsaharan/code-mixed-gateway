import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { Card } from "./SiteChrome";
import { fetchCalibrationMetrics, type CalibrationMetrics } from "../../lib/gateway";

export function CalibrationPanel() {
  const [m, setM] = useState<CalibrationMetrics | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [chartView, setChartView] = useState<"sweep" | "reliability">("sweep");
  const [windowSize, setWindowSize] = useState<number | undefined>(undefined);

  const load = async (win?: number) => {
    setLoading(true);
    setErr(null);
    try {
      const r = await fetchCalibrationMetrics(true, win);
      setM(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(windowSize);
  }, [windowSize]);

  if (loading && !m)
    return (
      <Card className="bg-secondary/40">
        <p className="text-sm text-muted-foreground">Loading calibration…</p>
      </Card>
    );
  if (err || !m)
    return (
      <Card className="border-destructive/30 bg-destructive/10">
        <p className="text-sm text-destructive">Calibration unreachable: {err}</p>
        <button
          onClick={() => load(windowSize)}
          className="mt-2 rounded-lg border border-border bg-card px-3 py-1.5 text-xs"
        >
          Retry
        </button>
      </Card>
    );

  const reliable = m.reliability ?? [];
  const sweepData = m.sweep ?? [];
  const ecePct = (m.ece * 100).toFixed(2);
  const failIfWrong = Math.round(m.error_bound * 100);
  const challengeN = 100;
  const maxFails = Math.round(m.error_bound * challengeN);

  const benchN = m.bench_n ?? 0;
  const padN = m.pad_n ?? 0;
  const realState =
    benchN >= 30
      ? {
          label: `Empirical Calibrated (${benchN} real)`,
          class: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-100",
        }
      : benchN > 0
        ? {
            label: `Hybrid Grounding (${benchN} real + ${padN} pad)`,
            class: "bg-blue-100 text-blue-900 dark:bg-blue-900/30 dark:text-blue-100",
          }
        : {
            label: `Synthetic Pad (${padN} pad)`,
            class: "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-100",
          };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-primary/20 bg-primary/[0.04] p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs uppercase tracking-[0.16em] text-primary">
            Falsifiability panel — invite scrutiny, not marketing
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setWindowSize(undefined)}
              className={`rounded-lg px-2 py-1 text-xs transition-colors ${windowSize === undefined ? "bg-primary text-primary-foreground font-medium" : "border border-border bg-card text-muted-foreground"}`}
            >
              All ({m.n})
            </button>
            <button
              onClick={() => setWindowSize(200)}
              className={`rounded-lg px-2 py-1 text-xs transition-colors ${windowSize === 200 ? "bg-primary text-primary-foreground font-medium" : "border border-border bg-card text-muted-foreground"}`}
            >
              Rolling 200
            </button>
          </div>
        </div>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          <strong className="text-foreground">Claim:</strong> cascade error rate ≤{" "}
          <span className="font-mono font-medium text-foreground">{m.error_bound.toFixed(4)}</span>{" "}
          at 95% confidence (Hoeffding LTT, grid 200, δ=0.05), threshold τ={m.threshold.toFixed(3)},
          n={m.n} ({benchN} real + {padN} pad), ECE {ecePct}%.
          <br />
          <strong className="text-foreground">Falsifiable prediction:</strong> In the next{" "}
          {challengeN} routed queries you should see ≤{" "}
          <strong className="text-foreground">{maxFails} failures</strong> (≈{failIfWrong}%); if you
          see more, the bound is broken — report it as a break.
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-card border border-border px-2.5 py-1">
            risk̂ {m.risk_hat.toFixed(4)}
          </span>
          <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">
            bound {m.error_bound.toFixed(4)}
          </span>
          <span className="rounded-full bg-card border border-border px-2.5 py-1">
            ECE {ecePct}%
          </span>
          <span className={`rounded-full px-2.5 py-1 font-medium ${realState.class}`}>
            {realState.label}
          </span>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
              {chartView === "sweep"
                ? "Threshold-Sweep Frontier (R̂(τ) & R_ub(τ) vs τ)"
                : "Reliability diagram (predicted vs empirical)"}
            </p>
            <div className="flex gap-1 rounded-lg border border-border bg-secondary/50 p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setChartView("sweep")}
                className={`rounded-md px-2.5 py-1 ${chartView === "sweep" ? "bg-card text-foreground font-medium shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                Sweep Curve
              </button>
              <button
                type="button"
                onClick={() => setChartView("reliability")}
                className={`rounded-md px-2.5 py-1 ${chartView === "reliability" ? "bg-card text-foreground font-medium shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
              >
                Reliability Diagram
              </button>
            </div>
          </div>

          <div className="mt-4 h-[280px]">
            {chartView === "sweep" ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={sweepData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="tau"
                    tick={{ fontSize: 11 }}
                    domain={[0, 1]}
                    label={{
                      value: "Threshold τ",
                      position: "insideBottom",
                      offset: -4,
                      fontSize: 11,
                    }}
                  />
                  <YAxis domain={[0, 0.25]} tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 12,
                    }}
                  />
                  <Legend />
                  <ReferenceLine
                    y={m.alpha}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                    label={{
                      value: `α = ${m.alpha}`,
                      position: "top",
                      fill: "#ef4444",
                      fontSize: 11,
                    }}
                  />
                  <ReferenceLine
                    x={Number(m.threshold.toFixed(3))}
                    stroke="#10b981"
                    strokeDasharray="3 3"
                    label={{
                      value: `τ* = ${m.threshold.toFixed(3)}`,
                      position: "insideTopLeft",
                      fill: "#10b981",
                      fontSize: 11,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="risk_bound"
                    name="Hoeffding Bound R_ub(τ)"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="risk_hat"
                    name="Empirical Risk R̂(τ)"
                    stroke="hsl(var(--muted-foreground))"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={reliable} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="bin"
                    tick={{ fontSize: 11 }}
                    label={{
                      value: "confidence bin",
                      position: "insideBottom",
                      offset: -4,
                      fontSize: 11,
                    }}
                  />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 12,
                    }}
                  />
                  <Legend />
                  <Bar
                    dataKey="accuracy"
                    name="Empirical"
                    fill="hsl(var(--primary))"
                    radius={[8, 8, 0, 0]}
                  />
                  <Bar
                    dataKey="confidence"
                    name="Predicted"
                    fill="hsl(var(--muted-foreground))"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {chartView === "sweep"
              ? `Scanning 200 grid points. Chosen τ=${m.threshold.toFixed(3)} is the largest threshold where R_ub(τ) ≤ α=0.05.`
              : "Perfect calibration = bars match. Gap = ECE contribution (|acc−conf|×count/n)."}
          </p>
        </Card>
        <Card className="lg:col-span-2">
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Bound anatomy</p>
          <div className="mt-3 space-y-3 text-sm">
            <div className="flex justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2.5">
              <span className="text-muted-foreground">α (target error)</span>
              <span className="font-mono font-medium">{m.alpha.toFixed(3)}</span>
            </div>
            <div className="flex justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2.5">
              <span className="text-muted-foreground">risk̂</span>
              <span className="font-mono">{m.risk_hat.toFixed(4)}</span>
            </div>
            <div className="flex justify-between rounded-xl border border-primary/30 bg-primary/[0.04] px-3 py-2.5">
              <span className="font-medium">Hoeffding bound</span>
              <span className="font-mono font-medium text-primary">
                {m.error_bound_hoeffding.toFixed(4)}
              </span>
            </div>
            <div className="flex justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2.5">
              <span className="text-muted-foreground">Simple 1/(n+1) bound</span>
              <span className="font-mono">{m.error_bound_simple.toFixed(4)}</span>
            </div>
            <div className="flex justify-between rounded-xl border border-border bg-secondary/30 px-3 py-2.5">
              <span className="text-muted-foreground">Threshold τ</span>
              <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400">
                {m.threshold.toFixed(4)}
              </span>
            </div>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            Try to{" "}
            <a href="/demo" className="font-medium text-primary hover:underline">
              break the bound in the Demo
            </a>{" "}
            — send Hinglish edge cases that should be cheap but fail, or premium-worthy but routed
            cheap.
          </p>
        </Card>
      </div>
    </div>
  );
}
