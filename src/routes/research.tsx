import { createFileRoute } from "@tanstack/react-router";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";

export const Route = createFileRoute("/research")({
  head: () => ({
    meta: [
      { title: "Research Pillars — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "Four pillars: a reward-trained compressor, a conformally-calibrated cascade router, a reasoning-budget controller, and the serving layer.",
      },
      { property: "og:title", content: "Research Pillars — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "Reward-trained compression, conformal cascade routing, reasoning-budget control and serving infrastructure for code-mixed text.",
      },
      {
        property: "og:description",
        content:
          "Reward-trained compression, conformal cascade routing, reasoning-budget control and serving infrastructure for code-mixed text.",
      },
    ],
  }),
  component: ResearchPage,
});

const PILLARS = [
  {
    tag: "A",
    title: "A reward-trained compressor for code-mixed text",
    what: "Rather than calling an off-the-shelf compression library, train a small compressor from an open dense backbone using GRPO or DPO-style RL, where the reward is actual downstream task correctness on code-mixed input.",
    novel:
      "Reward-optimized compression is the current frontier direction, but no open implementation targets code-mixed or informal business text. This is the strongest 'nobody has done this' claim in the project.",
    fallback:
      "Training-free path: prompt a capable model to compress while preserving every task-critical detail, or use classic perplexity-based token pruning. If RL is unstable, fall back to rejection-sampling distillation.",
  },
  {
    tag: "B",
    title: "A conformally-calibrated cascade router",
    what: "Wrap the escalation decision in conformal risk control so the cascade carries a distribution-free, finite-sample bound on accuracy — instead of a hand-tuned confidence threshold.",
    novel:
      "Turns 'it seems to work' into a stated guarantee. Comparable industrial pilots closing this loop reported roughly 58% cost reduction against 62% predicted from offline benchmarks — a validation target as well as a template.",
    fallback:
      "Conformal calibration is statistics applied to model outputs already being collected, not a trained network — it stays fully in play even with zero training compute. It only needs a calibration set large enough, which is why benchmark v0 must be sizeable by week 5.",
  },
  {
    tag: "C",
    title: "A reasoning-budget controller",
    what: "Train a small predictor that estimates how many thinking tokens a query actually needs before generation begins, using an open reasoning model as the executor.",
    novel:
      "The open side-question nobody has asked: does a Hinglish math or logic query need a different reasoning budget than its English equivalent? A clean answer either way is a publishable finding.",
    fallback:
      "Budget can be set through prompting and API reasoning parameters instead of a trained predictor, which keeps the research question answerable without training compute.",
  },
  {
    tag: "D",
    title: "Serving infrastructure",
    what: "A single OpenAI-compatible gateway endpoint over a high-throughput serving stack with prefix caching and speculative decoding, exposing compression, routing and budget control as one API.",
    novel:
      "Not novel, and deliberately so — this is the fast engineering layer that makes the research usable by real users and by classmates' coding tools.",
    fallback:
      "Ship a dumb pass-through gateway in week 1 so something is live early, then add each pillar behind the same endpoint.",
  },
];

function ResearchPage() {
  return (
    <Page
      eyebrow="Research"
      title="Four pillars, each with a training-free path if compute runs out"
      lede="The research direction does not depend on training succeeding. Every pillar has a version that can be built with statistics and prompting alone, so a compute failure costs quality — never the contribution."
    >
      <div className="space-y-6">
        {PILLARS.map((p) => (
          <Card key={p.tag}>
            <div className="flex flex-wrap items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-accent font-serif text-lg text-accent-foreground">
                {p.tag}
              </span>
              <h2 className="text-2xl">{p.title}</h2>
            </div>
            <div className="mt-6 grid gap-6 md:grid-cols-3">
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  What gets built
                </p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.what}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Why it is novel
                </p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.novel}</p>
              </div>
              <div className="rounded-xl bg-secondary/50 p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                  Training-free fallback
                </p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.fallback}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-14">
        <SectionHeading kicker="Model stack" title="Open weights, clean licenses" />
        <div className="grid gap-5 sm:grid-cols-3">
          <Card>
            <h3 className="text-lg">Compressor backbone</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              A small dense open-weight model under a permissive license, chosen for tokenizer
              behaviour on Devanagari and romanized Hindi as much as for raw quality.
            </p>
          </Card>
          <Card>
            <h3 className="text-lg">Cascade tiers</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              A small local model for the cheap tier, a hosted open model on fast inference hardware
              for the mid tier, and a frontier API only for escalated queries.
            </p>
          </Card>
          <Card>
            <h3 className="text-lg">Reasoning executor</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              An open reasoning-distilled model whose thinking tokens can be measured and budgeted
              directly, so the controller is evaluated on observable behaviour.
            </p>
          </Card>
        </div>
      </div>
    </Page>
  );
}
