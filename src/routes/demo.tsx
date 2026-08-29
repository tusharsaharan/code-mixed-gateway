import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";
import {
  GATEWAY_URL,
  chatCompletion,
  fetchDashboardStats,
  streamChatCompletion,
  type ChatResponse,
  type DashboardStats,
  type GatewayMeta,
} from "../lib/gateway";

export const Route = createFileRoute("/demo")({
  head: () => ({
    meta: [
      { title: "Live Gateway Demo — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "Run a real Hinglish query through the compressor and the conformally-calibrated cascade router, live.",
      },
      { property: "og:title", content: "Live Gateway Demo — Code-Mixed LLM Gateway" },
    ],
  }),
  component: DemoPage,
});

const PRESETS = [
  "yaar matlab mera email user@example.com par bhejo na",
  "arre yaar physics ka numerical solve karo 5*3+2 ka answer batao",
  "bhai amount Rs. 2,500 transfer karo na abhi",
  "hostel ka wifi bahut slow chal raha hai, complaint kahan karni hai?",
];

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-1.5 font-serif text-2xl text-primary">{value}</p>
    </Card>
  );
}

function DemoPage() {
  const [query, setQuery] = useState(PRESETS[0] ?? "");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [useStream, setUseStream] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [streamAnswer, setStreamAnswer] = useState("");
  const [streamMeta, setStreamMeta] = useState<GatewayMeta | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  const refreshStats = () => {
    fetchDashboardStats()
      .then(setStats)
      .catch(() => setStats(null));
  };

  useEffect(() => {
    refreshStats();
  }, []);

  async function run() {
    setLoading(true);
    setStreaming(useStream);
    setError(null);
    setResult(null);
    setStreamAnswer("");
    setStreamMeta(null);
    try {
      if (useStream) {
        let full = "";
        let meta: GatewayMeta | null = null;
        for await (const chunk of streamChatCompletion(query)) {
          if (chunk.meta) setStreamMeta(chunk.meta);
          if (chunk.meta) meta = chunk.meta;
          if (chunk.content) {
            full += chunk.content;
            setStreamAnswer(full);
          }
        }
        // Build a synthetic result so the stats panel reuses the same shape
        if (meta) {
          setResult({
            id: `stream-${Date.now()}`,
            object: "chat.completion",
            created: Math.floor(Date.now() / 1000),
            model: meta.model_routed,
            choices: [
              { index: 0, message: { role: "assistant", content: full }, finish_reason: "stop" },
            ],
            usage: {
              prompt_tokens: meta.compressed_tokens,
              completion_tokens: 0,
              total_tokens: meta.compressed_tokens,
            },
            x_gateway: meta,
          });
        } else {
          // Fallback to non-streaming if the gateway didn't stream meta
          const r = await chatCompletion(query);
          setResult(r);
        }
        refreshStats();
      } else {
        const r = await chatCompletion(query);
        setResult(r);
        refreshStats();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setStreaming(false);
    }
  }

  const meta = result?.x_gateway ?? streamMeta;
  const answer = result?.choices[0]?.message?.content ?? streamAnswer;
  const keptPct = meta ? Math.round(meta.compression_ratio * 100) : 0;
  const savedPct = meta ? Math.round((1 - meta.compression_ratio) * 100) : 0;

  return (
    <Page
      eyebrow="Interactive"
      title="Run a Hinglish query through the gateway"
      lede="Live compression + calibrated routing. The answer below is produced from the compressed prompt and routed to the cheap or premium tier by the conformal threshold — the same pipeline the Telegram bot runs."
    >
      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <div className="space-y-4">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            placeholder="Apna sawal Hinglish mein likho…"
            className="w-full rounded-xl border border-border bg-card px-4 py-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-ring"
          />

          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => {
                  setQuery(p);
                  setResult(null);
                }}
                className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                {p}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={run}
              disabled={loading || !query.trim()}
              className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? (streaming ? "Streaming…" : "Routing…") : "Run through the gateway"}
            </button>
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={useStream}
                onChange={(e) => setUseStream(e.target.checked)}
                className="h-3 w-3 rounded"
              />
              Stream
            </label>
            <a
              href={`${GATEWAY_URL}/dashboard`}
              target="_blank"
              rel="noreferrer"
              className="text-sm font-medium text-primary hover:underline"
            >
              Open live dashboard ↗
            </a>
          </div>

          {error ? (
            <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
              {error}
              <p className="mt-2 text-xs">
                Is the gateway running? Start it with{" "}
                <code className="font-mono">uvicorn gateway.modules.m5_gateway.main:app</code> in{" "}
                <code className="font-mono">backend/</code>.
              </p>
            </div>
          ) : null}

          {result || streamAnswer ? (
            <Card>
              <h3 className="text-lg">Answer</h3>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">
                {answer}
                {streaming ? <span className="animate-pulse">▍</span> : null}
              </p>
              {meta?.compressed_prompt ? (
                <>
                  <div className="mt-4 rounded-lg bg-secondary/50 p-3 text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">Compressed prompt: </span>
                    {meta.compressed_prompt}
                  </div>
                  <div className="mt-3 rounded-lg border border-border bg-card p-3">
                    <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                      Word-level diff (what got cut)
                    </p>
                    <p className="mt-2 flex flex-wrap gap-1.5 text-xs leading-relaxed">
                      {(() => {
                        const origWords = query.split(/\s+/);
                        const compSet = new Set(
                          meta.compressed_prompt
                            .toLowerCase()
                            .split(/\s+/)
                            .map((w) => w.replace(/[,.!?;:"]+/g, "")),
                        );
                        return origWords.map((w, i) => {
                          const norm = w.toLowerCase().replace(/[,.!?;:"]+/g, "");
                          const isPII = /(@|Rs\.?|\+91|https?:)/.test(w);
                          const kept = compSet.has(norm) || isPII;
                          return (
                            <span
                              key={i}
                              className={
                                kept
                                  ? "rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700 border border-emerald-200"
                                  : "rounded bg-red-50 px-1.5 py-0.5 text-red-600 line-through border border-red-200"
                              }
                              title={kept ? "kept" : "removed"}
                            >
                              {w}
                            </span>
                          );
                        });
                      })()}
                    </p>
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      Green = kept, red strikethrough = removed. PII/code/amounts are always kept
                      (safety spans).
                    </p>
                  </div>
                </>
              ) : null}
            </Card>
          ) : null}
        </div>

        <div className="space-y-4">
          {result && meta ? (
            <>
              <SectionHeading kicker="Routing decision" title="What the cascade did" />
              <div className="grid gap-4 sm:grid-cols-2">
                <Stat label="Tier" value={meta.tier} />
                <Stat label="Model routed" value={meta.model_routed} />
                <Stat label="Difficulty score" value={meta.difficulty_score.toFixed(3)} />
                <Stat label="Threshold" value={meta.conformal_threshold.toFixed(3)} />
                <Stat
                  label="Tokens"
                  value={`${meta.original_tokens} → ${meta.compressed_tokens}`}
                />
                <Stat label="Kept" value={`${keptPct}%`} />
                <Stat label="Compressed" value={`${savedPct}%`} />
                <Stat label="Cost" value={`$${meta.estimated_cost_usd.toFixed(6)}`} />
                <Stat label="Saved" value={`$${meta.estimated_cost_savings_usd.toFixed(6)}`} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Kept = compressed / original. Compressed = tokens removed.
              </p>
              <div className="mt-4">
                <SectionHeading kicker="Pillar C" title="Reasoning budget" />
                <div className="grid gap-4 sm:grid-cols-2">
                  <Stat label="Thinking tokens" value={String(meta.reasoning_budget ?? 0)} />
                  <Stat
                    label="Hinglish ↔ English Δ"
                    value={
                      meta.budget_delta_hinglish_en == null
                        ? "—"
                        : `${meta.budget_delta_hinglish_en >= 0 ? "+" : ""}${meta.budget_delta_hinglish_en}`
                    }
                  />
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  The controller estimates how many reasoning tokens the query needs before
                  answering. The delta compares the same query in Hinglish vs. its English gloss — a
                  publishable side-finding from the report.
                </p>
              </div>
              <div className="mt-4">
                <SectionHeading kicker="Pillar B" title="Provable bound" />
                <div className="grid gap-4 sm:grid-cols-2">
                  <Stat label="Error bound" value={`≤ ${(meta.error_bound * 100).toFixed(1)}%`} />
                  <Stat label="Calibration n" value={String(meta.calibration_n)} />
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Distribution-free, finite-sample guarantee from conformal risk control — not a
                  tuned threshold.
                </p>
              </div>
            </>
          ) : null}

          <SectionHeading kicker="Pilot" title="Live dashboard" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Stat label="Queries" value={String(stats?.queries ?? 0)} />
            <Stat
              label="Tokens saved"
              value={String(
                (stats?.total_original_tokens ?? 0) - (stats?.total_compressed_tokens ?? 0),
              )}
            />
            <Stat
              label="Savings (₹)"
              value={`₹${(stats?.total_cost_savings_inr ?? 0).toFixed(2)}`}
            />
            <Stat label="Tiers" value={String(Object.keys(stats?.tier_split ?? {}).length)} />
          </div>
        </div>
      </div>
    </Page>
  );
}
