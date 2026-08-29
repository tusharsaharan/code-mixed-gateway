import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Bar,
  BarChart,
} from "recharts";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";
import {
  fetchDashboardStats,
  fetchRecent,
  fetchSeries,
  GATEWAY_URL,
  type DashboardStats,
} from "../lib/gateway";

export const Route = createFileRoute("/analytics")({
  head: () => ({
    meta: [
      { title: "Analytics — Code-Mixed Gateway" },
      {
        name: "description",
        content: "Live pilot analytics: queries, cost savings, tier split and recent traffic.",
      },
    ],
  }),
  loader: async () => {
    try {
      if (!GATEWAY_URL) return { stats: null, series: [], recent: [], error: null };
      const [stats, series, recent] = await Promise.all([
        fetchDashboardStats(),
        fetchSeries(),
        fetchRecent(20),
      ]);
      return { stats, series, recent, error: null as string | null };
    } catch (e) {
      return {
        stats: null,
        series: [],
        recent: [],
        error: e instanceof Error ? e.message : String(e),
      };
    }
  },
  errorComponent: ({ error }) => (
    <div className="mx-auto max-w-6xl px-5 pt-14">
      <p className="text-sm text-destructive">
        Analytics failed to load: {String((error as Error)?.message ?? error)}
      </p>
    </div>
  ),
  component: AnalyticsPage,
});

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-1.5 font-serif text-2xl text-primary">{value}</p>
    </Card>
  );
}

function AnalyticsPage() {
  const loaderData = Route.useLoaderData() as {
    stats: DashboardStats | null;
    series: { bucket: string; queries: number; savings_usd: number }[];
    recent: unknown[];
    error: string | null;
  };
  const [stats, setStats] = useState<DashboardStats | null>(loaderData.stats ?? null);
  const [series, setSeries] = useState<{ bucket: string; queries: number; savings_usd: number }[]>(
    loaderData.series ?? [],
  );
  const [recent, setRecent] = useState<unknown[]>(loaderData.recent ?? []);
  const [error, setError] = useState<string | null>(loaderData.error ?? null);

  const load = async () => {
    try {
      const [s, ser, rec] = await Promise.all([
        fetchDashboardStats(),
        fetchSeries(),
        fetchRecent(20),
      ]);
      setStats(s);
      setSeries(ser);
      setRecent(rec as unknown[]);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  useEffect(() => {
    // if loader already seeded, keep polling
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const tierEntries = stats ? Object.entries(stats.tier_split) : [];

  return (
    <Page
      eyebrow="Observability"
      title="Live pilot analytics"
      lede="Polled every 15 seconds from the gateway's SQLite store. The same data backing the static /dashboard page — now as a reactive SPA view with tier breakdowns and recent query table."
    >
      {error ? (
        <div className="mb-6 rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error} — is the gateway running
          {GATEWAY_URL
            ? ` at ${GATEWAY_URL}`
            : " (proxy /v1 → 127.0.0.1:8000 in dev, set VITE_GATEWAY_URL in prod)"}
          ?
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Queries" value={String(stats?.queries ?? 0)} />
        <Stat
          label="Tokens saved"
          value={String(
            (stats?.total_original_tokens ?? 0) - (stats?.total_compressed_tokens ?? 0),
          )}
        />
        <Stat label="Savings (₹)" value={`₹${(stats?.total_cost_savings_inr ?? 0).toFixed(2)}`} />
        <Stat label="Savings ($)" value={`$${(stats?.total_cost_savings_usd ?? 0).toFixed(4)}`} />
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <Card>
          <SectionHeading kicker="Time series" title="Savings per hour" />
          {series.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No time series data yet — run queries via the demo.
            </p>
          ) : (
            <div className="h-[240px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={series.map((p) => ({
                    ...p,
                    t: new Date(Number(p.bucket) * 1000).toLocaleTimeString(),
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="t" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="savings_usd"
                    stroke="hsl(var(--primary))"
                    fill="hsl(var(--primary) / 0.18)"
                  />
                  <Area
                    type="monotone"
                    dataKey="queries"
                    stroke="hsl(var(--accent-foreground))"
                    fill="transparent"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card>
          <SectionHeading kicker="Traffic" title="Tier split" />
          {tierEntries.length === 0 ? (
            <p className="text-sm text-muted-foreground">No splits yet.</p>
          ) : (
            <div className="h-[240px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={tierEntries.map(([k, v]) => ({ tier: k, count: v }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="tier" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 12,
                    }}
                  />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <div className="mt-10">
        <SectionHeading kicker="Recent" title="Latest queries" />
        <Card>
          {recent.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent queries.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs uppercase tracking-[0.08em] text-muted-foreground">
                    <th className="px-3 py-2">User</th>
                    <th className="px-3 py-2">Orig</th>
                    <th className="px-3 py-2">Comp</th>
                    <th className="px-3 py-2">Model</th>
                    <th className="px-3 py-2">Savings $</th>
                  </tr>
                </thead>
                <tbody>
                  {(recent as Record<string, unknown>[]).map((r, i) => (
                    <tr key={i} className="border-b border-border/60">
                      <td className="px-3 py-2 font-mono text-xs">{String(r["user_id"] ?? "")}</td>
                      <td className="px-3 py-2">{String(r["original_tokens"] ?? "")}</td>
                      <td className="px-3 py-2">{String(r["compressed_tokens"] ?? "")}</td>
                      <td className="px-3 py-2">{String(r["model_routed"] ?? "")}</td>
                      <td className="px-3 py-2">
                        {Number(r["estimated_cost_savings"] ?? 0).toFixed(6)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </Page>
  );
}
