import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";
import { fetchReceipt, sendFeedback, type ReceiptResp } from "../lib/gateway";

export const Route = createFileRoute("/receipt/$id")({
  head: () => ({
    meta: [
      { title: "Query Audit Receipt — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "Cryptographic audit receipt for routed queries with live human correctness feedback.",
      },
      { property: "og:title", content: "Query Audit Receipt — Code-Mixed LLM Gateway" },
    ],
  }),
  component: ReceiptPage,
});

function ReceiptPage() {
  const { id } = Route.useParams() as { id: string };
  const [receipt, setReceipt] = useState<ReceiptResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState<string | null>(null);
  const [view, setView] = useState<"full" | "minimal">("full");

  const loadReceipt = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchReceipt(id);
      setReceipt(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadReceipt();
  }, [loadReceipt]);

  const handleFeedback = async (wasCorrect: boolean) => {
    if (!receipt) return;
    setSubmitting(true);
    setFeedbackSuccess(null);
    try {
      const res = await sendFeedback(receipt.task_id, wasCorrect);
      setReceipt((prev: ReceiptResp | null) =>
        prev ? { ...prev, was_correct: wasCorrect } : null,
      );
      setFeedbackSuccess(
        res.recalibrated
          ? "Feedback logged & conformal risk model recalibrated live!"
          : "Feedback recorded successfully.",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Page
        eyebrow="Receipt"
        title="Loading audit receipt…"
        lede="Fetching query metrics from the gateway database."
      >
        <Card className="bg-secondary/40">
          <p className="text-sm text-muted-foreground">Retrieving receipt data for {id}…</p>
        </Card>
      </Page>
    );
  }

  if (error || !receipt) {
    return (
      <Page
        eyebrow="Receipt"
        title="Receipt Not Found"
        lede="Could not locate an audit record for this query ID."
      >
        <Card className="border-destructive/30 bg-destructive/10">
          <p className="text-sm text-destructive">Error: {error || "No receipt available."}</p>
          <div className="mt-4 flex gap-3">
            <button
              onClick={loadReceipt}
              className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground"
            >
              Retry
            </button>
            <Link
              to="/demo"
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
            >
              Back to Demo
            </Link>
          </div>
        </Card>
      </Page>
    );
  }

  const dateStr = new Date(receipt.ts * 1000).toLocaleString();
  const tokenRatio = (
    (receipt.compressed_tokens / Math.max(1, receipt.original_tokens)) *
    100
  ).toFixed(1);

  const anonUser = receipt.user_id
    ? `${receipt.user_id.slice(0, 4)}***${receipt.user_id.slice(-2)}`
    : "anon";

  return (
    <Page
      eyebrow="Audit Receipt"
      title={`Receipt #${receipt.task_id || receipt.id}`}
      lede="Cryptographic transparency: exact token counts, routing decisions, cost savings, and live evaluation feedback."
    >
      {/* Dual view toggle — do both options: full anonymized vs minimal */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card px-4 py-3">
        <div className="flex items-center gap-2 text-xs">
          <span className="uppercase tracking-[0.14em] text-muted-foreground">View</span>
          <div className="flex gap-1 rounded-lg border border-border bg-secondary/50 p-1">
            <button
              onClick={() => setView("full")}
              className={`rounded-md px-3 py-1 text-xs font-medium ${view === "full" ? "bg-card shadow-sm text-foreground" : "text-muted-foreground"}`}
            >
              Full (anonymized)
            </button>
            <button
              onClick={() => setView("minimal")}
              className={`rounded-md px-3 py-1 text-xs font-medium ${view === "minimal" ? "bg-card shadow-sm text-foreground" : "text-muted-foreground"}`}
            >
              Minimal (tokens only)
            </button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          {view === "full"
            ? "Shows anonymized user hash + compressed prompt — for audit, not PII"
            : "Hides user hash & prompt — shares only tier/tokens/savings"}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Details Card */}
        <Card className="lg:col-span-2">
          <SectionHeading kicker="Transaction" title="Query Metadata" />

          <dl className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 text-sm">
            <div className="rounded-xl border border-border bg-secondary/30 p-3.5">
              <dt className="text-xs uppercase tracking-wider text-muted-foreground">Task ID</dt>
              <dd className="mt-1 font-mono font-medium text-foreground">
                {receipt.task_id || receipt.id}
              </dd>
            </div>
            <div className="rounded-xl border border-border bg-secondary/30 p-3.5">
              <dt className="text-xs uppercase tracking-wider text-muted-foreground">Timestamp</dt>
              <dd className="mt-1 text-foreground">{dateStr}</dd>
            </div>
            <div className="rounded-xl border border-border bg-secondary/30 p-3.5">
              <dt className="text-xs uppercase tracking-wider text-muted-foreground">
                Tier Routed
              </dt>
              <dd className="mt-1 flex items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${receipt.tier === "premium" ? "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-100" : "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-100"}`}
                >
                  {receipt.tier}
                </span>
                <span className="font-mono text-xs text-muted-foreground">
                  {receipt.model_routed}
                </span>
              </dd>
            </div>
            {view === "full" ? (
              <>
                <div className="rounded-xl border border-border bg-secondary/30 p-3.5">
                  <dt className="text-xs uppercase tracking-wider text-muted-foreground">
                    User (anonymized)
                  </dt>
                  <dd className="mt-1 font-mono text-xs text-foreground">{anonUser}</dd>
                  <dd className="text-[11px] text-muted-foreground">hash, not PII</dd>
                </div>
                <div className="rounded-xl border border-border bg-secondary/30 p-3.5">
                  <dt className="text-xs uppercase tracking-wider text-muted-foreground">
                    Difficulty Score
                  </dt>
                  <dd className="mt-1 font-mono font-medium text-foreground">
                    {receipt.difficulty_score.toFixed(4)}
                  </dd>
                </div>
              </>
            ) : null}
          </dl>

          <div className="mt-6 border-t border-border pt-4">
            <SectionHeading kicker="Compression" title="Token & Savings Efficiency" />
            <div className="mt-3 grid grid-cols-3 gap-3 text-center">
              <div className="rounded-xl border border-border bg-card p-3">
                <p className="text-xs text-muted-foreground">Original Tokens</p>
                <p className="mt-1 font-mono text-lg font-bold text-foreground">
                  {receipt.original_tokens}
                </p>
              </div>
              <div className="rounded-xl border border-border bg-card p-3">
                <p className="text-xs text-muted-foreground">Compressed</p>
                <p className="mt-1 font-mono text-lg font-bold text-primary">
                  {receipt.compressed_tokens}
                </p>
                <p className="text-[10px] text-muted-foreground">{tokenRatio}% kept</p>
              </div>
              <div className="rounded-xl border border-border bg-card p-3">
                <p className="text-xs text-muted-foreground">Savings</p>
                <p className="mt-1 font-mono text-lg font-bold text-emerald-600 dark:text-emerald-400">
                  ${receipt.estimated_cost_savings.toFixed(5)}
                </p>
              </div>
            </div>
          </div>

          {view === "full" && receipt.compressed_prompt ? (
            <div className="mt-6 border-t border-border pt-4">
              <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
                Compressed Prompt Executed (anonymized view):
              </p>
              <pre className="overflow-x-auto rounded-xl border border-border bg-secondary/50 p-3 font-mono text-xs text-foreground whitespace-pre-wrap">
                {receipt.compressed_prompt}
              </pre>
            </div>
          ) : view === "minimal" ? (
            <p className="mt-4 text-xs italic text-muted-foreground">
              Minimal view hides prompt & user — share safely.
            </p>
          ) : null}
        </Card>

        {/* Feedback & Grounding Loop Card */}
        <Card>
          <SectionHeading kicker="Ground Truth" title="Was this response correct?" />
          <p className="text-xs leading-relaxed text-muted-foreground mt-2">
            Your evaluation directly grounds the live conformal calibration algorithm. Marking
            cheap-tier successes or failures tightens the risk bound.
          </p>

          <div className="mt-6 space-y-3">
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleFeedback(true)}
              className={`w-full flex items-center justify-center gap-2 rounded-xl border py-3 text-sm font-medium transition-all ${receipt.was_correct === true ? "border-emerald-500 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 ring-2 ring-emerald-500/20" : "border-border bg-card hover:bg-secondary text-foreground"}`}
            >
              <span>👍</span>
              <span>Yes, answer was correct</span>
              {receipt.was_correct === true ? " ✓" : ""}
            </button>

            <button
              type="button"
              disabled={submitting}
              onClick={() => handleFeedback(false)}
              className={`w-full flex items-center justify-center gap-2 rounded-xl border py-3 text-sm font-medium transition-all ${receipt.was_correct === false ? "border-red-500 bg-red-500/10 text-red-700 dark:text-red-300 ring-2 ring-red-500/20" : "border-border bg-card hover:bg-secondary text-foreground"}`}
            >
              <span>👎</span>
              <span>No, cheap tier failed</span>
              {receipt.was_correct === false ? " ✗" : ""}
            </button>
          </div>

          {feedbackSuccess ? (
            <div className="mt-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-200">
              {feedbackSuccess}
            </div>
          ) : null}

          <div className="mt-8 border-t border-border pt-4">
            <Link
              to="/demo"
              className="block text-center rounded-lg border border-border bg-secondary/60 py-2 text-xs font-medium text-foreground hover:bg-secondary"
            >
              ← Back to Live Demo
            </Link>
          </div>
        </Card>
      </div>
    </Page>
  );
}
