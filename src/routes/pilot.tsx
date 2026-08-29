import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";

export const Route = createFileRoute("/pilot")({
  head: () => ({
    meta: [
      { title: "Live Pilot — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "Where the gateway meets real users: a Telegram bot, an OpenAI-compatible endpoint, a public demo and a consent-first data policy.",
      },
      { property: "og:title", content: "Live Pilot — Code-Mixed LLM Gateway" },
    ],
  }),
  component: PilotPage,
});

const CHANNELS = [
  {
    title: "Telegram bot",
    body: "A free bot that answers real student questions in natural Hinglish, routed through the gateway, deployed in campus and course groups.",
  },
  {
    title: "OpenAI-compatible endpoint",
    body: "Classmates point Continue.dev, Cline or aider at it for coding help — real developer traffic and real savings data.",
  },
  {
    title: "Public demo + dashboard",
    body: "A Hugging Face Space with the live demo and dashboard, hosted free on ZeroGPU hardware.",
  },
  {
    title: "Community feedback",
    body: "Post to r/developersIndia or r/LocalLLaMA for outside critique — a community that cares about exactly this angle.",
  },
];

function PilotPage() {
  return (
    <Page
      eyebrow="Deployment"
      title="Where the gateway meets real users"
      lede="The pilot is not a demo — it is real traffic, and its single most convincing number is the count of real queries routed and answered in production."
    >
      <div className="grid gap-6 sm:grid-cols-2">
        {CHANNELS.map((c) => (
          <Card key={c.title}>
            <h3 className="text-xl">{c.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{c.body}</p>
          </Card>
        ))}
      </div>

      <div className="mt-12 flex flex-wrap gap-3">
        <Link
          to="/demo"
          className="rounded-lg bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          Try the live demo
        </Link>
        <Link
          to="/benchmark"
          className="rounded-lg border border-border bg-card px-5 py-3 text-sm font-medium transition-colors hover:bg-secondary"
        >
          See the benchmark it feeds
        </Link>
      </div>

      <div className="mt-14">
        <SectionHeading kicker="Ethics & consent" title="Data handling, decided up front" />
        <Card className="border-primary/30 bg-secondary/40">
          <ul className="space-y-3 text-sm leading-relaxed text-muted-foreground">
            <li>
              Users are told their anonymized queries may be used for the project, and nothing
              identifying is logged.
            </li>
            <li>
              Queries are anonymized at collection time — no usernames, phone numbers or group
              identifiers are retained.
            </li>
            <li>
              A lightweight consent / ethics sign-off is requested from the supervising institute in
              week 1, not discovered after data has been collected.
            </li>
          </ul>
        </Card>
      </div>
    </Page>
  );
}
