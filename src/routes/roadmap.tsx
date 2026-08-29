import { createFileRoute } from "@tanstack/react-router";
import { Card, DataTable, Page, SectionHeading } from "../components/site/SiteChrome";

export const Route = createFileRoute("/roadmap")({
  head: () => ({
    meta: [
      { title: "12-Week Roadmap — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "The twelve-week plan from setup and baselines through training, a live pilot, analysis and an open release.",
      },
      { property: "og:title", content: "12-Week Roadmap — Code-Mixed LLM Gateway" },
    ],
  }),
  component: RoadmapPage,
});

const WEEKS = [
  {
    w: "1–2",
    focus: "Setup",
    m: "Compute accounts live, gateway skeleton up, professor scope email, benchmark v0 collection starts.",
  },
  {
    w: "3–4",
    focus: "Baselines",
    m: "Baseline compression + naive cascade numbers; recruit the first test users.",
  },
  {
    w: "5–6",
    focus: "Pillar A",
    m: "Train the reward-based compressor; compare against baseline on the ratio-vs-accuracy chart.",
  },
  {
    w: "7",
    focus: "Pillar B",
    m: "Build the conformal cascade router; measure calibration (ECE) before/after.",
  },
  {
    w: "8",
    focus: "Pillar C",
    m: "Reasoning-budget controller; test the Hinglish-vs-English budget question.",
  },
  {
    w: "9",
    focus: "Integration",
    m: "Merge all pillars into one gateway; stand up the dashboard.",
  },
  {
    w: "10",
    focus: "Live pilot",
    m: "Deploy the Telegram bot + coding endpoint to real users; collect 1–2 weeks of traffic.",
  },
  {
    w: "11",
    focus: "Analysis",
    m: "Analyze real traffic against benchmark predictions; refine thresholds.",
  },
  {
    w: "12",
    focus: "Wrap-up",
    m: "Final report / optional arXiv preprint, open-source release, demo day, community post.",
  },
];

const TARGETS = [
  ["≥15× compression", "on code-mixed text at ≤5–8% task-accuracy loss"],
  ["Provable bound", "a conformal accuracy bound stated as a guarantee, not an estimate"],
  ["≥40% cost reduction", "measured on live traffic against an always-large-model baseline"],
  ["Real users", "a real count of real queries from the pilot — the single fact that matters most"],
  ["Open release", "GitHub repo + Hugging Face dataset; arXiv as a stretch goal"],
];

function RoadmapPage() {
  return (
    <Page
      eyebrow="Plan"
      title="Twelve weeks, four pillars, one live pilot"
      lede="The schedule protects the two things that matter most: a sizeable calibration set before pillar B, and real users before the analysis phase — both of which are easier to slip than the training."
    >
      <SectionHeading kicker="Timeline" title="Milestones by week" />
      <div className="space-y-4">
        {WEEKS.map((s) => (
          <Card key={s.w}>
            <div className="grid gap-2 sm:grid-cols-[80px_140px_1fr] sm:items-baseline">
              <span className="font-serif text-xl text-primary">Wk {s.w}</span>
              <span className="text-sm font-medium">{s.focus}</span>
              <span className="text-sm leading-relaxed text-muted-foreground">{s.m}</span>
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-14">
        <SectionHeading kicker="Targets, not results" title="What impressive looks like" />
        <DataTable head={["Target", "Why it counts"]} rows={TARGETS} />
      </div>

      <div className="mt-14 grid gap-6 sm:grid-cols-3">
        <Card>
          <h3 className="text-lg">If RL is unstable</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Keep rejection-sampling distillation ready as a fallback so pillar A degrades to
            quality, never to nothing.
          </p>
        </Card>
        <Card>
          <h3 className="text-lg">If the calibration set is small</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Conformal guarantees need enough calibration data — benchmark v0 must be sizeable by
            week 5, before pillar B.
          </p>
        </Card>
        <Card>
          <h3 className="text-lg">If users are slow to arrive</h3>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Recruitment starts in weeks 1–2, not week 10 — invite the first test users before the
            system is polished.
          </p>
        </Card>
      </div>
    </Page>
  );
}
