import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card, DataTable, Page, SectionHeading } from "../components/site/SiteChrome";
import { fetchHealth, GATEWAY_URL } from "../lib/gateway";

export const Route = createFileRoute("/api")({
  head: () => ({
    meta: [
      { title: "API Reference — Code-Mixed Gateway" },
      {
        name: "description",
        content:
          "OpenAI-compatible endpoint plus gateway extensions: compression, reasoning budget, dashboard, evaluation and calibration.",
      },
    ],
  }),
  component: ApiPage,
});

function Code({ children }: { children: string }) {
  return <code className="rounded bg-secondary px-1.5 py-0.5 font-mono text-xs">{children}</code>;
}

function ApiPage() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => {});
  }, []);

  const base = GATEWAY_URL || "http://127.0.0.1:8000";
  const baseNote = GATEWAY_URL
    ? `VITE_GATEWAY_URL=${GATEWAY_URL}`
    : "proxy in dev (/v1 → 127.0.0.1:8000) — set VITE_GATEWAY_URL in production";
  return (
    <Page
      eyebrow="Reference"
      title="Gateway API — OpenAI-compatible + extensions"
      lede="Point any OpenAI SDK at the gateway by overriding the base URL. Every response carries execution metadata via the x_gateway field."
    >
      <div className="flex flex-wrap gap-3">
        <a
          href={`${base}/docs`}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Open Swagger /docs ↗
        </a>
        <a
          href={`${base}/healthz`}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium hover:bg-secondary"
        >
          GET /healthz
        </a>
        <a
          href={`${base}/v1/models`}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium hover:bg-secondary"
        >
          GET /v1/models
        </a>
      </div>
      <p className="mt-3 text-xs text-muted-foreground">{baseNote}</p>

      {health ? (
        <Card className="mt-6 bg-secondary/40">
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Live health</p>
          <pre className="mt-2 overflow-auto rounded bg-card p-3 text-xs leading-relaxed">
            {JSON.stringify(health, null, 2)}
          </pre>
        </Card>
      ) : null}

      <div className="mt-12">
        <SectionHeading kicker="Core" title="OpenAI-compatible chat" />
        <DataTable
          head={["Method", "Path", "Notes"]}
          rows={[
            [
              <Code>POST</Code>,
              <Code>/v1/chat/completions</Code>,
              "model: 'cascade' · messages · stream?: bool · temperature · user? · returns ChatCompletion + x_gateway",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/models</Code>,
              "Lists cheap / premium / local-compressor tier models",
            ],
            [
              <Code>GET</Code>,
              <Code>/healthz</Code>,
              "Dry-run flag, version, calibration_n, threshold, models, pricing_date",
            ],
          ]}
        />
        <Card className="mt-4">
          <h3 className="text-sm font-medium">Example — Python (OpenAI SDK)</h3>
          <pre className="mt-3 overflow-auto rounded-lg bg-secondary/60 p-4 font-mono text-xs leading-relaxed">
            {`from openai import OpenAI
client = OpenAI(base_url="${base}/v1", api_key="not-needed-in-dry-run")
resp = client.chat.completions.create(
  model="cascade",
  messages=[{"role": "user", "content": "yaar email bhejna hai user@example.com"}],
)
print(resp.choices[0].message.content)
print(resp.model_extra["x_gateway"])  # if using httpx directly, inspect raw JSON`}
          </pre>
          <pre className="mt-3 overflow-auto rounded-lg bg-secondary/60 p-4 font-mono text-xs leading-relaxed">
            {`curl -s ${base}/v1/chat/completions \\
  -H 'Content-Type: application/json' \\
  -d '{"model":"cascade","messages":[{"role":"user","content":"hostel wifi slow hai, kya karu?"}]}' | jq .x_gateway`}
          </pre>
        </Card>
      </div>

      <div className="mt-12">
        <SectionHeading kicker="Extensions" title="Gateway-specific endpoints" />
        <DataTable
          head={["Method", "Path", "What it returns"]}
          rows={[
            [
              <Code>POST</Code>,
              <Code>/v1/compress</Code>,
              "{text, method?} → CompressResult (heuristic|distilled|model|auto)",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/compress/methods</Code>,
              "Lists supported compressor methods",
            ],
            [
              <Code>POST</Code>,
              <Code>/v1/reasoning/budget</Code>,
              "{text, english_gloss?} → reasoning_tokens + code-mix + math/logic counts + delta",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/reasoning/compare?hinglish=&english=</Code>,
              "Side-by-side budget comparison (publishable delta)",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/tokenizer/report</Code>,
              "Per-tokenizer inflation vs gpt4o_cl100k for Hinglish seed",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/dashboard/stats</Code>,
              "DashboardStats: queries, tokens, savings, tier_split",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/dashboard/series?window=3600</Code>,
              "Time-bucketed series points",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/dashboard/recent?limit=20</Code>,
              "Most recent pilot rows",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/eval/curve</Code>,
              "Fig-1 ratio-vs-accuracy points for heuristic/distilled/llmlingua2",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/eval/summary</Code>,
              "EvalSummary with BLEU/ROUGE-L/task success + ₹/$ costs",
            ],
            [
              <Code>GET</Code>,
              <Code>/v1/calibration/metrics</Code>,
              "n, α, τ, ECE, reliability diagram, simple + Hoeffding error bounds",
            ],
            [
              <Code>GET</Code>,
              <Code>/dashboard</Code>,
              "Static HTML pilot dashboard (no build step)",
            ],
          ]}
        />
      </div>

      <div className="mt-10 grid gap-5 sm:grid-cols-2">
        <Card>
          <h3 className="text-lg">Streaming</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Pass <Code>stream: true</Code>. The first SSE chunk carries <Code>x_gateway</Code>{" "}
            routing metadata; subsequent chunks carry <Code>delta.content</Code> tokens, ending with{" "}
            <Code>data: [DONE]</Code>. The demo and gateway streaming both log to the pilot DB on
            completion.
          </p>
        </Card>
        <Card>
          <h3 className="text-lg">x_gateway fields</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            <Code>original_tokens</Code>, <Code>compressed_tokens</Code>,{" "}
            <Code>compression_ratio</Code>, <Code>compressed_prompt</Code>,{" "}
            <Code>difficulty_score</Code>, <Code>conformal_threshold</Code>, <Code>tier</Code>,{" "}
            <Code>model_routed</Code>, <Code>estimated_cost_usd</Code>,{" "}
            <Code>estimated_cost_savings_usd</Code>, <Code>reasoning_budget</Code>,{" "}
            <Code>budget_delta_hinglish_en</Code>, <Code>error_bound</Code>,{" "}
            <Code>calibration_n</Code>.
          </p>
        </Card>
      </div>

      <div className="mt-8 flex gap-3">
        <Link
          to="/demo"
          className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Try the live demo
        </Link>
        <Link
          to="/analytics"
          className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium hover:bg-secondary"
        >
          Open analytics
        </Link>
      </div>
    </Page>
  );
}
