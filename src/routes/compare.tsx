import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";
import { fetchReasoningBudget } from "../lib/gateway";

export const Route = createFileRoute("/compare")({
  head: () => ({
    meta: [
      { title: "Hinglish ↔ English — Reasoning Budget Compare" },
      {
        name: "description",
        content:
          "Test whether a Hinglish query needs a different reasoning budget than its English equivalent — the report's publishable side-finding.",
      },
    ],
  }),
  component: ComparePage,
});

function ComparePage() {
  const PAIRS: [string, string][] = [
    [
      "arre yaar physics ka numerical solve karo 5*3+2 ka answer batao",
      "solve this physics numerical 5*3+2 and tell the answer",
    ],
    [
      "hostel ka wifi bahut slow chal raha hai, complaint kahan karni hai?",
      "the hostel wifi is very slow, where do I file a complaint?",
    ],
    [
      "yaar matlab mera email user@example.com par bhejo na",
      "please send my email to user@example.com",
    ],
  ];

  const [hinglish, setHinglish] = useState(PAIRS[0]?.[0] ?? "");
  const [english, setEnglish] = useState(PAIRS[0]?.[1] ?? "");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<unknown | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const [hi, en] = await Promise.all([
        fetchReasoningBudget(hinglish),
        fetchReasoningBudget(english),
      ]);
      const delta = hi.reasoning_tokens - en.reasoning_tokens;
      setResult({ hinglish: hi, english: en, delta });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Page
      eyebrow="Pillar C"
      title="Does Hinglish need a different reasoning budget?"
      lede="Run the fast budget estimator on a Hinglish query and its English gloss side by side. The delta is the publishable finding from the report — answer it honestly on your data."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Hinglish</p>
          <textarea
            value={hinglish}
            onChange={(e) => setHinglish(e.target.value)}
            rows={4}
            className="mt-2 w-full rounded-xl border border-border bg-card p-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-ring"
          />
        </Card>
        <Card>
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">English</p>
          <textarea
            value={english}
            onChange={(e) => setEnglish(e.target.value)}
            rows={4}
            className="mt-2 w-full rounded-xl border border-border bg-card p-3 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-ring"
          />
        </Card>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {PAIRS.map(([h, e]) => (
          <button
            key={h}
            type="button"
            onClick={() => {
              setHinglish(h);
              setEnglish(e);
              setResult(null);
            }}
            className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            {h.slice(0, 44)}…
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={run}
        disabled={loading || !hinglish.trim() || !english.trim()}
        className="mt-6 rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
      >
        {loading ? "Scoring…" : "Compare budgets"}
      </button>

      {error ? (
        <div className="mt-4 rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="mt-8">
          <SectionHeading kicker="Result" title="Budget comparison" />
          <div className="grid gap-6 sm:grid-cols-3">
            <Card>
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Hinglish budget
              </p>
              <p className="mt-2 font-serif text-3xl text-primary">
                {(result as { hinglish: { reasoning_tokens: number } }).hinglish.reasoning_tokens}
              </p>
              <pre className="mt-2 text-xs text-muted-foreground">
                {JSON.stringify((result as { hinglish: unknown }).hinglish, null, 2)}
              </pre>
            </Card>
            <Card>
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                English budget
              </p>
              <p className="mt-2 font-serif text-3xl text-primary">
                {(result as { english: { reasoning_tokens: number } }).english.reasoning_tokens}
              </p>
              <pre className="mt-2 text-xs text-muted-foreground">
                {JSON.stringify((result as { english: unknown }).english, null, 2)}
              </pre>
            </Card>
            <Card
              className={
                (result as { delta: number }).delta > 30
                  ? "border-amber-300 bg-amber-50/40"
                  : "bg-secondary/40"
              }
            >
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Δ (H − E)</p>
              <p className="mt-2 font-serif text-3xl text-primary">
                {(result as { delta: number }).delta > 0 ? "+" : ""}
                {(result as { delta: number }).delta}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Positive means the Hinglish variant requests more thinking tokens under the current
                estimator — a signal worth investigating on your full benchmark, not proof on its
                own.
              </p>
            </Card>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Estimator: base 128 + 120·code_mix + 96·math + 48·logic + 8·min(len,40), capped at 2048.
            No model call — purely observable features.
          </p>
        </div>
      ) : null}
    </Page>
  );
}
