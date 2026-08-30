import { createFileRoute, Link } from "@tanstack/react-router";
import { Page, SectionHeading, Card } from "../components/site/SiteChrome";
import { TokenizerVisualizer } from "../components/tokenizer/TokenizerVisualizer";
import { CodeSwitchSlider } from "../components/tokenizer/CodeSwitchSlider";

export const Route = createFileRoute("/tokenizer")({
  head: () => ({
    meta: [
      { title: "Tokenizer Fairness — Hinglish Cost Playground" },
      {
        name: "description",
        content:
          "Type one Hinglish sentence and see English / Hinglish / Devanagari tokenize side-by-side with real GPT-style counts and cost bars.",
      },
    ],
  }),
  component: TokenizerPage,
});

function TokenizerPage() {
  return (
    <Page
      eyebrow="Hinglish / Code-mixed"
      title="Tokenizer fairness, live — the finding that motivates the whole project"
      lede="Published cost numbers are on clean English. Type one Hinglish sentence and watch the same idea cost differently across English, roman Hinglish and Devanagari — with real js-tiktoken counts, cost bars and an interpolating slider that turns mix into a research figure."
    >
      <Card className="border-primary/20 bg-primary/[0.03]">
        <p className="text-sm leading-relaxed text-muted-foreground">
          <strong className="text-foreground">What this proves:</strong> tokenizers can report{" "}
          <strong className="text-foreground">up to 15×</strong> more tokens for the same content
          across languages (Petrov et al.). Our bucketed offline proxy already shows high-mix 1.54×
          vs low-mix 1.46× even without HF tokenizers — the visualizer makes the direction
          undeniable. Backend MuRIL/Qwen/Gemma behind{" "}
          <code className="rounded bg-secondary px-1 py-0.5">pip install .[tokenizers]</code> widens
          the gap.
        </p>
      </Card>

      <div className="mt-10">
        <SectionHeading
          kicker="Visualizer"
          title="Live 3-way tokenization — English / Hinglish / Devanagari"
        />
        <Card>
          <TokenizerVisualizer />
        </Card>
      </div>

      <div className="mt-14">
        <SectionHeading
          kicker="Slider"
          title="Code-switch interpolation — a research figure you can drag"
        />
        <Card>
          <CodeSwitchSlider />
        </Card>
        <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
          Slider is deterministic via{" "}
          <code className="rounded bg-secondary px-1 py-0.5">m12_novel/gloss.py</code> word map — no
          model call, fully reproducible for the paper. Try the demo-picked sentence first, then
          your own.
        </p>
      </div>

      <div className="mt-14 flex flex-wrap gap-3">
        <Link
          to="/results"
          className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          See the full live results →
        </Link>
        <Link
          to="/demo"
          className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium hover:bg-secondary"
        >
          Try adaptive in the Demo
        </Link>
      </div>
    </Page>
  );
}
