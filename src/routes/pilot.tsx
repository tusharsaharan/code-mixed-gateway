import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";
import {
  GATEWAY_URL,
  fetchDashboardStats,
  fetchSeries,
  fetchRecent,
  fetchHealth,
  fetchCalibrationMetrics,
  type DashboardStats,
  type SeriesPoint,
  type CalibrationMetrics,
} from "../lib/gateway";

export const Route = createFileRoute("/pilot")({
  head: () => ({
    meta: [
      { title: "Live Pilot — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "Where the gateway meets real users: a Telegram bot, an OpenAI-compatible endpoint, a public demo and a consent-first data policy.",
      },
      { property: "og:title", content: "Live Pilot — Code-Mixed LLM Gateway" },
    ],
  }),
  component: PilotPage,
});

const CHANNELS = [
  {
    title: "Telegram bot",
    body: "A free bot that answers real student questions in natural Hinglish, routed through the gateway, deployed in campus and course groups.",
  },
  {
    title: "OpenAI-compatible endpoint",
    body: "Classmates point Continue.dev, Cline or aider at it for coding help — real developer traffic and real savings data.",
  },
  {
    title: "Public demo + dashboard",
    body: "A Hugging Face Space with the live demo and dashboard, hosted free on ZeroGPU hardware.",
  },
  {
    title: "Community feedback",
    body: "Post to r/developersIndia or r/LocalLLaMA for outside critique — a community that cares about exactly this angle.",
  },
];

function PilotPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [series, setSeries] = useState<SeriesPoint[] | null>(null);
  const [recent, setRecent] = useState<unknown[] | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [calibration, setCalibration] = useState<CalibrationMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setStatsError(null);
    try {
      const [s, se, re, h, c] = await Promise.all([
        fetchDashboardStats().catch((e) => {
          throw e;
        }),
        fetchSeries(3600).catch(() => [] as SeriesPoint[]),
        fetchRecent(10).catch(() => [] as unknown[]),
        fetchHealth().catch(() => null),
        fetchCalibrationMetrics().catch(() => null),
      ]);
      setStats(s);
      setSeries(se);
      setRecent(re);
      setHealth(h);
      setCalibration(c);
    } catch (e) {
      setStatsError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);

  const tierEntries = stats ? Object.entries(stats.tier_split) : [];
  const totalTier = tierEntries.reduce((a, [, v]) => a + v, 0) || 1;

  return (
    <Page
      eyebrow="Deployment"
      title="Where the gateway meets real users"
      lede="The pilot is not a demo — it is real traffic, and its single most convincing number is the count of real queries routed and answered in production."
    >
      {/* LIVE STATS STRIP - replaces dummy with real backend data */}
      <div className="mb-10">
        <div className="flex items-center justify-between">
          <SectionHeading kicker="Live from gateway" title="Pilot metrics — real, not mocked" />
          <button
            onClick={load}
            disabled={loading}
            className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary hover:text-foreground disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {statsError ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Gateway unreachable: {statsError} — start it with{" "}
            <code className="rounded bg-secondary px-1 py-0.5">
              uvicorn gateway.modules.m5_gateway.main:app --port 8000
            </code>
            <span className="ml-2 text-xs text-muted-foreground">
              ({GATEWAY_URL ? GATEWAY_URL : "dev proxy /v1 → 127.0.0.1:8000"})
            </span>
          </div>
        ) : !stats ? (
          <p className="text-sm text-muted-foreground">Loading live pilot stats…</p>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-4">
              <Card>
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Queries routed
                </p>
                <p className="mt-1.5 font-serif text-3xl text-primary">
                  {stats.queries.toLocaleString()}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">via /v1/chat/completions</p>
              </Card>
              <Card>
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Tokens saved
                </p>
                <p className="mt-1.5 font-serif text-3xl text-primary">
                  {(stats.total_original_tokens - stats.total_compressed_tokens).toLocaleString()}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {stats.total_original_tokens.toLocaleString()} →{" "}
                  {stats.total_compressed_tokens.toLocaleString()}
                </p>
              </Card>
              <Card>
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Cost saved
                </p>
                <p className="mt-1.5 font-serif text-3xl text-primary">
                  ${stats.total_cost_savings_usd.toFixed(4)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  ₹{stats.total_cost_savings_inr.toFixed(2)} saved
                </p>
              </Card>
              <Card>
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Calibration
                </p>
                <p className="mt-1.5 font-serif text-3xl text-primary">
                  {calibration ? calibration.n : "—"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  thr {calibration ? calibration.threshold.toFixed(3) : "—"} · err{" "}
                  {calibration ? calibration.error_bound.toFixed(4) : "—"}
                </p>
              </Card>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <Card>
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Tier split — live
                </p>
                <div className="mt-4 space-y-3">
                  {tierEntries.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No queries yet — try the Demo</p>
                  ) : (
                    tierEntries.map(([model, count]) => (
                      <div key={model} className="flex items-center gap-3">
                        <span
                          className="w-36 truncate font-mono text-xs text-muted-foreground"
                          title={model}
                        >
                          {model}
                        </span>
                        <div className="h-2 flex-1 rounded-full bg-secondary">
                          <div
                            className="h-2 rounded-full bg-primary"
                            style={{ width: `${Math.max(4, (count / totalTier) * 100)}%` }}
                          />
                        </div>
                        <span className="w-10 text-right font-mono text-xs">{count}</span>
                      </div>
                    ))
                  )}
                </div>
                {health ? (
                  <p className="mt-4 text-xs text-muted-foreground">
                    Backend: {String(health["dry_run"] ? "dry_run" : "live")} · tokenizer{" "}
                    {String(health["tokenizer_backend"] ?? "—")} · pricing{" "}
                    {String(health["pricing_date"] ?? "—")}
                  </p>
                ) : null}
              </Card>

              <Card>
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Recent queries — live
                </p>
                <div className="mt-3 overflow-hidden rounded-lg border border-border">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-secondary/60">
                      <tr>
                        <th className="px-3 py-2 font-medium text-muted-foreground">user</th>
                        <th className="px-3 py-2 font-medium text-muted-foreground">tokens</th>
                        <th className="px-3 py-2 font-medium text-muted-foreground">model</th>
                        <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                          saved $
                        </th>
                        <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                          receipt
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {!recent || recent.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="px-3 py-4 text-center text-muted-foreground">
                            No recent queries
                          </td>
                        </tr>
                      ) : (
                        (recent as Array<Record<string, unknown>>).slice(0, 8).map((r, i) => {
                          const taskId = String(r["task_id"] || r["id"] || "");
                          return (
                            <tr key={i} className="border-t border-border/60">
                              <td className="px-3 py-2 font-mono truncate max-w-[80px]">
                                {String(r["user_id"] ?? "—")}
                              </td>
                              <td className="px-3 py-2 font-mono">
                                {String(r["original_tokens"] ?? "—")}→
                                {String(r["compressed_tokens"] ?? "—")}
                              </td>
                              <td className="px-3 py-2 font-mono truncate max-w-[100px]">
                                {String(r["model_routed"] ?? "—")}
                              </td>
                              <td className="px-3 py-2 text-right font-mono">
                                {typeof r["estimated_cost_savings"] === "number"
                                  ? (r["estimated_cost_savings"] as number).toFixed(5)
                                  : String(r["estimated_cost_savings"] ?? "—")}
                              </td>
                              <td className="px-3 py-2 text-right">
                                {taskId ? (
                                  <Link
                                    to="/receipt/$id"
                                    params={{ id: taskId }}
                                    className="font-mono text-[11px] text-primary hover:underline"
                                  >
                                    #{taskId.slice(-6)}
                                  </Link>
                                ) : (
                                  <span className="text-muted-foreground">—</span>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
                {series && series.length > 0 ? (
                  <p className="mt-3 text-xs text-muted-foreground">
                    Last {series.length} buckets · {series.reduce((a, p) => a + p.queries, 0)}{" "}
                    queries in window
                  </p>
                ) : null}
              </Card>
            </div>

            <p className="mt-3 text-xs text-muted-foreground">
              All numbers fetched live from{" "}
              <code className="rounded bg-secondary px-1 py-0.5">GET /v1/dashboard/stats</code>,{" "}
              <code className="rounded bg-secondary px-1 py-0.5">/series</code>,{" "}
              <code className="rounded bg-secondary px-1 py-0.5">/recent</code>,{" "}
              <code className="rounded bg-secondary px-1 py-0.5">/healthz</code>. Auto-refreshes
              every 30s.
            </p>
          </>
        )}
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        {CHANNELS.map((c) => (
          <Card key={c.title}>
            <h3 className="text-xl">{c.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{c.body}</p>
          </Card>
        ))}
      </div>

      <div className="mt-12 flex flex-wrap gap-3">
        <Link
          to="/demo"
          className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Try the live Demo
        </Link>
        <Link
          to="/benchmark"
          className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium transition-colors hover:bg-secondary"
        >
          See the benchmark it feeds
        </Link>
        <a
          href={`${GATEWAY_URL}/dashboard`}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium transition-colors hover:bg-secondary"
        >
          Open raw Dashboard ↗
        </a>
      </div>

      <div className="mt-14">
        <SectionHeading kicker="Ethics & consent" title="Data handling, decided up front" />
        <Card className="border-primary/30 bg-secondary/40">
          <ul className="space-y-3 text-sm leading-relaxed text-muted-foreground">
            <li>
              Users are told their anonymized queries may be used for the project, and nothing
              identifying is logged.
            </li>
            <li>
              Queries are anonymized at collection time — no usernames, phone numbers or group
              identifiers are retained.
            </li>
            <li>
              A lightweight consent / ethics sign-off is requested from the supervising institute in
              week 1, not discovered after data has been collected.
            </li>
          </ul>
        </Card>
      </div>
    </Page>
  );
}
