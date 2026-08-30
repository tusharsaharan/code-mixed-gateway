import { useEffect, useMemo, useState } from "react";
import { countTokensCl100k, countChar4Proxy, countWhitespace, estimateCostUsd, tokenChips } from "../../lib/tokenizer";
import { toDevanagariApprox, toEnglishGloss } from "../../lib/hinglish";
import { Card } from "../site/SiteChrome";

type Variant = { label: string; text: string; accent: string };

function useTokenStats(text: string) {
  const [tokens, setTokens] = useState<number | null>(null);
  const [chips, setChips] = useState<{ id: number; text: string; token: number }[]>([]);
  useEffect(() => {
    let cancelled = false;
    countTokensCl100k(text).then((n) => { if (!cancelled) setTokens(n); });
    tokenChips(text).then((c) => { if (!cancelled) setChips(c.slice(0, 48)); });
    return () => { cancelled = true; };
  }, [text]);
  const ws = useMemo(() => countWhitespace(text), [text]);
  const char4 = useMemo(() => countChar4Proxy(text), [text]);
  const cost = tokens != null ? estimateCostUsd(tokens) : 0;
  const tpc = tokens != null && text.length ? tokens / text.length : 0;
  return { tokens, ws, char4, cost, tpc, chips };
}

function CostBar({ tokens, max }: { tokens: number | null; max: number }) {
  const pct = tokens != null ? Math.min(100, (tokens / max) * 100) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
      <div className="h-2 rounded-full bg-primary transition-all duration-700 ease-out" style={{ width: `${pct}%` }} />
    </div>
  );
}

function VariantCard({ v, maxTokens }: { v: Variant; maxTokens: number }) {
  const { tokens, cost, tpc, chips } = useTokenStats(v.text);
  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-center justify-between">
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${v.accent}`}>{v.label}</span>
        <span className="font-mono text-xs text-muted-foreground">{tokens ?? "…"} tok · {tpc.toFixed(3)}/char</span>
      </div>
      <p className="mt-3 min-h-[48px] text-sm leading-relaxed">{v.text || "—"}</p>
      <div className="mt-3 flex flex-wrap gap-1">
        {chips.map((c) => (
          <span key={c.id} className="rounded bg-secondary px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground" title={`token ${c.token}`}>
            {c.text || "·"}
          </span>
        ))}
        {(tokens ?? 0) > 48 ? <span className="px-1 py-0.5 text-xs text-muted-foreground">+{(tokens ?? 0) - 48} more</span> : null}
      </div>
      <div className="mt-4 space-y-2">
        <CostBar tokens={tokens} max={maxTokens || 1} />
        <div className="flex justify-between font-mono text-xs">
          <span className="text-muted-foreground">${cost.toFixed(7)} @ gpt-4o $0.0025/1k</span>
          <span className="font-medium text-primary">{tokens ?? 0} tok</span>
        </div>
      </div>
    </Card>
  );
}

export function TokenizerVisualizer({ initialHinglish = "yaar mera hostel ka wifi slow hai, complaint kahan karun? kal assignment submit karna hai", compact = false }: { initialHinglish?: string; compact?: boolean }) {
  const [hinglish, setHinglish] = useState(initialHinglish);
  const english = useMemo(() => toEnglishGloss(hinglish), [hinglish]);
  const devanagari = useMemo(() => toDevanagariApprox(hinglish), [hinglish]);
  const variants: Variant[] = useMemo(() => [
    { label: "English", text: english, accent: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-100" },
    { label: "Hinglish (roman)", text: hinglish, accent: "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-100" },
    { label: "Devanagari Hindi", text: devanagari, accent: "bg-violet-100 text-violet-900 dark:bg-violet-900/30 dark:text-violet-100" },
  ], [english, hinglish, devanagari]);

  // Compute max tokens for bar scale
  const [maxTok, setMaxTok] = useState(40);
  useEffect(() => {
    Promise.all(variants.map((v) => countTokensCl100k(v.text))).then((ns) => setMaxTok(Math.max(20, ...ns, 1)));
  }, [variants]);

  const presets = [
    "yaar mera hostel ka wifi slow hai, complaint kahan karun?",
    "bhai ye maths ka sawal solve karo 15*8+22 ka answer batao jaldi",
    "mera phone charge nahi ho raha hai, charger bhi change kar liya",
  ];

  return (
    <div className={compact ? "" : "space-y-6"}>
      <div>
        {!compact ? <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Live tokenizer-fairness visualizer</p> : null}
        {!compact ? <h3 className="mt-1 text-xl">Type Hinglish → see 3 tokenizations side by side</h3> : null}
        <textarea
          value={hinglish}
          onChange={(e) => setHinglish(e.target.value)}
          rows={compact ? 2 : 3}
          placeholder="Type a Hinglish sentence…"
          className="mt-3 w-full resize-y rounded-xl border border-input bg-background px-3.5 py-3 text-sm leading-relaxed outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15"
        />
        <div className="mt-2 flex flex-wrap gap-1.5">
          {presets.map((p) => (
            <button key={p} onClick={() => setHinglish(p)} className="rounded-full border border-border bg-secondary/60 px-2.5 py-1 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground">
              {p.slice(0, 28)}…
            </button>
          ))}
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {variants.map((v) => <VariantCard key={v.label} v={v} maxTokens={maxTok} />)}
      </div>
      {!compact ? (
        <p className="text-xs leading-relaxed text-muted-foreground">
          Counts via{" "}<code className="rounded bg-secondary px-1 py-0.5">js-tiktoken cl100k_base</code> (GPT-4o) entirely client-side + cost at{" "}<code className="rounded bg-secondary px-1 py-0.5">pricing.py 2026-08-28</code>. Devanagari is an approximate transliteration for visual proof — backend MuRIL/HF tokenizers give the full Indic truth (see{" "}<a href="/tokenizer" className="font-medium text-primary hover:underline">/tokenizer</a>).
        </p>
      ) : null}
    </div>
  );
}
