# Code-Mixed LLM Gateway — Project Website

A professional, soft-toned marketing + research site for the code-mixed (Hinglish) compression + calibrated-routing gateway project. Content-first, no backend, no live model calls — it presents the research direction, the four pillars, benchmark targets, timeline, team split, and compute stack in a form you can send to a professor or link from GitHub/HF.

## Visual direction

Soft, academic-modern: warm off-white paper background, deep ink text, one muted accent (soft teal) plus a warm sand secondary. Generous whitespace, rounded cards, hairline borders, very subtle shadows. No purple gradients, no dark hero. Typography: a refined serif for headings (Instrument Serif / Lora feel) paired with a clean grotesque for body — signals "research" without looking like a template SaaS page.

## Pages (separate routes, each with its own SEO metadata)

- `/` — Home: hero with the one-line thesis, the gap statement (published compression numbers are benchmarked on clean English; code-mixed text is untested), three headline target metrics, and links onward.
- `/research` — The four pillars (A reward-trained compressor, B conformally-calibrated cascade router, C reasoning-budget controller, D serving infrastructure), each as a card with what it is, why it's novel, and the training-free fallback path.
- `/benchmark` — The open code-mixed cost/quality benchmark: what it contains, how it's graded, the ₹/$ cost conversion angle, planned Hugging Face release, and the "even if experiments slip, the dataset stands alone" framing.
- `/roadmap` — The 12-week timeline as a readable vertical milestone list, plus the "what impressive looks like" targets and the risk/fallback notes.
- `/team` — 80/10/10 split table (Research Lead, Data & Eval Lead, Platform Lead) with ownership and rationale, plus the compute-tier table (Kaggle, Colab, HF ZeroGPU, Lightning AI, RunPod/Vast, Groq/Cerebras, department cluster).
- `/pilot` — Where the audience lives: WhatsApp/Telegram bot, OpenAI-compatible endpoint for classmates, HF Space demo, community posts — plus a clear, visible data-handling and consent note (anonymized queries, no identifying data).

Shared header with the six links and a footer carrying the honesty disclaimer (which numbers are measured vs. illustrative/reference) and repo/dataset placeholder links.

## Technical notes

- TanStack Start file routes under `src/routes/`; `src/routes/index.tsx` is rewritten as the home page.
- Design tokens (colors, radii, fonts) defined in `src/styles.css`; components use semantic tokens only — no hardcoded color utilities.
- Fonts loaded via a `<link>` in `src/routes/__root.tsx`; shared header/footer live there around `<Outlet />`.
- Small shared presentation components (`SectionHeading`, `PillarCard`, `MetricStat`, `DataTable`) under `src/components/`.
- Each leaf route defines its own `head()` with unique title/description/og tags; root metadata replaced (no "Lovable App").
- Fully responsive; content is static, so no data fetching or Cloud backend.

## Not included (say the word and I'll add later)

Live model calls, the interactive gateway demo, dashboards, auth, or any backend.
