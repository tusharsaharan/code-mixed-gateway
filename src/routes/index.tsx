import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, SectionHeading } from "../components/site/SiteChrome";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Code-Mixed LLM Gateway — Compression & Calibrated Routing" },
      {
        name: "description",
        content:
          "An open, reward-optimized compression and conformally-calibrated routing gateway built and measured on real Hindi–English code-mixed text.",
      },
      {
        property: "og:title",
        content: "Code-Mixed LLM Gateway — Compression & Calibrated Routing",
      },
      {
        property: "og:description",
        content:
          "Published LLM compression numbers are benchmarked on clean English. We test, train and deploy for code-mixed text instead.",
      },
    ],
  }),
  component: Index,
});

const TARGETS = [
  {
    value: "≥15×",
    label: "Compression target",
    note: "on code-mixed text at ≤5–8% task-accuracy loss",
  },
  {
    value: "Provable",
    label: "Accuracy bound",
    note: "distribution-free conformal risk control, not a tuned threshold",
  },
  {
    value: "≥40%",
    label: "Cost reduction",
    note: "on live pilot traffic vs. an always-large-model baseline",
  },
];

const PILLARS = [
  {
    tag: "A",
    title: "Reward-trained compressor",
    body: "A small compressor optimized against actual downstream task correctness on code-mixed text — not proxy perplexity.",
  },
  {
    tag: "B",
    title: "Conformally-calibrated router",
    body: "Escalation wrapped in conformal risk control, giving a finite-sample guarantee on cascade accuracy.",
  },
  {
    tag: "C",
    title: "Reasoning-budget controller",
    body: "Predicting thinking-token budget per query — and asking whether Hinglish needs a different budget than English.",
  },
  {
    tag: "D",
    title: "Serving infrastructure",
    body: "Prefix caching and speculative decoding behind one OpenAI-compatible gateway endpoint.",
  },
];

function Index() {
  return (
    <main>
      <section className="paper-grid border-b border-border/70">
        <div className="mx-auto max-w-6xl px-5 py-20 sm:py-28">
          <p className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs uppercase tracking-[0.16em] text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            Undergraduate research project · 12 weeks
          </p>
          <h1 className="mt-6 max-w-4xl text-[2.6rem] leading-[1.05] sm:text-6xl">
            LLM cost research stops at clean English.{" "}
            <span className="italic text-primary">Real conversations don&apos;t.</span>
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            We are building the first open, reward-optimized prompt-compression and
            conformally-calibrated routing gateway for Hindi–English code-mixed text — the actual
            language of Indian customer support, WhatsApp business chat and campus life — and
            deploying it to people who genuinely speak that way.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              to="/research"
              className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Read the research plan
            </Link>
            <Link
              to="/benchmark"
              className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium transition-colors hover:bg-secondary"
            >
              The open benchmark
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16">
        <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
          <Card>
            <SectionHeading kicker="The gap" title="Nobody has measured this" />
            <div className="space-y-4 text-sm leading-relaxed text-muted-foreground">
              <p>
                Published compression and routing results are benchmarked almost entirely on clean
                English corpora — GSM8K, MeetingBank, ShareGPT. Whether those savings survive
                code-switching, transliteration and informal spelling has never been rigorously
                tested.
              </p>
              <p>
                Tokenizer-fairness work reports that the same content can cost{" "}
                <strong className="text-foreground">up to 15× more tokens</strong> depending on the
                language it is written in. If that holds for code-mixed text, millions of real
                conversations are quietly expensive in a way no benchmark currently captures.
              </p>
              <p>
                That is the gap this project takes: measure it honestly, then build a system that
                closes it.
              </p>
            </div>
          </Card>

          <Card className="bg-secondary/40">
            <SectionHeading kicker="Scope" title="Study → built system" />
            <ul className="space-y-4 text-sm leading-relaxed text-muted-foreground">
              <li>
                <span className="font-medium text-foreground">From</span> an evaluation study of
                existing compression libraries on new text.
              </li>
              <li>
                <span className="font-medium text-foreground">To</span> a trained compressor, a
                calibrated router, a released benchmark and a live pilot with real users.
              </li>
              <li className="rounded-xl border border-border bg-card p-4">
                <span className="font-medium text-foreground">First action:</span> a two-line scope
                update to the supervising professor, on record in week 1 — plus a lightweight
                consent/ethics check before any user query is logged.
              </li>
            </ul>
          </Card>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 pb-4">
        <SectionHeading kicker="Targets, not results" title="What success looks like" />
        <div className="grid gap-5 sm:grid-cols-3">
          {TARGETS.map((t) => (
            <Card key={t.label}>
              <p className="font-serif text-4xl text-primary">{t.value}</p>
              <p className="mt-2 text-sm font-medium">{t.label}</p>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{t.note}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16">
        <SectionHeading kicker="Four pillars" title="The actual work" />
        <div className="grid gap-5 sm:grid-cols-2">
          {PILLARS.map((p) => (
            <Card key={p.tag}>
              <div className="flex items-start gap-4">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent font-serif text-lg text-accent-foreground">
                  {p.tag}
                </span>
                <div>
                  <h3 className="text-xl">{p.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
        <Link
          to="/research"
          className="mt-6 inline-block text-sm font-medium text-primary hover:underline"
        >
          Full pillar breakdown, including training-free fallbacks →
        </Link>
      </section>
    </main>
  );
}
