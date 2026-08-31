import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Card, Page, SectionHeading } from "../components/site/SiteChrome";
import { GATEWAY_URL } from "../lib/gateway";

export const Route = createFileRoute("/connect")({
  head: () => ({
    meta: [
      { title: "Connect MCP Gateway — Code-Mixed LLM Gateway" },
      {
        name: "description",
        content:
          "Connect the Code-Mixed Gateway as a Model Context Protocol (MCP) tool into Claude Desktop, Cursor, Continue.dev or aider.",
      },
      { property: "og:title", content: "Connect MCP Gateway — Code-Mixed LLM Gateway" },
    ],
  }),
  component: ConnectPage,
});

const MCP_TOOLS = [
  {
    name: "healthz",
    desc: "Gateway health check, active threshold τ, and dry_run operational status.",
    schema: "{}",
  },
  {
    name: "compress",
    desc: "Compress Hinglish text using heuristic, distilled, adaptive, or auto modes with protected span preservation.",
    schema: '{"text": string, "method"?: "heuristic"|"distilled"|"adaptive"|"auto"}',
  },
  {
    name: "chat",
    desc: "Full cascade execution: compress prompt, score difficulty, conformal route, and return completion.",
    schema: '{"text": string}',
  },
  {
    name: "reasoning_budget",
    desc: "Estimate required reasoning tokens for Hinglish queries vs English gloss.",
    schema: '{"text": string}',
  },
  {
    name: "compare_budgets",
    desc: "Direct side-by-side comparison of reasoning token demand for Hinglish vs English equivalents.",
    schema: '{"hinglish": string, "english": string}',
  },
  {
    name: "tokenizer_report",
    desc: "Cross-tokenizer inflation report across GPT-4o, Llama 3.1, Qwen 2.5, Gemma 2, and MuRIL.",
    schema: "{}",
  },
  {
    name: "tokenizer_encode",
    desc: "Live tokenization with per-token visual chip segmentation and tier pricing.",
    schema: '{"text": string, "tokenizer"?: string}',
  },
  {
    name: "code_mix_interpolate",
    desc: "Interpolate 5 intermediate code-mixing stages between natural Hinglish and full English gloss.",
    schema: '{"text": string, "steps"?: number}',
  },
  {
    name: "novel_report",
    desc: "Comprehensive research summary: adaptive vs fixed compression, tokenizer tax, reasoning delta.",
    schema: "{}",
  },
  {
    name: "dashboard_stats",
    desc: "Real-time production metrics: routed query counts, token totals, and dollar savings.",
    schema: "{}",
  },
];

const CLAUDE_CONFIG = `{
  "mcpServers": {
    "code-mixed-gateway": {
      "command": "python",
      "args": ["-m", "gateway.mcp"],
      "cwd": "/path/to/code-mixed-gateway/backend",
      "env": {
        "GATEWAY_DRY_RUN": "true"
      }
    }
  }
}`;

const MCP_JSON = `{
  "mcpServers": {
    "code-mixed-gateway": {
      "command": "uv",
      "args": ["run", "python", "-m", "gateway.mcp"]
    }
  }
}`;

function ConnectPage() {
  const [copiedClaude, setCopiedClaude] = useState(false);
  const [copiedMcp, setCopiedMcp] = useState(false);

  const copyClaude = () => {
    navigator.clipboard.writeText(CLAUDE_CONFIG);
    setCopiedClaude(true);
    setTimeout(() => setCopiedClaude(false), 2000);
  };

  const copyMcp = () => {
    navigator.clipboard.writeText(MCP_JSON);
    setCopiedMcp(true);
    setTimeout(() => setCopiedMcp(false), 2000);
  };

  return (
    <Page
      eyebrow="Developer Surface"
      title="Connect the gateway as a tool"
      lede="Integrate the Code-Mixed Gateway directly into your local development workflows, agent runtimes, and IDEs via standard Model Context Protocol (MCP 2024-11-05)."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Quick Connect Configurations */}
        <Card>
          <SectionHeading kicker="Setup" title="Claude Desktop configuration" />
          <p className="text-sm leading-relaxed text-muted-foreground">
            Add the gateway to your{" "}
            <code className="rounded bg-secondary px-1 py-0.5">claude_desktop_config.json</code> to
            give Claude direct access to Hinglish compression and conformal routing tools:
          </p>
          <div className="relative mt-3">
            <pre className="overflow-x-auto rounded-xl border border-border bg-secondary/50 p-3.5 font-mono text-xs text-foreground leading-relaxed">
              {CLAUDE_CONFIG}
            </pre>
            <button
              type="button"
              onClick={copyClaude}
              className="absolute right-2.5 top-2.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              {copiedClaude ? "✓ Copied" : "Copy"}
            </button>
          </div>

          <div className="mt-6 border-t border-border pt-4">
            <SectionHeading kicker="IDE Integration" title="Cursor & Continue.dev (mcp.json)" />
            <div className="relative mt-2">
              <pre className="overflow-x-auto rounded-xl border border-border bg-secondary/50 p-3.5 font-mono text-xs text-foreground leading-relaxed">
                {MCP_JSON}
              </pre>
              <button
                type="button"
                onClick={copyMcp}
                className="absolute right-2.5 top-2.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground"
              >
                {copiedMcp ? "✓ Copied" : "Copy"}
              </button>
            </div>
          </div>
        </Card>

        {/* Server Runtime & Architecture */}
        <Card>
          <SectionHeading kicker="Execution" title="Running the stdio server" />
          <p className="text-sm leading-relaxed text-muted-foreground">
            The MCP server runs over standard I/O (
            <code className="rounded bg-secondary px-1 py-0.5">stdio</code>) with zero mandatory
            cloud dependencies.
          </p>
          <div className="mt-4 rounded-xl border border-border bg-secondary/40 p-4 space-y-3 font-mono text-xs">
            <div>
              <p className="text-muted-foreground text-[11px] uppercase tracking-wider">
                # Step 1: Install & run
              </p>
              <p className="text-foreground font-semibold">cd backend && python -m gateway.mcp</p>
            </div>
            <div>
              <p className="text-muted-foreground text-[11px] uppercase tracking-wider">
                # Step 2: Test via stdin JSON-RPC
              </p>
              <p className="text-foreground">{`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`}</p>
            </div>
          </div>

          <div className="mt-6 space-y-3 text-xs leading-relaxed text-muted-foreground">
            <div className="rounded-xl border border-primary/20 bg-primary/[0.04] p-3.5">
              <p className="font-medium text-foreground">Honest Protocol Implementation:</p>
              <p className="mt-1">
                When the optional <code className="font-mono text-primary">mcp</code> package is
                installed, the server uses the official Anthropic SDK server protocol. If{" "}
                <code className="font-mono">mcp</code> is absent, it seamlessly falls back to a
                clean internal stdio JSON-RPC loop without crashing.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-3.5">
              <p className="font-medium text-foreground">REST & OpenAI API Alternative:</p>
              <p className="mt-1">
                Prefer HTTP? Point any OpenAI SDK or Continue.dev client directly to{" "}
                <code className="font-mono text-foreground">
                  {GATEWAY_URL || "http://127.0.0.1:8000"}/v1
                </code>
                .
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Exposed 10 MCP Tools Grid */}
      <div className="mt-10">
        <SectionHeading kicker="Tools catalog" title="10 Available MCP Tools" />
        <p className="text-sm text-muted-foreground -mt-2 mb-6">
          Every tool exposed by <code className="font-mono">gateway.mcp</code> with exact parameter
          signatures:
        </p>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {MCP_TOOLS.map((t) => (
            <Card key={t.name} className="flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm font-semibold text-primary">{t.name}</span>
                  <span className="rounded bg-secondary px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                    mcp-tool
                  </span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{t.desc}</p>
              </div>
              <div className="mt-4 pt-3 border-t border-border">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                  Input Schema:
                </p>
                <code className="block font-mono text-[11px] text-foreground bg-secondary/50 p-2 rounded-lg break-all">
                  {t.schema}
                </code>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </Page>
  );
}
