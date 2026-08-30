import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, SectionHeading } from "../components/site/SiteChrome";
import { TokenizerVisualizer } from "../components/tokenizer/TokenizerVisualizer";
import { LiveTicker, SavingsCounter } from "../components/site/LiveTicker";

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
    value: "35%",
    label: "Adaptive savings",
    note: "tokens saved vs 1.3% fixed heuristic — same span safety, measured now",
    href: "/results" as const,
  },
  {
    value: "+56",
    label: "Hinglish thinking tax",
    note: "extra reasoning tokens Hinglish needs over English (n=50, live)",
    href: "/results" as const,
  },
  {
    value: "Provable",
    label: "Accuracy bound",
    note: "distribution-free conformal bound on both routing and compression",
    href: "/results" as const,
  },
];

const PILLARS = [
  {
    tag: "1",
    title: "Adaptive code-mix-aware compression",
    body: "First compressor that conditions aggressiveness on Hindi–English mix + difficulty: 35% savings vs 1.3% fixed, at a bounded reward cost. The policy is the contribution.",
  },
  {
    tag: "2",
    title: "Conformal fidelity for compression",
    body: "Not just routing — we conformal-certify the compressor itself (reward ≥0.85) with a 95% Hoeffding LTT bound. No prior code-mixed work does this.",
  },
  {
    tag: "3",
    title: "Hinglish reasoning tax",
    body: "First measurement: Hinglish needs +56 reasoning tokens on average (88% of pairs, n=50) versus English equivalents — a publishable side-finding.",
  },
  {
    tag: "4",
    title: "Tokenizer fairness on code-mix",
    body: "Bucketed inflation (low/mid/high mix) shows the Hinglish tax explicitly — high-mix inflates 1.54× vs 1.46× low-mix even with an offline proxy (15× in literature).",
  },
];

function Index() {
  return (
    <main>
      <LiveTicker />
      <section className="paper-grid border-b border-border/70">
        <div className="mx-auto max-w-6xl px-5 py-14 sm:py-20">
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
              to="/tokenizer"
              className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
            >
              Play with the tokenizer — 3-way live
            </Link>
            <Link
              to="/results"
              className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium transition-colors hover:bg-secondary"
            >
              See that it works — live results
            </Link>
            <Link
              to="/demo"
              className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium transition-colors hover:bg-secondary"
            >
              Try the live gateway
            </Link>
          </div>
          <div className="mt-8 grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
            <SavingsCounter />
            <Card className="flex items-center justify-between bg-secondary/30">
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">One-sentence demo</p>
                <p className="mt-1 text-sm leading-relaxed">Drag the slider on the tokenizer page and watch cost move — that’s the research.</p>
              </div>
              <Link to="/tokenizer" className="shrink-0 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">Open →</Link>
            </Card>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-14">
        <SectionHeading kicker="Try it now — no backend required" title="Type Hinglish → see 3 tokenizations, 3 costs, live" />
        <Card>
          <TokenizerVisualizer compact={false} />
        </Card>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link to="/tokenizer" className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium hover:bg-secondary">Open full playground with slider →</Link>
          <Link to="/demo" className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium hover:bg-secondary">Run it through the gateway →</Link>
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
        <SectionHeading kicker="Live results, not targets" title="What we actually measured" />
        <div className="grid gap-5 sm:grid-cols-3">
          {TARGETS.map((t) => (
            <Link key={t.label} to={t.href} className="block">
              <Card className="h-full hover:border-primary/30">
                <p className="font-serif text-4xl text-primary">{t.value}</p>
                <p className="mt-2 text-sm font-medium">{t.label}</p>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{t.note}</p>
                <span className="mt-3 inline-block text-xs font-medium text-primary">See live chart →</span>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16">
        <SectionHeading kicker="Five novelties" title="What makes this more than ' Hinglish + compression '" />
        <div className="grid gap-5 sm:grid-cols-2">
          {PILLARS.map((p) => (
            <Card key={p.tag} className="hover:border-primary/20">
              <div className="flex items-start gap-4">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-primary font-serif text-lg text-primary-foreground">
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
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/results" className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90">
            See the proof — live results
          </Link>
          <Link to="/research" className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium hover:bg-secondary">
            Full pillar breakdown →
          </Link>
        </div>
      </section>
    </main>
  );
}
