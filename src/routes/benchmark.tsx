import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, DataTable, Page, SectionHeading } from "../components/site/SiteChrome";
import { GATEWAY_URL } from "../lib/gateway";

export const Route = createFileRoute("/benchmark")({
  head: () => ({
    meta: [
      { title: "The Open Code-Mixed Cost/Quality Benchmark" },
      {
        name: "description",
        content:
          "A citable open dataset of real Hinglish support-style queries, graded for task accuracy across compression ratios with cost converted to actual rupees and dollars.",
      },
      { property: "og:title", content: "The Open Code-Mixed Cost/Quality Benchmark" },
      {
        property: "og:description",
        content:
          "Real Hinglish queries graded for accuracy at multiple compression ratios, with per-query cost in ₹ and $ at current API pricing.",
      },
    ],
  }),
  loader: async () => {
    try {
      const base = GATEWAY_URL || (typeof window === "undefined" ? "http://127.0.0.1:8000" : "");
      const [curveRes, summaryRes] = await Promise.all([
        fetch(`${base}/v1/eval/curve`).then((r) => {
          if (!r.ok) throw new Error(String(r.status));
          return r.json();
        }),
        fetch(`${base}/v1/eval/summary`).then((r) => {
          if (!r.ok) throw new Error(String(r.status));
          return r.json();
        }),
      ]);
      return { curve: curveRes, summary: summaryRes };
    } catch {
      return { curve: null, summary: null };
    }
  },
  errorComponent: ({ error }) => (
    <div className="mx-auto max-w-6xl px-5 pt-14">
      <p className="text-sm text-destructive">
        Benchmark failed to load: {String((error as Error)?.message ?? error)}
      </p>
    </div>
  ),
  component: BenchmarkPage,
});

type CurvePoint = {
  method: string;
  ratio: number;
  kept_pct: number;
  accuracy: number;
  is_simulated: boolean;
};

type EvalSummary = {
  n: number;
  mean_token_savings_ratio: number;
  total_savings_usd: number;
  total_savings_inr: number;
  pricing_date: string;
};

function BenchmarkPage() {
  const loaderData = Route.useLoaderData() as {
    curve: CurvePoint[] | null;
    summary: EvalSummary | null;
  };
  const [curve, setCurve] = useState<CurvePoint[] | null>(loaderData.curve ?? null);
  const [curveError, setCurveError] = useState<string | null>(null);
  const [summary, setSummary] = useState<EvalSummary | null>(loaderData.summary ?? null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [sweep, setSweep] = useState<{ method: string; target: number; accuracy: number }[] | null>(
    null,
  );

  useEffect(() => {
    // sweep always fetches; curve/summary skip if loader provided
    fetch(`${GATEWAY_URL}/v1/eval/curve/sweep`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setSweep)
      .catch(() => setSweep([]));
    if (curve && summary) return;
    fetch(`${GATEWAY_URL}/v1/eval/curve`)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<CurvePoint[]>;
      })
      .then(setCurve)
      .catch((e) => setCurveError(e instanceof Error ? e.message : String(e)));
    fetch(`${GATEWAY_URL}/v1/eval/summary`)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<EvalSummary>;
      })
      .then((s) => setSummary(s))
      .catch((e) => setSummaryError(e instanceof Error ? e.message : String(e)));
  }, [curve, summary]);

  return (
    <Page
      eyebrow="Benchmark"
      title="The first open code-mixed LLM cost/quality benchmark"
      lede="Even if every training experiment stalls, a clean, well-documented, citable dataset is a standalone contribution — and it is the calibration set the conformal router depends on."
    >
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Card>
          <SectionHeading kicker="Contents" title="What goes in" />
          <ul className="space-y-3 text-sm leading-relaxed text-muted-foreground">
            <li>
              Real support-chat-style Hindi–English queries: romanized Hindi, Devanagari, English
              and genuine mid-sentence code-switching.
            </li>
            <li>
              Paired English equivalents for a subset, so tokenizer cost and reasoning budget can be
              compared like for like.
            </li>
            <li>
              Task categories with checkable answers — factual lookup, arithmetic and logic,
              multi-turn support resolution, code help.
            </li>
            <li>
              Each item graded for task accuracy at several compression ratios, not just a single
              setting.
            </li>
            <li>Every query anonymized at collection time; nothing identifying is stored.</li>
          </ul>
        </Card>

        <Card className="bg-secondary/40">
          <SectionHeading kicker="Method" title="How it is graded" />
          <ol className="space-y-3 text-sm leading-relaxed text-muted-foreground">
            <li>
              <span className="font-medium text-foreground">1.</span> Compress each query at a sweep
              of target ratios.
            </li>
            <li>
              <span className="font-medium text-foreground">2.</span> Answer with each cascade tier,
              recording input and output tokens.
            </li>
            <li>
              <span className="font-medium text-foreground">3.</span> Score correctness against the
              reference answer, with a human-checked sample to validate automated grading.
            </li>
            <li>
              <span className="font-medium text-foreground">4.</span> Convert token counts to ₹ and
              $ at API pricing on a stated date — pricing moves, so the date ships with the number.
            </li>
            <li>
              <span className="font-medium text-foreground">5.</span> Plot the ratio-versus-accuracy
              curve per tier and per language mix.
            </li>
          </ol>
        </Card>
      </div>

      <div className="mt-4">
        <SectionHeading kicker="Live summary" title="Evaluation totals" />
        <div className="grid gap-4 sm:grid-cols-4">
          <Card>
            <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Records</p>
            <p className="mt-1.5 font-serif text-2xl text-primary">
              {summary ? String(summary.n) : "—"}
            </p>
          </Card>
          <Card>
            <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
              Avg savings ratio
            </p>
            <p className="mt-1.5 font-serif text-2xl text-primary">
              {summary ? `${(summary.mean_token_savings_ratio * 100).toFixed(1)}%` : "—"}
            </p>
          </Card>
          <Card>
            <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
              Total saved $
            </p>
            <p className="mt-1.5 font-serif text-2xl text-primary">
              {summary ? `$${summary.total_savings_usd.toFixed(4)}` : "—"}
            </p>
          </Card>
          <Card>
            <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
              Total saved ₹
            </p>
            <p className="mt-1.5 font-serif text-2xl text-primary">
              {summary ? `₹${summary.total_savings_inr.toFixed(2)}` : "—"}
            </p>
          </Card>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Pricing date: {summary?.pricing_date ?? "—"} ·{" "}
          {summaryError ? `error: ${summaryError}` : "live from /v1/eval/summary"}
        </p>
      </div>

      <div className="mt-14">
        <SectionHeading kicker="Fig. 1 — live" title="Compression ratio vs task accuracy" />
        <Card>
          {curveError ? (
            <p className="text-sm text-destructive">
              Could not load live curve ({curveError}). Is the gateway running?
            </p>
          ) : !curve ? (
            <p className="text-sm text-muted-foreground">Loading live curve…</p>
          ) : curve.length === 0 ? (
            <p className="text-sm text-muted-foreground">No benchmark data found.</p>
          ) : (
            <>
              <div className="h-[320px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={curve} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="method" tick={{ fontSize: 12 }} />
                    <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
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
                      name="Task accuracy (reward)"
                      fill="hsl(var(--primary))"
                      radius={[8, 8, 0, 0]}
                    />
                    <Bar
                      dataKey="ratio"
                      name="Kept ratio (lower = more compressed)"
                      fill="hsl(var(--accent-foreground))"
                      radius={[8, 8, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">heuristic</span> = training-free
                filler pruning. <span className="font-medium text-foreground">distilled</span> = CPU
                rejection-sampling distillation (the report&apos;s fallback, honestly labelled).{" "}
                <span className="font-medium text-foreground">llmlingua2</span> = simulated baseline
                (heuristic −0.06, clearly marked as simulated).
              </p>
            </>
          )}
        </Card>
      </div>

      {sweep && sweep.length > 0 ? (
        <div className="mt-10">
          <SectionHeading kicker="Fig. 1 — sweep" title="Target kept-ratio vs accuracy (curve)" />
          <Card>
            <div className="h-[320px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={(["heuristic", "distilled", "llmlingua2"] as const)
                    .flatMap((m) =>
                      sweep
                        .filter((p) => p.method === m)
                        .map((p) => ({ target: p.target, [m]: p.accuracy })),
                    )
                    .reduce((acc: Record<string, number>[], cur) => {
                      const ex = acc.find((r) => r["target"] === cur["target"]);
                      if (ex) Object.assign(ex, cur);
                      else acc.push(cur as Record<string, number>);
                      return acc;
                    }, [])}
                  margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="target"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v) => `${Math.round(v * 100)}%`}
                  />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 12,
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="heuristic"
                    stroke="hsl(var(--primary))"
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="distilled"
                    stroke="hsl(var(--accent-foreground))"
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="llmlingua2"
                    stroke="hsl(var(--muted-foreground))"
                    dot={false}
                    strokeDasharray="4 4"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
              Sweep of 30/50/70/90% kept ratio — shows degradation as compression tightens.
              `llmlingua2` is simulated.
            </p>
          </Card>
        </div>
      ) : null}

      <div className="mt-14">
        <SectionHeading kicker="Reported columns" title="What every row carries" />
        <DataTable
          head={["Field", "Why it is recorded"]}
          rows={[
            ["query_id", "Stable anonymous identifier; no user linkage of any kind"],
            [
              "language_mix",
              "Estimated Hindi / English / Devanagari proportion — the primary independent variable",
            ],
            ["task_type", "Factual, arithmetic, logic, support resolution, or code"],
            ["reference_answer", "Checkable ground truth so accuracy is not a judgement call"],
            [
              "tokens_raw / tokens_compressed",
              "Per tokenizer, so the tokenizer-fairness effect is visible rather than assumed",
            ],
            ["compression_ratio", "Swept, not fixed — the curve is the result, not one point"],
            ["accuracy_at_ratio", "Task correctness at each ratio, per cascade tier"],
            ["cost_inr / cost_usd", "Converted at a stated pricing date"],
            [
              "difficulty_score",
              "Router input, retained so it can serve as conformal calibration data",
            ],
          ]}
        />
      </div>

      <div className="mt-14 grid gap-6 sm:grid-cols-3">
        <Card>
          <h3 className="text-lg">v0 — week 2</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            50–100 anonymized real messages, enough to sanity-check the pipeline end to end.
          </p>
        </Card>
        <Card>
          <h3 className="text-lg">v1 — week 5</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Large enough to serve as a conformal calibration set. This gate blocks pillar B, so it
            is protected in the schedule.
          </p>
        </Card>
        <Card>
          <h3 className="text-lg">Release — week 12</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Public dataset release with a datasheet: collection method, consent language, grading
            protocol, pricing date and known limitations.
          </p>
        </Card>
      </div>
    </Page>
  );
}
