import { Link } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";

const NAV = [
  { to: "/", label: "Overview" },
  { to: "/research", label: "Research" },
  { to: "/benchmark", label: "Benchmark" },
  { to: "/roadmap", label: "Roadmap" },
  { to: "/team", label: "Team & Compute" },
  { to: "/pilot", label: "Pilot" },
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-5 py-4">
        <Link to="/" className="flex items-center gap-2.5" onClick={() => setOpen(false)}>
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary/12 font-serif text-base text-primary">
            ⌘
          </span>
          <span className="leading-tight">
            <span className="block font-serif text-lg">Code-Mixed Gateway</span>
            <span className="block text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              Compression · Routing · Research
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              activeOptions={{ exact: item.to === "/" }}
              className="rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              activeProps={{ className: "bg-secondary text-foreground" }}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <button
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="rounded-md border border-border px-3 py-2 text-sm md:hidden"
        >
          Menu
        </button>
      </div>

      {open ? (
        <nav className="border-t border-border/70 px-5 pb-4 md:hidden">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setOpen(false)}
              className="block rounded-md px-3 py-2.5 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground"
              activeProps={{ className: "bg-secondary text-foreground" }}
              activeOptions={{ exact: item.to === "/" }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-border/70 bg-secondary/35">
      <div className="mx-auto max-w-6xl px-5 py-12">
        <div className="grid gap-8 md:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <h3 className="text-xl">Code-Mixed LLM Gateway</h3>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
              An open compression, calibrated-routing and reasoning-budget gateway built and
              evaluated on real Hindi–English code-mixed traffic.
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Project</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link to="/research" className="text-muted-foreground hover:text-foreground">
                  Research pillars
                </Link>
              </li>
              <li>
                <Link to="/benchmark" className="text-muted-foreground hover:text-foreground">
                  Benchmark
                </Link>
              </li>
              <li>
                <Link to="/roadmap" className="text-muted-foreground hover:text-foreground">
                  12-week roadmap
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Releases</p>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              <li>GitHub repository — coming week 1</li>
              <li>Hugging Face dataset — coming week 4</li>
              <li>Public demo Space — coming week 9</li>
            </ul>
          </div>
        </div>

        <p className="mt-10 border-t border-border/70 pt-6 text-xs leading-relaxed text-muted-foreground">
          Honesty note: every figure on this site is either a stated <em>target</em>, a{" "}
          <em>reference number from published work</em>, or a <em>planned</em> deliverable. Nothing
          here is presented as a measured result of this project yet. Measured results will be
          labelled as such, with the evaluation setup and pricing date attached, once the benchmark
          and pilot produce them.
        </p>
      </div>
    </footer>
  );
}

export function Page({
  eyebrow,
  title,
  lede,
  children,
}: {
  eyebrow: string;
  title: string;
  lede: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto max-w-6xl px-5 pt-14">
      <p className="text-xs uppercase tracking-[0.18em] text-primary">{eyebrow}</p>
      <h1 className="mt-3 max-w-3xl text-4xl leading-[1.1] sm:text-5xl">{title}</h1>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted-foreground">{lede}</p>
      <div className="mt-12">{children}</div>
    </main>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-border bg-card p-6 shadow-[var(--shadow-soft)] ${className}`}
    >
      {children}
    </div>
  );
}

export function SectionHeading({ kicker, title }: { kicker?: string; title: string }) {
  return (
    <div className="mb-6">
      {kicker ? (
        <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{kicker}</p>
      ) : null}
      <h2 className="mt-1.5 text-2xl sm:text-3xl">{title}</h2>
    </div>
  );
}

export function DataTable({
  head,
  rows,
}: {
  head: string[];
  rows: ReactNode[][];
}) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-border bg-card shadow-[var(--shadow-soft)]">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="bg-secondary/60">
            {head.map((h) => (
              <th
                key={h}
                className="border-b border-border px-5 py-3 text-left text-xs font-medium uppercase tracking-[0.1em] text-muted-foreground"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="align-top">
              {row.map((cell, j) => (
                <td
                  key={j}
                  className={`border-b border-border/70 px-5 py-4 ${
                    j === 0 ? "font-medium text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
