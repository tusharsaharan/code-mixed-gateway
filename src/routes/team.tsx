import { createFileRoute } from "@tanstack/react-router";
import { Card, DataTable, Page, SectionHeading } from "../components/site/SiteChrome";

export const Route = createFileRoute("/team")({
  head: () => ({
    meta: [
      { title: "Team & Compute — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "The 80/10/10 team split and the compute tiering strategy — free GPUs first, rented bursts for training.",
      },
      { property: "og:title", content: "Team & Compute — Code-Mixed LLM Gateway" },
    ],
  }),
  component: TeamPage,
});

const SPLIT = [
  [
    "Research Lead · 80%",
    "Pillars A, B, C — training the compressor, the conformal router, the reasoning-budget controller, experiments and writeup",
    "The genuinely novel, exploratory ML work; needs deep continuity, doesn't parallelize cleanly",
  ],
  [
    "Data & Eval Lead · 10%",
    "Building the benchmark, running the eval suite across pillars, charts/tables, scheduling compute",
    "Structured and scriptable — real, meaningful, but doesn't need constant judgment calls",
  ],
  [
    "Platform Lead · 10%",
    "Gateway engineering via Antigravity, the Telegram bot, HF Space + dashboard, user recruitment, monitoring",
    "Building is fast with AI tools now; this doesn't need more time to be a real contribution",
  ],
];

const COMPUTE = [
  [
    "Kaggle (free)",
    "Daily experimentation, small training runs",
    "30 hrs/week, most reliable free tier",
  ],
  ["Colab (free)", "Overflow, quick tests", "Unreliable GPU availability"],
  [
    "HF ZeroGPU Spaces (free)",
    "Hosting the public demo/dashboard",
    "H200-class hardware, no card needed",
  ],
  ["Lightning AI (free)", "Persistent dev environment", "80 hrs/month"],
  ["RunPod / Vast.ai (~$1–2/hr)", "GRPO/DPO training bursts", "Use sparingly, budget it"],
  [
    "Groq / Cerebras (free API)",
    "Fast inference for the big cascade tier",
    "Inference only, no training",
  ],
  [
    "Your department",
    "Ask directly given the expanded scope",
    "Many CS depts have a cluster or credits",
  ],
];

function TeamPage() {
  return (
    <Page
      eyebrow="People & compute"
      title="An 80 / 10 / 10 split with free GPUs first"
      lede="Three clear owners, sized to the kind of work each one does — plus a compute strategy that spends zero before renting."
    >
      <SectionHeading kicker="Team" title="Who owns what" />
      <DataTable head={["Role", "Owns", "Why this split"]} rows={SPLIT} />

      <div className="mt-14">
        <SectionHeading kicker="Compute" title="Where to train and host" />
        <DataTable head={["Tier", "Use it for", "Notes"]} rows={COMPUTE} />
      </div>

      <div className="mt-14 grid gap-6 sm:grid-cols-2">
        <Card className="bg-secondary/40">
          <h3 className="text-lg">Model stack</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Qwen3.6 open weights (Apache 2.0) for the compressor and mid-tier cascade, Gemma 4 for
            the multilingual code-mixed angle, DeepSeek-R1-distill or gpt-oss for the
            reasoning-budget executor.
          </p>
        </Card>
        <Card>
          <h3 className="text-lg">Budgeting rule</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Free tiers are the daily driver and the hosting layer. Rented A100/H100 spot instances
            are reserved for the heavier GRPO/DPO bursts that worth-their-cost training requires —
            never for experiments that fit a T4.
          </p>
        </Card>
      </div>
    </Page>
  );
}
