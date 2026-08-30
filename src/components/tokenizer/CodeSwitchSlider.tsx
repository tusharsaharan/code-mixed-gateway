import { useCallback, useEffect, useState } from "react";
import { Card } from "../site/SiteChrome";
import { fetchInterpolate, type InterpolateVariant } from "../../lib/gateway";
import { Slider } from "../ui/slider";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from "recharts";

export function CodeSwitchSlider({ initial = "yaar mera hostel ka wifi slow hai, complaint kahan karun? kal assignment submit karna hai" }: { initial?: string }) {
  const [text, setText] = useState(initial);
  const [variants, setVariants] = useState<InterpolateVariant[] | null>(null);
  const [level, setLevel] = useState(2); // 0..4
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async (t: string) => {
    setLoading(true); setErr(null);
    try {
      const r = await fetchInterpolate(t, 5);
      setVariants(r.variants);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setVariants(null);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(text); }, [text]); // eslint-disable-line react-hooks/exhaustive-deps
  // initial load only on mount + when text changes via explicit action to avoid spam

  const active = variants?.[level] ?? null;
  const chartData = variants?.map((v) => ({
    mix: `${Math.round(v.code_mix_ratio * 100)}%`,
    level: v.level,
    tokens: v.tokens,
    kept: +(v.heuristic_kept_ratio * 100).toFixed(1),
    target: +(v.adaptive_target * 100).toFixed(1),
    cost: v.cost_premium_usd * 1e6, // µ$
  })) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Code-switch slider — interpolate Hindi ↔ Hinglish ↔ English</p>
        <h3 className="mt-1 text-xl">Drag to watch compression + cost shift with the mix</h3>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={2}
          placeholder="Type a Hinglish sentence to interpolate…"
          className="mt-3 w-full rounded-xl border border-input bg-background px-3.5 py-3 text-sm outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/15"
        />
        <div className="mt-3 flex gap-2">
          <button onClick={() => load(text)} disabled={loading || !text.trim()} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50">
            {loading ? "Interpolating…" : "Re-interpolate"}
          </button>
          <span className="self-center text-xs text-muted-foreground">Nobody’s built this — slider + live backend mix.</span>
        </div>
        {err ? <p className="mt-2 text-sm text-destructive">{err}</p> : null}
      </div>

      {variants ? (
        <>
          <Card>
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Mix level</span>
              <span className="rounded-full bg-secondary px-2.5 py-1 font-mono text-xs">{active ? `${(active.level * 100).toFixed(0)}% English` : "—"}</span>
            </div>
            <div className="mt-4 px-1">
              <Slider value={[level]} min={0} max={4} step={1} onValueChange={([v]) => setLevel(v ?? 2)} />
              <div className="mt-2 flex justify-between font-mono text-[11px] text-muted-foreground">
                <span>Hinglish (0%)</span><span>50%</span><span>English (100%)</span>
              </div>
            </div>
            {active ? (
              <div className="mt-4 rounded-xl border border-border bg-secondary/30 p-4">
                <p className="font-mono text-sm leading-relaxed">{active.text}</p>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-full bg-card border border-border px-2.5 py-1">mix {(active.code_mix_ratio * 100).toFixed(0)}%</span>
                  <span className="rounded-full bg-card border border-border px-2.5 py-1">{active.tokens} tok</span>
                  <span className="rounded-full bg-card border border-border px-2.5 py-1">difficulty {active.difficulty.toFixed(3)}</span>
                  <span className="rounded-full bg-primary/10 px-2.5 py-1 font-medium text-primary">target {(active.adaptive_target * 100).toFixed(0)}% kept</span>
                </div>
                <p className="mt-3 text-xs leading-relaxed text-muted-foreground">Heuristic preview: <span className="font-mono text-foreground">{active.heuristic_compressed || "—"}</span></p>
              </div>
            ) : null}
          </Card>

          <Card>
            <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Compression + cost vs mix — research figure, live</p>
            <div className="mt-4 h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="mix" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12 }} />
                  <Legend />
                  <Line type="monotone" dataKey="target" name="Adaptive target kept%" stroke="hsl(var(--primary))" strokeWidth={2} dot />
                  <Line type="monotone" dataKey="kept" name="Heuristic kept%" stroke="hsl(var(--muted-foreground))" strokeDasharray="4 4" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 h-[160px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="mix" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 12 }} />
                  <Bar dataKey="tokens" name="Tokens" fill="hsl(var(--accent-foreground))" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">Adaptive keeps more when mix is high (conservative) and compresses English aggressively — the policy is the novelty. Backend <code className="rounded bg-secondary px-1 py-0.5">POST /v1/code_mix/interpolate</code>.</p>
          </Card>
        </>
      ) : (
        <Card className="bg-secondary/40"><p className="text-sm text-muted-foreground">Interpolate to see 5 variants.</p></Card>
      )}
    </div>
  );
}
