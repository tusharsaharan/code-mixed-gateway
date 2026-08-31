import { createFileRoute, Link } from "@tanstack/react-router";
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
  fetchDifficultyFeatures,
  fetchRewardAutopsy,
  fetchCompressCandidates,
  fetchPrompts,
  type DifficultyAnatomyResp,
  type RewardAutopsyResp,
  type CompressCandidatesResp,
  type PromptsResp,
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

  const [anatomy, setAnatomy] = useState<DifficultyAnatomyResp | null>(null);
  const [autopsy, setAutopsy] = useState<RewardAutopsyResp | null>(null);
  const [candidates, setCandidates] = useState<CompressCandidatesResp | null>(null);
  const [prompts, setPrompts] = useState<PromptsResp | null>(null);

  const [compView, setCompView] = useState<"shred" | "candidates">("shred");
  const [reproMode, setReproMode] = useState(false);
  const [copiedCurl, setCopiedCurl] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  // health probe + prompts
  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then(() => {
        if (!cancelled) setHealthOk(true);
      })
      .catch(() => {
        if (!cancelled) setHealthOk(false);
      });
    fetchPrompts()
      .then((p) => {
        if (!cancelled) setPrompts(p);
      })
      .catch(() => null);
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
    setAnatomy(null);
    setAutopsy(null);
    setCandidates(null);
    setTaskId(null);

    try {
      // 1) Parallel fetch: compress + reasoning budget + difficulty features + candidates
      const [cRes, rBudget, anat, cands] = await Promise.all([
        compressText(trimmed, method),
        fetchReasoningBudget(trimmed).catch(() => null),
        fetchDifficultyFeatures(trimmed).catch(() => null),
        fetchCompressCandidates(trimmed).catch(() => null),
      ]);
      if (ac.signal.aborted) return;
      setCompressRes(cRes);
      if (rBudget) setReasoning(rBudget);
      if (anat) setAnatomy(anat);
      if (cands) setCandidates(cands);

      // Fetch autopsy for the compressed output
      if (cRes) {
        fetchRewardAutopsy(trimmed, cRes.compressed)
          .then((a) => {
            if (!ac.signal.aborted) setAutopsy(a);
          })
          .catch(() => null);
      }

      // 2) full gateway chat (stream or not)
      if (useStream) {
        let full = "";
        let gotMeta: GatewayMeta | null = null;
        for await (const chunk of streamChatCompletion(trimmed)) {
          if (ac.signal.aborted) return;
          if (chunk.meta) {
            gotMeta = chunk.meta;
            setMeta(chunk.meta);
            // when meta arrives, merge delta if present
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
        if (!gotMeta) {
          const fallback = await chatCompletion(trimmed);
          if (!ac.signal.aborted) {
            setAnswer(fallback.choices[0]?.message.content ?? full);
            if (fallback.x_gateway) setMeta(fallback.x_gateway);
            if (fallback.id) setTaskId(fallback.id);
          }
        }
      } else {
        const res = await chatCompletion(trimmed);
        if (ac.signal.aborted) return;
        setAnswer(res.choices[0]?.message.content ?? "");
        if (res.x_gateway) setMeta(res.x_gateway);
        if (res.id) setTaskId(res.id);
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
    setAnatomy(null);
    setAutopsy(null);
    setCandidates(null);
    setTaskId(null);
    setError(null);
    setLoading(false);
  }, []);

  const curlCommand = `curl -X POST "${GATEWAY_URL || "http://127.0.0.1:8000"}/v1/chat/completions" \\
  -H "Content-Type: application/json" \\
  -d '{\n    "model": "cascade",\n    "messages": [{"role": "user", "content": "${input.replace(/"/g, '\\"').replace(/\n/g, " ")}"}]\n  }'`;

  const copyCurl = () => {
    navigator.clipboard.writeText(curlCommand);
    setCopiedCurl(true);
    setTimeout(() => setCopiedCurl(false), 2000);
  };

  const copyMetaJson = () => {
    if (!meta) return;
    navigator.clipboard.writeText(JSON.stringify(meta, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  const diff = compressRes ? wordDiff(compressRes.original, compressRes.compressed) : null;
  const charCount = input.length;
  const overLimit = charCount > 4000;

  return (
    <Page
      eyebrow="Live demo"
      title="Run a prompt through the gateway"
      lede="Compression, conformal routing and the answer happen live — tokens, tier and savings update as the gateway streams. Dry-run by default, real models when keys are set."
    >
      <div className="-mx-6 -mt-12 mb-6">
        <LiveTicker />
      </div>
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
            <label className="inline-flex items-center gap-1.5 text-muted-foreground">
              <input
                type="checkbox"
                checked={reproMode}
                onChange={(e) => setReproMode(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-input"
              />
              Reproducibility mode
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
            <button
              type="button"
              onClick={copyCurl}
              className="rounded-lg border border-border bg-card px-3 py-2 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground"
              title="Copy copy-pasteable curl for this query"
            >
              {copiedCurl ? "✓ Copied cURL" : "Copy cURL"}
            </button>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            <span className="font-medium text-foreground">auto</span> uses distilled if available,
            else model when not dry-run, else heuristic.{" "}
            <span className="font-medium text-foreground">adaptive</span> is code-mix-aware (novel):
            keeps more for Hinglish/math-heavy, compresses aggressively for light English. Protected
            spans are masked before compression and re-injected fail-closed ·{" "}
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

        {/* compression preview + candidate explorer */}
        <Card className={compressRes ? "" : "bg-secondary/30"}>
          <div className="flex items-center justify-between">
            <SectionHeading kicker="Compression" title="What got cut" />
            {candidates && candidates.candidates.length > 0 ? (
              <div className="flex gap-1 rounded-lg border border-border bg-secondary/50 p-0.5 text-xs">
                <button
                  type="button"
                  onClick={() => setCompView("shred")}
                  className={`rounded-md px-2 py-1 ${compView === "shred" ? "bg-card text-foreground font-medium shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                >
                  Shred
                </button>
                <button
                  type="button"
                  onClick={() => setCompView("candidates")}
                  className={`rounded-md px-2 py-1 ${compView === "candidates" ? "bg-card text-foreground font-medium shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                >
                  5 Candidates
                </button>
              </div>
            ) : null}
          </div>

          {!compressRes ? (
            <p className="text-sm leading-relaxed text-muted-foreground">
              Run the gateway to see the compressed prompt, token counts and which filler words were
              dropped. Protected spans like{" "}
              <code className="rounded bg-secondary px-1 py-0.5 text-xs">user@example.com</code> are
              never removed.
            </p>
          ) : compView === "candidates" && candidates ? (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-muted-foreground">
                Rejection-sampling distillation search across 5 candidate variants:
              </p>
              <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                {candidates.candidates.map((c) => (
                  <div
                    key={c.index}
                    className={`rounded-xl border p-2.5 text-xs transition-colors ${c.is_winner ? "border-primary/40 bg-primary/[0.04]" : "border-border bg-card"}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] font-medium">
                        #{c.index + 1} · {c.tokens} tok ({(c.compression_ratio * 100).toFixed(0)}%
                        kept)
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 font-mono text-[10px] ${c.is_winner ? "bg-primary text-primary-foreground font-bold" : "bg-secondary text-muted-foreground"}`}
                      >
                        {c.is_winner ? "Winner ★" : `reward ${c.reward.toFixed(3)}`}
                      </span>
                    </div>
                    <p className="mt-1 font-mono text-muted-foreground line-clamp-2">{c.text}</p>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground">
                * Distilled CPU fallback executes rejection sampling over candidates scored by task
                reward.
              </p>
            </div>
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
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Shred — watch filler fall
                </p>
                <div className="mt-2 min-h-[28px]">
                  <Shred
                    original={compressRes.original}
                    compressed={compressRes.compressed}
                    active={!loading}
                  />
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
                  <p className="mt-3 text-xs text-muted-foreground">
                    Nothing dropped — already minimal.
                  </p>
                )}
              </div>
              {/* inline reward autopsy */}
              {autopsy ? (
                <div className="mt-3 rounded-xl border border-primary/20 bg-primary/[0.02] p-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-foreground">Reward autopsy</span>
                    <span className="font-mono font-medium text-primary">
                      score {autopsy.combined_reward.toFixed(4)}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    0.70 × fidelity ({autopsy.answer_fidelity.toFixed(3)}) + 0.30 × faithfulness (
                    {autopsy.faithfulness.toFixed(3)})
                  </p>
                </div>
              ) : null}
              <p className="mt-3 font-mono text-xs leading-relaxed text-muted-foreground">
                Original: <span className="text-foreground">{compressRes.original}</span>
              </p>
            </>
          )}
        </Card>
      </div>

      {/* routing + difficulty anatomy + cost + reasoning */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Routing card with Difficulty Anatomy */}
        <Card>
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Routing & Difficulty Anatomy
          </p>
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

              {/* 4-bar difficulty decomposition */}
              {anatomy ? (
                <div className="mt-4 space-y-2 border-y border-border py-3 text-xs">
                  <p className="font-medium text-muted-foreground">Feature decomposition:</p>
                  <div>
                    <div className="flex justify-between text-[11px]">
                      <span>Code-Mix (40%)</span>
                      <span className="font-mono">+{anatomy.contrib_code_mix.toFixed(3)}</span>
                    </div>
                    <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full bg-primary"
                        style={{
                          width: `${Math.min(100, (anatomy.contrib_code_mix / 0.4) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-[11px]">
                      <span>Entity Density (30%)</span>
                      <span className="font-mono">+{anatomy.contrib_entity.toFixed(3)}</span>
                    </div>
                    <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full bg-blue-500"
                        style={{ width: `${Math.min(100, (anatomy.contrib_entity / 0.3) * 100)}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-[11px]">
                      <span>Math Markers (20%)</span>
                      <span className="font-mono">+{anatomy.contrib_math.toFixed(3)}</span>
                    </div>
                    <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full bg-amber-500"
                        style={{ width: `${Math.min(100, (anatomy.contrib_math / 0.2) * 100)}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-[11px]">
                      <span>Length (10%)</span>
                      <span className="font-mono">+{anatomy.contrib_length.toFixed(3)}</span>
                    </div>
                    <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full bg-purple-500"
                        style={{ width: `${Math.min(100, (anatomy.contrib_length / 0.1) * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              ) : null}

              <dl className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Total Difficulty</dt>
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
              </dl>
            </>
          )}
        </Card>

        <Card>
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Cost & Savings
          </p>
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
                Pricing via <code className="rounded bg-secondary px-1 py-0.5">pricing.py</code> at{" "}
                <span className="font-medium">2026-08-28</span> · CHEAP $0.00006 / PREMIUM $0.0025
                per 1k tokens.
              </p>
              {taskId ? (
                <div className="mt-4 pt-3 border-t border-border">
                  <Link
                    to="/receipt/$id"
                    params={{ id: taskId }}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/[0.04] px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/[0.08]"
                  >
                    🧾 View query receipt #{taskId.slice(-8)} →
                  </Link>
                </div>
              ) : null}
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
                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3 text-xs text-muted-foreground">
                  <span>
                    Compressed prompt was {meta ? `${meta.compressed_tokens} tokens` : "—"} · Routed
                    to{" "}
                    <span className="font-medium text-foreground">
                      {meta?.model_routed ?? "routed tier"}
                    </span>
                    .
                  </span>
                  {meta ? (
                    <button
                      type="button"
                      onClick={copyMetaJson}
                      className="rounded bg-secondary px-2 py-1 text-xs hover:text-foreground"
                    >
                      {copiedJson ? "✓ Copied x_gateway" : "Copy x_gateway JSON"}
                    </button>
                  ) : null}
                </div>
              ) : null}
            </>
          )}
        </Card>
      </div>

      {/* Reproducibility Mode drawer */}
      {reproMode ? (
        <div className="mt-6 space-y-4 rounded-2xl border border-primary/30 bg-card p-5">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.16em] text-primary font-semibold">
              Raw Protocol & Reproducibility Exposure (Commit {prompts?.commit_sha ?? "003d033"})
            </p>
            <button
              type="button"
              onClick={copyCurl}
              className="rounded bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground"
            >
              {copiedCurl ? "✓ Copied" : "Copy cURL"}
            </button>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">Exact cURL Command:</p>
              <pre className="overflow-x-auto rounded-xl border border-border bg-secondary/50 p-3 font-mono text-[11px] text-foreground">
                {curlCommand}
              </pre>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">System Prompt Sent:</p>
              <pre className="overflow-x-auto max-h-[160px] rounded-xl border border-border bg-secondary/50 p-3 font-mono text-[11px] text-foreground whitespace-pre-wrap">
                {prompts?.compress_system_prompt ?? "Loading system prompt..."}
              </pre>
            </div>
          </div>
          {meta ? (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">
                Full x_gateway Header JSON:
              </p>
              <pre className="overflow-x-auto rounded-xl border border-border bg-secondary/50 p-3 font-mono text-[11px] text-foreground">
                {JSON.stringify(meta, null, 2)}
              </pre>
            </div>
          ) : null}
        </div>
      ) : null}
    </Page>
  );
}
