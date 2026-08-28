import { createFileRoute } from "@tanstack/react-router";
import { Card, DataTable, Page, SectionHeading } from "../components/site/SiteChrome";

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
  component: BenchmarkPage,
});

function BenchmarkPage() {
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
              Real support-chat-style Hindi–English queries: romanized Hindi, Devanagari, English and
              genuine mid-sentence code-switching.
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
              <span className="font-medium text-foreground">4.</span> Convert token counts to ₹ and $
              at API pricing on a stated date — pricing moves, so the date ships with the number.
            </li>
            <li>
              <span className="font-medium text-foreground">5.</span> Plot the ratio-versus-accuracy
              curve per tier and per language mix.
            </li>
          </ol>
        </Card>
      </div>

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
            ["difficulty_score", "Router input, retained so it can serve as conformal calibration data"],
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
            Large enough to serve as a conformal calibration set. This gate blocks pillar B, so it is
            protected in the schedule.
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
