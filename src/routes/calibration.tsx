import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";
import { fetchCalibrationMetrics, type CalibrationMetrics } from "../lib/gateway";

export const Route = createFileRoute("/calibration")({
  head: () => ({
    meta: [
      { title: "Conformal Calibration — Code-Mixed Gateway" },
      {
        name: "description",
        content:
          "Inspect the conformal risk threshold, ECE, and reliability diagram that give the cascade its finite-sample guarantee.",
      },
    ],
  }),
  component: CalibrationPage,
});

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-1.5 font-serif text-2xl text-primary">{value}</p>
    </Card>
  );
}

function CalibrationPage() {
  const [data, setData] = useState<CalibrationMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCalibrationMetrics()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <Page
      eyebrow="Pillar B"
      title="Conformal calibration inspector"
      lede="The cascade's escalation rule is not a tuned knob — it is a distribution-free guarantee. Inspect its threshold, empirical risk, ECE and per-bin reliability live from the calibration set."
    >
      {error && !data ? (
        <div className="mb-6 rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error} — is the gateway running? Check VITE_GATEWAY_URL or the proxy at /v1.
        </div>
      ) : null}
      {error && !data ? null : !data ? (
        <p className="text-sm text-muted-foreground">Loading calibration metrics…</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-4">
            <Stat label="n (calibration)" value={String(data.n)} />
            <Stat label="Threshold τ" value={data.threshold.toFixed(3)} />
            <Stat label="Risk hat" value={data.risk_hat.toFixed(4)} />
            <Stat label="ECE" value={data.ece.toFixed(4)} />
          </div>
          <div className="mt-4">
            <Card
              className={
                data.is_real
                  ? "border-emerald-300 bg-emerald-50/40"
                  : "border-amber-300 bg-amber-50/40"
              }
            >
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Calibration source —{" "}
                {data.is_real
                  ? "REAL (from benchmark-derived + anchored synthetic)"
                  : "SYNTHETIC fallback"}
              </p>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                {data.is_real
                  ? `Loaded from ${data.real_path ?? "calibration.jsonl"} — 50 real benchmark-derived samples + 1950 anchored synthetic. Threshold is benchmark-grounded.`
                  : "No calibration.jsonl found — using randomized synthetic 2000-sample fallback. Numbers are illustrative until real calibration is ingested via POST /v1/calibration/ingest."}
              </p>
            </Card>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <Stat label="α (target error)" value={`${(data.alpha * 100).toFixed(1)}%`} />
            <Stat
              label="Error bound (simple)"
              value={`≤ ${(data.error_bound_simple * 100).toFixed(2)}%`}
            />
            <Stat
              label="Error bound (Hoeffding)"
              value={`≤ ${(data.error_bound_hoeffding * 100).toFixed(2)}%`}
            />
          </div>

          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            Simple bound = α + 1/(n+1) (split-conformal, diagnostic). Hoeffding bound = R̂(τ) +
            √(log(m/δ)/(2n)) with m=200 grid, δ=0.05. The deployed guarantee is the Hoeffding bound
            (conservative, distribution-free); simple is shown for comparison.
          </p>

          <div className="mt-10">
            <SectionHeading kicker="Diagnostics" title="Reliability diagram" />
            <Card>
              <p className="mb-4 text-sm text-muted-foreground">
                Each bin shows predicted success probability 1−score vs empirical cheap-success
                rate. Perfect calibration lies on the diagonal.
              </p>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.reliability}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis
                      dataKey="bin"
                      tick={{ fontSize: 11 }}
                      label={{ value: "confidence bin", position: "insideBottom", offset: -4 }}
                    />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: 12,
                      }}
                    />
                    <Bar
                      dataKey="accuracy"
                      name="Empirical accuracy"
                      fill="hsl(var(--primary))"
                      radius={[6, 6, 0, 0]}
                    />
                    <Bar
                      dataKey="confidence"
                      name="Mean confidence"
                      fill="hsl(var(--accent-foreground))"
                      radius={[6, 6, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground">
                      <th className="px-2 py-1">Bin</th>
                      <th className="px-2 py-1">Accuracy</th>
                      <th className="px-2 py-1">Confidence</th>
                      <th className="px-2 py-1">Count</th>
                      <th className="px-2 py-1">Gap</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.reliability.map((r) => (
                      <tr key={r.bin} className="border-b border-border/50">
                        <td className="px-2 py-1">{r.bin}</td>
                        <td className="px-2 py-1">{r.accuracy.toFixed(3)}</td>
                        <td className="px-2 py-1">{r.confidence.toFixed(3)}</td>
                        <td className="px-2 py-1">{r.count}</td>
                        <td
                          className={`px-2 py-1 ${Math.abs(r.accuracy - r.confidence) > 0.12 ? "text-destructive" : "text-muted-foreground"}`}
                        >
                          {Math.abs(r.accuracy - r.confidence).toFixed(3)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </>
      )}
    </Page>
  );
}
