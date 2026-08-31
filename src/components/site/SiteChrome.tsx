import { Link, useMatchRoute } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState, type ReactNode } from "react";
import { GATEWAY_URL } from "../../lib/gateway";

const NAV = [
  { to: "/", label: "Overview", exact: true },
  { to: "/demo", label: "Demo" },
  { to: "/redteam", label: "Red Team" },
  { to: "/tokenizer", label: "Tokenizer" },
  { to: "/results", label: "Results" },
  { to: "/research", label: "Research" },
  { to: "/benchmark", label: "Benchmark" },
  { to: "/roadmap", label: "Roadmap" },
  { to: "/team", label: "Team & Compute" },
  { to: "/pilot", label: "Pilot" },
  { to: "/connect", label: "Connect" },
] as const;

function NavItem({ to, label, exact }: { to: string; label: string; exact?: boolean }) {
  const matchRoute = useMatchRoute();
  // TanStack Router's matchRoute uses `fuzzy`; exact ↔ fuzzy:false
  const isActive = Boolean(
    (matchRoute as unknown as (opts: unknown) => boolean)({
      to,
      fuzzy: !(exact ?? to === "/"),
    } as unknown),
  );
  return (
    <Link
      to={to}
      className="relative rounded-md px-2.5 py-2 text-[13px] transition-colors hover:text-foreground"
    >
      <span className={`relative z-10 ${isActive ? "text-foreground" : "text-muted-foreground"}`}>
        {label}
      </span>
      {isActive ? (
        <motion.span
          layoutId="nav-pill"
          className="absolute inset-0 -z-0 rounded-md bg-secondary"
          transition={{ type: "spring", stiffness: 380, damping: 32 }}
        />
      ) : null}
    </Link>
  );
}

function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const saved = localStorage.getItem("theme") === "dark";
    setDark(saved);
    document.documentElement.classList.toggle("dark", saved);
  }, []);
  return (
    <button
      type="button"
      aria-label="Toggle theme"
      onClick={() => {
        const next = !dark;
        setDark(next);
        document.documentElement.classList.toggle("dark", next);
        localStorage.setItem("theme", next ? "dark" : "light");
      }}
      className="rounded-md border border-border bg-card px-2.5 py-2 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground"
    >
      {dark ? "☀︎" : "☾"}
    </button>
  );
}

function HealthDot() {
  const [ok, setOk] = useState<boolean | null>(null);
  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const check = () => {
      fetch(`${GATEWAY_URL}/healthz`, { signal: controller.signal })
        .then((r) => {
          if (!cancelled) setOk(r.ok);
        })
        .catch(() => {
          if (!cancelled) setOk(false);
        });
    };
    check();
    const id = setInterval(check, 30000);
    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(id);
    };
  }, []);
  return (
    <span
      title={
        ok == null
          ? "checking gateway"
          : ok
            ? "gateway reachable"
            : "gateway unreachable (dry-run fallback)"
      }
      className={`h-2 w-2 rounded-full ${ok == null ? "bg-amber-400 animate-pulse" : ok ? "bg-emerald-500" : "bg-red-500"}`}
      aria-hidden
    />
  );
}

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <motion.header
      initial={{ y: -16, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-md"
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-5 py-4">
        <Link to="/" className="flex items-center gap-2.5" onClick={() => setOpen(false)}>
          <motion.span
            whileHover={{ rotate: -8, scale: 1.06 }}
            transition={{ type: "spring", stiffness: 320, damping: 18 }}
            className="grid h-8 w-8 place-items-center rounded-lg bg-primary/12 font-serif text-base text-primary"
          >
            ⌘
          </motion.span>
          <span className="leading-tight">
            <span className="block font-serif text-lg">Code-Mixed Gateway</span>
            <span className="block text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              Compression · Routing · Research
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-0.5 md:flex">
          {NAV.map((item) => {
            const ex = (item as { exact?: boolean }).exact;
            return ex !== undefined ? (
              <NavItem key={item.to} to={item.to} label={item.label} exact={ex} />
            ) : (
              <NavItem key={item.to} to={item.to} label={item.label} />
            );
          })}
          <div className="ml-2 flex items-center gap-1.5">
            <HealthDot />
            <ThemeToggle />
            <motion.a
              whileHover={{ y: -1 }}
              href={`${GATEWAY_URL}/dashboard`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-md border border-border bg-card px-2.5 py-2 text-[13px] text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
            >
              Dashboard
              <span aria-hidden className="text-[10px]">
                ↗
              </span>
            </motion.a>
          </div>
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

      <AnimatePresence initial={false}>
        {open ? (
          <motion.nav
            key="mobile-nav"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden border-t border-border/70 md:hidden"
          >
            <div className="space-y-1 px-5 py-3">
              {NAV.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={() => setOpen(false)}
                  className="block rounded-md px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                >
                  {item.label}
                </Link>
              ))}
              <a
                href={`${GATEWAY_URL}/dashboard`}
                target="_blank"
                rel="noreferrer"
                className="block rounded-md px-3 py-2.5 text-sm text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                Dashboard ↗
              </a>
            </div>
          </motion.nav>
        ) : null}
      </AnimatePresence>
    </motion.header>
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
              <li>
                <Link to="/team" className="text-muted-foreground hover:text-foreground">
                  Team & compute
                </Link>
              </li>
              <li>
                <Link to="/pilot" className="text-muted-foreground hover:text-foreground">
                  Live pilot
                </Link>
              </li>
              <li>
                <Link to="/demo" className="text-muted-foreground hover:text-foreground">
                  Live demo
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
      <motion.p
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-xs uppercase tracking-[0.18em] text-primary"
      >
        {eyebrow}
      </motion.p>
      <motion.h1
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
        className="mt-3 max-w-3xl text-4xl leading-[1.1] sm:text-5xl"
      >
        {title}
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.12, ease: [0.22, 1, 0.36, 1] }}
        className="mt-5 max-w-2xl text-lg leading-relaxed text-muted-foreground"
      >
        {lede}
      </motion.p>
      <div className="mt-12">{children}</div>
    </main>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      whileHover={{ y: -3 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      className={`rounded-2xl border border-border bg-card p-6 shadow-[var(--shadow-soft)] transition-shadow duration-300 hover:shadow-[0_2px_4px_oklch(0.35_0.03_80/6%),0_24px_48px_oklch(0.35_0.03_80/10%)] ${className}`}
    >
      {children}
    </motion.div>
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

export function DataTable({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
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
