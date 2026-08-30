import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";
import { Shred } from "../components/anim/Shred";
import { LiveTicker } from "../components/site/LiveTicker";
import {
  GATEWAY_URL,
  type GatewayMeta,
  compressText,
  fetchHealth,
  fetchReasoningBudget,
  streamChatCompletion,
  chatCompletion,
} from "../lib/gateway";

export const Route = createFileRoute("/demo")({
  head: () => ({
    meta: [
      { title: "Live Gateway Demo — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "Run a real Hinglish prompt through compression, conformal routing and the live gateway — see tokens, tier and savings update in real time.",
      },
      { property: "og:title", content: "Live Gateway Demo — Code-Mixed LLM Gateway" },
    ],
  }),
  component: DemoPage,
});

const PRESETS = [
  {
    label: "Support — Hinglish",
    text: "yaar mera hostel ka wifi slow hai, complaint kahan karun? kal se assignment submit karna hai",
  },
  {
    label: "Math — Hinglish",
    text: "arre yaar 15*8+22 ka answer kya hoga? exam me aaya tha, jaldi batao na",
  },
  {
    label: "Phone + polite fluff",
    text: "hello sir, yaar matlab basically mera phone charge nahi ho raha hai, actually dekho na help chahiye tha please",
  },
  {
    label: "Protected span",
    text: "yaar matlab mera email user@example.com par bhejo na, aur amount Rs. 2,500 ka check karo",
  },
] as const;

const METHODS = ["auto", "heuristic", "distilled", "adaptive", "model"] as const;

function wordDiff(original: string, compressed: string) {
  const c = new Set(compressed.split(/\s+/));
  const removed: string[] = [];
  for (const w of original.split(/\s+/)) {
    if (!c.has(w)) removed.push(w);
  }
  return { removed };
}

function DemoPage() {
  const [input, setInput] = useState<string>(PRESETS[0].text);
  const [method, setMethod] = useState<(typeof METHODS)[number]>("auto");
  const [useStream, setUseStream] = useState(true);
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [compressRes, setCompressRes] = useState<{
    original: string;
    compressed: string;
    token_original: number;
    token_compressed: number;
    ratio: number;
    method: string;
  } | null>(null);
  const [meta, setMeta] = useState<GatewayMeta | null>(null);
  const [answer, setAnswer] = useState<string>("");
  const [reasoning, setReasoning] = useState<{
    reasoning_tokens: number;
    code_mix_ratio: number;
    math_marker_count: number;
    logic_marker_count: number;
    delta_hinglish_minus_english?: number;
    english_budget?: number;
  } | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  // health probe
  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then(() => {
        if (!cancelled) setHealthOk(true);
      })
      .catch(() => {
        if (!cancelled) setHealthOk(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleRun = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed) {
      setError("Please enter a prompt.");
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError(null);
    setAnswer("");
    setMeta(null);
    setCompressRes(null);
    setReasoning(null);

    try {
      // 1) compress preview + reasoning budget in parallel
      const [cRes, rBudget] = await Promise.all([
        compressText(trimmed, method),
        fetchReasoningBudget(trimmed).catch(() => null),
      ]);
      if (ac.signal.aborted) return;
      setCompressRes(cRes);
      if (rBudget) setReasoning(rBudget);

      // 2) full gateway chat (stream or not)
      if (useStream) {
        let full = "";
        let gotMeta: GatewayMeta | null = null;
        for await (const chunk of streamChatCompletion(trimmed)) {
          if (ac.signal.aborted) return;
          if (chunk.meta) {
            gotMeta = chunk.meta;
            setMeta(chunk.meta);
            // when meta arrives, also merge reasoning if delta present
            if (chunk.meta.budget_delta_hinglish_en != null && rBudget) {
              setReasoning((prev) =>
                prev
                  ? { ...prev, delta_hinglish_minus_english: chunk.meta!.budget_delta_hinglish_en! }
                  : prev,
              );
            }
          }
          if (chunk.content) {
            full += chunk.content;
            setAnswer(full);
          }
        }
        // if stream didn't yield meta (shouldn't happen), fallback to non-stream meta fetch
        if (!gotMeta) {
          const fallback = await chatCompletion(trimmed);
          if (!ac.signal.aborted) {
            setAnswer(fallback.choices[0]?.message.content ?? full);
            if (fallback.x_gateway) setMeta(fallback.x_gateway);
          }
        }
      } else {
        const res = await chatCompletion(trimmed);
        if (ac.signal.aborted) return;
        setAnswer(res.choices[0]?.message.content ?? "");
        if (res.x_gateway) setMeta(res.x_gateway);
      }
    } catch (e) {
      if ((e as Error)?.name === "AbortError") return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (!ac.signal.aborted) setLoading(false);
    }
  }, [input, method, useStream]);

  const handleClear = useCallback(() => {
    abortRef.current?.abort();
    setAnswer("");
    setMeta(null);
    setCompressRes(null);
    setReasoning(null);
    setError(null);
    setLoading(false);
  }, []);

  const diff = compressRes ? wordDiff(compressRes.original, compressRes.compressed) : null;
  const charCount = input.length;
  const overLimit = charCount > 4000;

  return (
    <Page
      eyebrow="Live demo"
      title="Run a prompt through the gateway"
      lede="Compression, conformal routing and the answer happen live — tokens, tier and savings update as the gateway streams. Dry-run by default, real models when keys are set."
    >
      <div className="-mx-6 -mt-12 mb-6"><LiveTicker /></div>
      {/* health banner */}
      <div className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 text-sm">
        <span
          className={`h-2 w-2 rounded-full ${healthOk == null ? "bg-amber-400 animate-pulse" : healthOk ? "bg-emerald-500" : "bg-red-500"}`}
          aria-hidden
        />
        <span className="text-muted-foreground">
          Gateway:{" "}
          <span
            className={
              healthOk == null ? "text-amber-600" : healthOk ? "text-emerald-600" : "text-red-600"
            }
          >
            {healthOk == null ? "checking…" : healthOk ? "reachable" : "unreachable"}
          </span>
          {GATEWAY_URL ? ` · ${GATEWAY_URL}` : " · dev proxy (/v1 → 127.0.0.1:8000)"}
        </span>
        {!healthOk && healthOk != null ? (
          <span className="text-xs text-muted-foreground">
            The demo will show the error returned by the gateway. Start it with{" "}
            <code className="rounded bg-secondary px-1 py-0.5">
              uvicorn gateway.modules.m5_gateway.main:app --port 8000
            </code>
          </span>
        ) : null}
        <a
          href={`${GATEWAY_URL}/dashboard`}
          target="_blank"
          rel="noreferrer"
          className="ml-auto text-xs font-medium text-primary hover:underline"
        >
          Open pilot dashboard ↗
        </a>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        {/* input */}
        <Card>
          <SectionHeading kicker="Input" title="Your Hinglish prompt" />
          <label htmlFor="demo-input" className="sr-only">
            Prompt
          </label>
          <textarea
            id="demo-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a Hinglish message — e.g. 'yaar mera wifi slow hai...'"
            rows={5}
            maxLength={8000}
            className="w-full resize-y rounded-xl border border-input bg-background px-3.5 py-3 text-sm leading-relaxed outline-none placeholder:text-muted-foreground focus:border-primary/40 focus:ring-2 focus:ring-primary/15"
          />
          <div className="mt-2 flex items-center justify-between text-xs">
            <span className={overLimit ? "text-destructive" : "text-muted-foreground"}>
              {charCount.toLocaleString()} / 4,000 chars
              {overLimit ? " — too long, please shorten" : ""}
            </span>
            <label className="inline-flex items-center gap-1.5 text-muted-foreground">
              <input
                type="checkbox"
                checked={useStream}
                onChange={(e) => setUseStream(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-input"
              />
              Stream answer
            </label>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => setInput(p.text)}
                className="rounded-full border border-border bg-secondary/60 px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/30 hover:bg-secondary hover:text-foreground"
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm">
              <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Method
              </span>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as typeof method)}
                className="rounded-lg border border-input bg-background px-2.5 py-2 text-sm outline-none focus:border-primary/40"
              >
                {METHODS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>

            <button
              type="button"
              onClick={handleRun}
              disabled={loading || !input.trim() || overLimit}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" />
                  Running…
                </>
              ) : (
                "Run through the gateway"
              )}
            </button>
            <button
              type="button"
              onClick={handleClear}
              disabled={loading && !answer}
              className="rounded-lg border border-border bg-card px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-secondary hover:text-foreground disabled:opacity-50"
            >
              Clear
            </button>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            <span className="font-medium text-foreground">auto</span> uses distilled if available,
            else model when not dry-run, else heuristic.{" "}
            <span className="font-medium text-foreground">adaptive</span> is code-mix-aware (novel): keeps more for Hinglish/math-heavy, compresses aggressively for light English. Protected spans are masked before compression and re-injected fail-closed ·{" "}
            <a href="/results" className="font-medium text-primary hover:underline">
              See results →
            </a>
          </p>
          {error ? (
            <div className="mt-4 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          ) : null}
        </Card>

        {/* compression preview */}
        <Card className={compressRes ? "" : "bg-secondary/30"}>
          <SectionHeading kicker="Compression" title="What got cut" />
          {!compressRes ? (
            <p className="text-sm leading-relaxed text-muted-foreground">
              Run the gateway to see the compressed prompt, token counts and which filler words were
              dropped. Protected spans like{" "}
              <code className="rounded bg-secondary px-1 py-0.5 text-xs">user@example.com</code> are
              never removed.
            </p>
          ) : (
            <>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">
                  {compressRes.token_original} → {compressRes.token_compressed} tokens
                </span>
                <span className="rounded-full bg-secondary px-2.5 py-1 text-muted-foreground">
                  ratio {(compressRes.ratio * 100).toFixed(1)}% kept
                </span>
                <span className="rounded-full border border-border bg-card px-2.5 py-1 text-muted-foreground">
                  {compressRes.method}
                </span>
              </div>
              <div className="mt-4 rounded-xl border border-border bg-secondary/40 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Compressed prompt
                </p>
                <p className="mt-2 font-mono text-sm leading-relaxed">
                  {compressRes.compressed || "—"}
                </p>
              </div>
              <div className="mt-4 rounded-xl border border-border bg-card p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Shred — watch filler fall</p>
                <div className="mt-2 min-h-[28px]">
                  <Shred original={compressRes.original} compressed={compressRes.compressed} active={!loading} />
                </div>
                {diff && diff.removed.length > 0 ? (
                  <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                    Dropped:{" "}
                    {diff.removed.slice(0, 12).map((w) => (
                      <span
                        key={w}
                        className="mr-1 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-amber-900 dark:bg-amber-900/30 dark:text-amber-100"
                      >
                        {w}
                      </span>
                    ))}
                    {diff.removed.length > 12 ? ` +${diff.removed.length - 12} more` : ""}
                  </p>
                ) : (
                  <p className="mt-3 text-xs text-muted-foreground">Nothing dropped — already minimal.</p>
                )}
              </div>
              <p className="mt-3 font-mono text-xs leading-relaxed text-muted-foreground">
                Original: <span className="text-foreground">{compressRes.original}</span>
              </p>
            </>
          )}
        </Card>
      </div>

      {/* routing + reasoning */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card>
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Routing</p>
          {!meta ? (
            <p className="mt-2 text-sm text-muted-foreground">Run to see tier and threshold.</p>
          ) : (
            <>
              <p className="mt-2 flex items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-semibold ${meta.tier === "premium" ? "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-100" : "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-100"}`}
                >
                  {meta.tier}
                </span>
                <span className="font-mono text-xs text-muted-foreground">{meta.model_routed}</span>
              </p>
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Difficulty</dt>
                  <dd className="font-mono font-medium">{meta.difficulty_score.toFixed(4)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Threshold τ</dt>
                  <dd className="font-mono font-medium">{meta.conformal_threshold.toFixed(4)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Error bound</dt>
                  <dd className="font-mono font-medium">{meta.error_bound.toFixed(4)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Calibration n</dt>
                  <dd className="font-mono">{meta.calibration_n}</dd>
                </div>
              </dl>
            </>
          )}
        </Card>

        <Card>
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Cost (approx)</p>
          {!meta ? (
            <p className="mt-2 text-sm text-muted-foreground">Run to see pricing.</p>
          ) : (
            <>
              <p className="mt-2 font-serif text-2xl text-primary">
                ${meta.estimated_cost_usd.toFixed(6)}
              </p>
              <p className="text-xs text-muted-foreground">
                Savings vs always-premium:{" "}
                <span className="font-medium text-foreground">
                  ${meta.estimated_cost_savings_usd.toFixed(6)}
                </span>
              </p>
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                Pricing via <code className="rounded bg-secondary px-1 py-0.5">pricing.py</code>{" "}
                (single source) at <span className="font-medium">2026-08-28</span> · CHEAP $0.00006
                / PREMIUM $0.0025 per 1k tokens. Token counts depend on tokenizer (~1.5× spread) so
                treat as approximate.
              </p>
            </>
          )}
        </Card>

        <Card>
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Reasoning budget
          </p>
          {!reasoning ? (
            <p className="mt-2 text-sm text-muted-foreground">Run to see the budget estimate.</p>
          ) : (
            <>
              <p className="mt-2 font-serif text-2xl text-primary">
                {reasoning.reasoning_tokens} tokens
              </p>
              <dl className="mt-3 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Code-mix ratio</dt>
                  <dd className="font-mono">{reasoning.code_mix_ratio.toFixed(3)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Math markers</dt>
                  <dd className="font-mono">{reasoning.math_marker_count}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Logic markers</dt>
                  <dd className="font-mono">{reasoning.logic_marker_count}</dd>
                </div>
                {reasoning.delta_hinglish_minus_english != null ? (
                  <div className="flex justify-between border-t border-border pt-2">
                    <dt className="text-muted-foreground">Δ Hinglish − English</dt>
                    <dd
                      className={`font-mono font-medium ${reasoning.delta_hinglish_minus_english > 0 ? "text-amber-600" : reasoning.delta_hinglish_minus_english < 0 ? "text-emerald-600" : ""}`}
                    >
                      {reasoning.delta_hinglish_minus_english > 0 ? "+" : ""}
                      {reasoning.delta_hinglish_minus_english}
                      {reasoning.english_budget != null ? ` (en: ${reasoning.english_budget})` : ""}
                    </dd>
                  </div>
                ) : null}
              </dl>
            </>
          )}
        </Card>
      </div>

      {/* answer */}
      <div className="mt-6">
        <SectionHeading kicker="Answer" title="Gateway response" />
        <Card className="min-h-[160px]">
          {!answer && !loading ? (
            <p className="text-sm leading-relaxed text-muted-foreground">
              The gateway&apos;s answer will stream here. Try the Hinglish presets above — the
              second one should route to{" "}
              <span className="font-medium text-foreground">premium</span> if the difficulty is high
              enough, the first to <span className="font-medium text-foreground">cheap</span>.
            </p>
          ) : (
            <>
              <div className="prose prose-sm max-w-none whitespace-pre-wrap leading-relaxed">
                {answer}
                {loading ? (
                  <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-primary align-middle" />
                ) : null}
              </div>
              {!loading && answer ? (
                <p className="mt-4 border-t border-border pt-3 text-xs text-muted-foreground">
                  Compressed prompt was {meta ? `${meta.compressed_tokens} tokens` : "—"} · Answer
                  above is from{" "}
                  <span className="font-medium text-foreground">
                    {meta?.model_routed ?? "the routed tier"}
                  </span>{" "}
                  via the compressed prompt, so you can see it stays correct and coherent.
                </p>
              ) : null}
            </>
          )}
        </Card>
        <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
          What&apos;s real vs illustrative: compression, scoring, routing decision and the answer
          call are real live gateway calls. Tier names and per-1k prices are reference 2026 API
          rates from <code className="rounded bg-secondary px-1 py-0.5">pricing.py</code>. In
          dry-run the tier&apos;s model reply is a deterministic mock so you can exercise the whole
          pipeline without keys — set{" "}
          <code className="rounded bg-secondary px-1 py-0.5">GATEWAY_DRY_RUN=false</code> and real
          keys to call Groq / OpenAI / Ollama directly.
        </p>
      </div>
    </Page>
  );
}
