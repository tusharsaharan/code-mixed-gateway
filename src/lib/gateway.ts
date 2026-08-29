export const GATEWAY_URL: string =
  (import.meta.env as Record<string, string | undefined>)["VITE_GATEWAY_URL"] ?? "";

export interface GatewayMeta {
  original_tokens: number;
  compressed_tokens: number;
  compression_ratio: number;
  compressed_prompt: string;
  difficulty_score: number;
  conformal_threshold: number;
  tier: string;
  model_routed: string;
  estimated_cost_usd: number;
  estimated_cost_savings_usd: number;
  reasoning_budget: number;
  budget_delta_hinglish_en: number | null;
  error_bound: number;
  calibration_n: number;
}

export interface ChatResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: { index: number; message: { role: string; content: string }; finish_reason: string }[];
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
  x_gateway?: GatewayMeta;
}

export interface DashboardStats {
  queries: number;
  total_original_tokens: number;
  total_compressed_tokens: number;
  total_cost_savings_usd: number;
  total_cost_savings_inr: number;
  tier_split: Record<string, number>;
}

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = 10000,
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

export async function chatCompletion(message: string): Promise<ChatResponse> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: "cascade", messages: [{ role: "user", content: message }] }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Gateway ${res.status}: ${body}`);
  }
  return (await res.json()) as ChatResponse;
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/dashboard/stats`);
  if (!res.ok) throw new Error(`Gateway ${res.status}: ${await res.text()}`);
  return (await res.json()) as DashboardStats;
}

export interface CompressResponse {
  original: string;
  compressed: string;
  token_original: number;
  token_compressed: number;
  ratio: number;
  method: string;
}

export async function compressText(
  text: string,
  method: string = "auto",
): Promise<CompressResponse> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/compress`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, method }),
  });
  if (!res.ok) throw new Error(`Compress ${res.status}: ${await res.text()}`);
  return (await res.json()) as CompressResponse;
}

export interface CalibrationMetrics {
  n: number;
  alpha: number;
  threshold: number;
  error_bound: number;
  error_bound_simple: number;
  error_bound_hoeffding: number;
  risk_hat: number;
  ece: number;
  reliability: { bin: number; accuracy: number; confidence: number; count: number }[];
  is_real?: boolean;
  real_path?: string;
}

export async function fetchCalibrationMetrics(): Promise<CalibrationMetrics> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/calibration/metrics`);
  if (!res.ok) throw new Error(`Calibration ${res.status}: ${await res.text()}`);
  return (await res.json()) as CalibrationMetrics;
}

export interface ReasoningBudgetResp {
  reasoning_tokens: number;
  code_mix_ratio: number;
  math_marker_count: number;
  logic_marker_count: number;
  english_gloss?: string;
  english_budget?: number;
  delta_hinglish_minus_english?: number;
}

export async function fetchReasoningBudget(
  text: string,
  english_gloss?: string,
): Promise<ReasoningBudgetResp> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/reasoning/budget`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, english_gloss }),
  });
  if (!res.ok) throw new Error(`Budget ${res.status}: ${await res.text()}`);
  return (await res.json()) as ReasoningBudgetResp;
}

export interface SeriesPoint {
  bucket: string;
  queries: number;
  savings_usd: number;
}

export async function fetchSeries(window: number = 3600): Promise<SeriesPoint[]> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/dashboard/series?window=${window}`);
  if (!res.ok) throw new Error(`Series ${res.status}: ${await res.text()}`);
  return (await res.json()) as SeriesPoint[];
}

export async function fetchRecent(limit: number = 20): Promise<unknown[]> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/dashboard/recent?limit=${limit}`);
  if (!res.ok) throw new Error(`Recent ${res.status}: ${await res.text()}`);
  return (await res.json()) as unknown[];
}

export async function fetchHealth(): Promise<Record<string, unknown>> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/healthz`);
  if (!res.ok) throw new Error(`Health ${res.status}: ${await res.text()}`);
  return (await res.json()) as Record<string, unknown>;
}

export async function* streamChatCompletion(
  message: string,
): AsyncGenerator<{ content: string; meta?: GatewayMeta }, void, unknown> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "cascade",
      messages: [{ role: "user", content: message }],
      stream: true,
    }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Gateway ${res.status}: ${body}`);
  }
  if (!res.body) throw new Error("No response body");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      const data = line.slice(5).trim();
      if (data === "[DONE]") return;
      try {
        const obj = JSON.parse(data) as {
          choices?: { delta?: { content?: string } }[];
          x_gateway?: GatewayMeta;
        };
        if (obj.x_gateway) yield { content: "", meta: obj.x_gateway };
        const content = obj.choices?.[0]?.delta?.content;
        if (content) yield { content } as { content: string; meta?: GatewayMeta };
      } catch {
        continue;
      }
    }
  }
}
