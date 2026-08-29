import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, DataTable, Page, SectionHeading } from "../components/site/SiteChrome";
import { GATEWAY_URL } from "../lib/gateway";

export const Route = createFileRoute("/fairness")({
  head: () => ({
    meta: [
      { title: "Tokenizer Fairness — Code-Mixed Gateway" },
      {
        name: "description",
        content:
          "Petrov-style tokenizer fairness: Hinglish token inflation vs. English baseline across tokenizers.",
      },
    ],
  }),
  component: FairnessPage,
});

type Report = {
  n_records: number;
  inflation_vs_gpt4o: Record<string, number>;
  sample_rows: {
    id: string;
    tokenizer: string;
    num_tokens: number;
    chars: number;
    tokens_per_char: number;
  }[];
  pricing_date: string;
};

function FairnessPage() {
  const [data, setData] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${GATEWAY_URL}/v1/tokenizer/report`)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<Report>;
      })
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const inflationChart = data
    ? Object.entries(data.inflation_vs_gpt4o).map(([k, v]) => ({ tokenizer: k, inflation: v }))
    : [];

  return (
    <Page
      eyebrow="Tokenizer"
      title="Tokenizer fairness for Hinglish"
      lede="The same content can cost up to 1.5× tokens depending on tokenizer and script. This page makes that visible — the Petrov observation that motivates the whole gateway."
    >
      {error && !data ? (
        <div className="mb-6 rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error} — is the gateway running? Check VITE_GATEWAY_URL.
        </div>
      ) : null}
      {error && !data ? null : !data ? (
        <p className="text-sm text-muted-foreground">Loading tokenizer report…</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Records sampled
              </p>
              <p className="mt-1.5 font-serif text-2xl text-primary">{data.n_records}</p>
            </Card>
            <Card>
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Pricing date
              </p>
              <p className="mt-1.5 font-serif text-2xl text-primary">{data.pricing_date}</p>
            </Card>
            <Card>
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Max inflation
              </p>
              <p className="mt-1.5 font-serif text-2xl text-primary">
                {Object.values(data.inflation_vs_gpt4o).length
                  ? `${Math.max(...Object.values(data.inflation_vs_gpt4o)).toFixed(2)}×`
                  : "—"}
              </p>
            </Card>
          </div>

          <div className="mt-10">
            <SectionHeading kicker="Inflation" title="Tokens vs gpt4o baseline" />
            <Card>
              <div className="h-[280px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={inflationChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="tokenizer" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: 12,
                      }}
                    />
                    <Bar dataKey="inflation" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
                Baseline is <code className="rounded bg-secondary px-1 py-0.5">gpt4o_cl100k</code>{" "}
                (1.0). Values above 1.0 mean the tokenizer produces *more* tokens for the same
                Hinglish text — i.e. more expensive. Whitespace is a lower bound; `qwen2.5` and
                `char4_proxy` show the model-specific effect. Install HF tokenizers for
                `llama3.1`/`gemma2` to see true distributions.
              </p>
            </Card>
          </div>

          <div className="mt-10">
            <SectionHeading kicker="Sample" title="Per-tokenizer token counts (first 8 records)" />
            <DataTable
              head={["id", "tokenizer", "tokens", "chars", "t/c"]}
              rows={data.sample_rows
                .slice(0, 24)
                .map((r) => [
                  r.id,
                  r.tokenizer,
                  String(r.num_tokens),
                  String(r.chars),
                  r.tokens_per_char.toFixed(3),
                ])}
            />
          </div>
        </>
      )}
    </Page>
  );
}
