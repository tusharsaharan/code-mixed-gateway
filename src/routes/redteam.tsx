import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";
import {
  fetchChallenges,
  fetchRedteam,
  type ChallengesResp,
  type RedteamResp,
} from "../lib/gateway";

export const Route = createFileRoute("/redteam")({
  head: () => ({
    meta: [
      { title: "Break My Compressor — Red Team — Code-Mixed Gateway" },
      {
        name: "description",
        content:
          "Public gamified red-team: try to make the compressor drop a critical negation, order marker, number or protected span. Every break becomes free adversarial eval.",
      },
      { property: "og:title", content: "Break My Compressor — Red Team" },
    ],
  }),
  component: RedteamPage,
});

const PRESETS = [
  { label: "Negation trap", text: "please do NOT cancel my order #4829, amount Rs. 2,500" },
  { label: "Hinglish negation", text: "yaar Rs. 2,500 ka refund mat karna, order #4829 abhi" },
  { label: "Order matters", text: "first do step A before step B, then pay Rs. 1,200 on 12th May" },
  {
    label: "Code + amount",
    text: "my code is ```def foo(): return 42``` and amount is Rs. 2,500, do not delete",
  },
] as const;

const METHODS = ["adaptive", "heuristic", "distilled", "auto"] as const;

function RedteamPage() {
  const [input, setInput] = useState<string>(PRESETS[0].text);
  const [method, setMethod] = useState<(typeof METHODS)[number]>("adaptive");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RedteamResp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [board, setBoard] = useState<ChallengesResp | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);

  const loadBoard = useCallback(async () => {
    try {
      const b = await fetchChallenges(20);
      setBoard(b);
      setBoardError(null);
    } catch (e) {
      setBoardError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    loadBoard();
    const id = setInterval(loadBoard, 8000);
    return () => clearInterval(id);
  }, [loadBoard]);

  const handleTest = useCallback(async () => {
    const t = input.trim();
    if (!t) {
      setError("Enter a prompt to test");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetchRedteam(t, method);
      setResult(r);
      // refresh board after logging (backend auto-logs)
      setTimeout(loadBoard, 600);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [input, method, loadBoard]);

  return (
    <Page
      eyebrow="Adversarial · public gamified"
      title="Break my compressor"
      lede="Try to make compression drop something critical — a negation like “do NOT refund,” an order marker, a date/number, or a protected span. Every attempt is logged anonymously to the public leaderboard and becomes free adversarial eval for the writeup."
    >
      <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <Card>
          <SectionHeading kicker="Red-team input" title="Craft a trap" />
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={4}
            placeholder="Type a prompt with a critical detail that must not be dropped…"
            className="w-full rounded-xl border border-input bg-background px-3.5 py-3 text-sm leading-relaxed outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15"
          />
          <div className="mt-3 flex flex-wrap gap-1.5">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                onClick={() => setInput(p.text)}
                className="rounded-full border border-border bg-secondary/60 px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm">
              <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Method
              </span>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as typeof method)}
                className="rounded-lg border border-input bg-background px-2.5 py-2 text-sm"
              >
                {METHODS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </label>
            <button
              onClick={handleTest}
              disabled={loading || !input.trim()}
              className="rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
            >
              {loading ? "Testing…" : "Test break my compressor"}
            </button>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            Grader checks: <span className="font-medium text-foreground">negation</span> (not/nahi),{" "}
            <span className="font-medium text-foreground">order</span> (before/after/pehle/baad),{" "}
            <span className="font-medium text-foreground">number/amount</span> (Rs. 2,500, dates),
            and <span className="font-medium text-foreground">protected spans</span> (email, code,
            phone). Uses{" "}
            <code className="rounded bg-secondary px-1 py-0.5">POST /v1/compress/redteam</code>.
          </p>
          {error ? (
            <div className="mt-3 rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          ) : null}
          {result ? (
            <div
              className={`mt-4 rounded-xl border p-4 ${result.verdict === "break" ? "border-red-300 bg-red-50 dark:bg-red-950/20 dark:border-red-800" : "border-emerald-300 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-800"}`}
            >
              <p
                className={`text-sm font-semibold ${result.verdict === "break" ? "text-red-700 dark:text-red-300" : "text-emerald-700 dark:text-emerald-300"}`}
              >
                {result.verdict === "break"
                  ? `💥 Break! Dropped ${result.break_type}: ${result.critical_dropped.join(", ")}`
                  : "✅ Safe — compressor held, nothing critical dropped"}
              </p>
              <p className="mt-2 font-mono text-xs leading-relaxed">
                <span className="text-muted-foreground">Compressed:</span>{" "}
                <span className="text-foreground">{result.compressed}</span>
              </p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                {result.token_original}→{result.token_compressed} tok · ratio{" "}
                {(result.ratio * 100).toFixed(1)}% · reward {result.reward.toFixed(3)} · method{" "}
                {result.method}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                Original: <span className="font-mono text-foreground">{result.original}</span>
              </p>
            </div>
          ) : null}
        </Card>

        <Card>
          <SectionHeading kicker="Live leaderboard" title="Public gamified board" />
          {boardError ? (
            <p className="text-sm text-destructive">Failed to load board: {boardError}</p>
          ) : !board ? (
            <p className="text-sm text-muted-foreground">Loading leaderboard…</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-secondary px-2.5 py-1">
                  {board.total_attempts} attempts
                </span>
                <span className="rounded-full bg-red-100 px-2.5 py-1 text-red-900 dark:bg-red-900/30 dark:text-red-100">
                  {board.breaks_recent} breaks (recent {board.recent_n})
                </span>
                <span className="rounded-full border border-border bg-card px-2.5 py-1">
                  {Math.round(board.break_rate_recent * 100)}% break rate
                </span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                By type:{" "}
                {Object.entries(board.by_type)
                  .map(([k, v]) => `${k}:${v}`)
                  .join(" · ") || "—"}
              </p>
              <div className="mt-4 space-y-2 max-h-[320px] overflow-auto pr-1">
                {board.recent.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No attempts yet — be first.</p>
                ) : (
                  board.recent.slice(0, 12).map((c, i) => (
                    <div
                      key={i}
                      className={`rounded-xl border px-3 py-2.5 text-xs ${c.verdict === "break" ? "border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-800" : "border-border bg-secondary/30"}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate font-mono text-foreground">
                          {c.text.slice(0, 80)}
                        </span>
                        <span
                          className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${c.verdict === "break" ? "bg-red-600 text-white" : "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-100"}`}
                        >
                          {c.verdict}
                        </span>
                      </div>
                      {c.verdict === "break" ? (
                        <p className="mt-1 font-mono text-[11px] text-red-700 dark:text-red-300">
                          {c.break_type}: {c.critical_dropped.join(", ")} · {c.method}
                        </p>
                      ) : (
                        <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                          {c.method} · held
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                Every break is anonymized and becomes adversarial eval. Try to be on the board.{" "}
                <Link to="/demo" className="font-medium text-primary hover:underline">
                  Also in Demo →
                </Link>
              </p>
            </>
          )}
        </Card>
      </div>

      <div className="mt-10 rounded-2xl border border-primary/20 bg-primary/[0.04] p-5">
        <p className="text-xs uppercase tracking-[0.16em] text-primary">How grading works</p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          The grader is intentionally simple and auditable: it checks whether any token from the
          original’s critical set (negations, order markers, numbers/amounts, or protected spans
          detected via <code className="rounded bg-secondary px-1 py-0.5">safety_span.py</code>) is
          missing in the compressed output (case-insensitive, punctuation-normalized). No model
          judge — so a “break” is unambiguous and reproducible. See{" "}
          <code className="rounded bg-secondary px-1 py-0.5">POST /v1/compress/redteam</code> in{" "}
          <code className="rounded bg-secondary px-1 py-0.5">gateway/mcp.py</code>.
        </p>
      </div>
    </Page>
  );
}
