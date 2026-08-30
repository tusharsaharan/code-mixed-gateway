import { createFileRoute, Link } from "@tanstack/react-router";
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
    tag: "1",
    title: "Adaptive code-mix-aware compression (the flagship)",
    what: "A compressor that conditions its kept-ratio on measured code-mix ratio + difficulty. High Hinglish/math → keep 0.82–0.92 (conservative), light English → compress to 0.52 (aggressive). Built training-free via heuristic + truncation under a fail-closed safety-span mask.",
    novel:
      "No prior work conditions compression on code-mix. Our benchmark shows adaptive earns 35.0% token savings at 0.893 reward vs 1.3% at 0.995 for a fixed heuristic — 27× saving lift on the Pareto knee. The policy itself is the contribution, and POST /v1/compress method=adaptive is live.",
    fallback:
      "Training-free by design; the full GRPO/DPO RL path (reward = task correctness) remains as scale-up once GPU budget allows — adaptive policy supplies the offline teacher.",
  },
  {
    tag: "2",
    title: "Conformal fidelity guarantee for compression",
    what: "Wrap compression fidelity (reward ≥0.85) in Hoeffding LTT conformal risk control (grid 200, δ=0.05), producing a 95% upper bound — not just a point estimate — on how often compression preserves task correctness.",
    novel:
      "Prior work conformal-certifies routing; we certify compression fidelity itself — first on code-mixed text. Measured: adaptive risk̂ 0.02 → bound 0.308 on n=50. The guarantee is distribution-free and finite-sample.",
    fallback:
      "Pure statistics over collected rewards; no model training. Only needs enough benchmark rows (n≥50 already) — the bound tightens linearly with n.",
  },
  {
    tag: "3",
    title: "Hinglish reasoning-budget tax (publishable side-finding)",
    what: "A lightweight estimator (base 128 + code-mix + math/logic + length) plus a deterministic Hinglish→English gloss generator (no model call) gives paired Hinglish/English budgets for every benchmark item.",
    novel:
      "First measurement: Hinglish needs +56 reasoning tokens on average (median +60, 88% of pairs, n=50, range −20 to +120). Either direction would have been publishable; the measured tax is the result.",
    fallback:
      "Estimator is heuristic; with an open reasoning model (DeepSeek-R1-distill) the same delta can be re-measured on actual thinking tokens — the gloss protocol stays identical.",
  },
  {
    tag: "4",
    title: "Bucketed tokenizer Hinglish tax",
    what: "Measure char4_proxy vs gpt4o_cl100k inflation per code-mix bucket (low 0–0.2 via 19 synthetic English controls, mid, high). Results streamed live from /v1/eval/novel.",
    novel:
      "Makes the tokenizer inequality concrete and Hinglish-specific: high-mix inflates 1.54× vs 1.46× low-mix even with an offline byte proxy (literature reports up to 15× with real HF tokenizers Qwen/Llama/Gemma behind pip install .[tokenizers]).",
    fallback:
      "Offline proxy understates the effect — install tokenizers extras and re-run; the gap widens. The bucketing protocol is the contribution.",
  },
  {
    tag: "5",
    title: "Fail-closed protected-span guarantee + serving",
    what: "PII/code/amounts are masked to [[PSi]] before any compression and reinjected fail-closed — missing/duplicate marker → original returned. Single OpenAI-compatible gateway co-hosts all pillars.",
    novel:
      "Safety as a verified invariant: 100% span preservation (0 drops / 50) is checked in the evaluator, not assumed. The serving layer is deliberately not novel — it exists to put the research in front of real users.",
    fallback:
      "Already masked/reinjected offline; the guarantee holds even with the LLM compressor path (marker integrity checked before return).",
  },
];

function ResearchPage() {
  return (
    <Page
      eyebrow="Research"
      title="Five novelties — each live and measured, each training-free"
      lede="The project no longer 'just compresses Hinglish'. Four of the five novelties are already serving live from the gateway and visualized on /results — every claim below ships with a reproducibility path even if the GPU budget stays zero."
    >
      <div className="mb-8 flex flex-wrap gap-3">
        <Link to="/results" className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90">
          See the live proof — Results
        </Link>
        <Link to="/demo" className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium hover:bg-secondary">
          Try adaptive in the Demo
        </Link>
      </div>
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
