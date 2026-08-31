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

export interface SweepPoint {
  tau: number;
  risk_hat: number;
  risk_bound: number;
  feasible: boolean;
  is_selected?: boolean;
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
  bench_n?: number;
  pad_n?: number;
  sweep?: SweepPoint[];
}

export async function fetchCalibrationMetrics(
  fullSweep: boolean = true,
  window?: number,
  realOnly: boolean = false,
): Promise<CalibrationMetrics> {
  const params = new URLSearchParams();
  if (fullSweep) params.set("full_sweep", "1");
  if (window) params.set("window", String(window));
  if (realOnly) params.set("real_only", "1");
  const qs = params.toString() ? `?${params.toString()}` : "";
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/calibration/metrics${qs}`);
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

export interface NovelReport {
  n_benchmark: number;
  tokenizer_tax: {
    buckets: {
      bucket: string;
      n: number;
      avg_code_mix: number;
      char4_inflation: number;
      inflation: Record<string, number>;
    }[];
    overall: Record<string, number>;
    hinglish_tax_ratio: number;
    n_controls: number;
  };
  adaptive: {
    n: number;
    methods: {
      method: string;
      avg_kept_pct: number;
      avg_kept_ratio: number;
      avg_reward: number;
      avg_savings: number;
      is_adaptive: boolean;
    }[];
  };
  reasoning_delta: {
    n_pairs: number;
    mean_delta: number;
    median_delta: number;
    hinglish_higher_pct: number;
    max_delta: number;
    min_delta: number;
    histogram: { delta: number; count: number }[];
    top_hinglish_heavier: { id: string; original: string; gloss: string; delta: number }[];
    items: unknown[];
  };
  conformal_compression: {
    threshold_reward: number;
    heuristic: { risk_hat: number; risk_bound: number; failures: number; n: number };
    distilled: { risk_hat: number; risk_bound: number; failures: number; n: number };
    adaptive: { risk_hat: number; risk_bound: number; failures: number; n: number };
    best_method: string;
  };
  summary_bullets: string[];
  generated_at: string;
}

export async function fetchNovel(): Promise<NovelReport> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/eval/novel`);
  if (!res.ok) throw new Error(`Novel ${res.status}: ${await res.text()}`);
  return (await res.json()) as NovelReport;
}

export async function compressAdaptive(
  text: string,
): Promise<
  CompressResponse & { adaptive_target?: number; code_mix_ratio?: number; difficulty?: number }
> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/compress`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, method: "adaptive" }),
  });
  if (!res.ok) throw new Error(`Adaptive ${res.status}: ${await res.text()}`);
  return (await res.json()) as CompressResponse & {
    adaptive_target?: number;
    code_mix_ratio?: number;
    difficulty?: number;
  };
}

export interface TokenEncodeResp {
  text: string;
  tokenizer: string;
  tokens: number;
  chars: number;
  tokens_per_char: number;
  backend: string;
  cost_cheap_usd: number;
  cost_premium_usd: number;
  chips: { id: number; token: number; text: string }[];
  pricing_date: string;
}

export async function fetchTokenEncode(
  text: string,
  tokenizer = "gpt4o_cl100k",
): Promise<TokenEncodeResp> {
  const res = await fetchWithTimeout(
    `${GATEWAY_URL}/v1/tokenizer/encode?text=${encodeURIComponent(text)}&tokenizer=${tokenizer}`,
  );
  if (!res.ok) throw new Error(`Encode ${res.status}: ${await res.text()}`);
  return (await res.json()) as TokenEncodeResp;
}

export async function fetchTokenBatch(
  texts: string[],
  tokenizer = "gpt4o_cl100k",
): Promise<{ results: { text: string; tokens: number; cost_premium_usd: number }[] }> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/tokenizer/encode_batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texts, tokenizer }),
  });
  if (!res.ok) throw new Error(`Batch ${res.status}: ${await res.text()}`);
  return (await res.json()) as {
    results: { text: string; tokens: number; cost_premium_usd: number }[];
  };
}

export interface InterpolateVariant {
  level: number;
  text: string;
  code_mix_ratio: number;
  tokens: number;
  tokens_per_char: number;
  cost_cheap_usd: number;
  cost_premium_usd: number;
  difficulty: number;
  adaptive_target: number;
  heuristic_kept_ratio: number;
  heuristic_compressed: string;
}
export async function fetchInterpolate(
  text: string,
  steps = 5,
): Promise<{ original: string; variants: InterpolateVariant[] }> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/code_mix/interpolate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, steps }),
  });
  if (!res.ok) throw new Error(`Interpolate ${res.status}: ${await res.text()}`);
  return (await res.json()) as { original: string; variants: InterpolateVariant[] };
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

export interface DifficultyAnatomyResp {
  text: string;
  char_count: number;
  token_count: number;
  code_mix_ratio: number;
  entity_density: number;
  math_marker_count: number;
  w_code_mix: number;
  w_entity: number;
  w_math: number;
  w_length: number;
  contrib_code_mix: number;
  contrib_entity: number;
  contrib_math: number;
  contrib_length: number;
  difficulty_score: number;
  threshold: number;
  tier: string;
}

export async function fetchDifficultyFeatures(text: string): Promise<DifficultyAnatomyResp> {
  const res = await fetchWithTimeout(
    `${GATEWAY_URL}/v1/difficulty/features?text=${encodeURIComponent(text)}`,
  );
  if (!res.ok) throw new Error(`Difficulty features ${res.status}: ${await res.text()}`);
  return (await res.json()) as DifficultyAnatomyResp;
}

export interface RewardAutopsyResp {
  original: string;
  compressed: string;
  reference_answer: string;
  predicted_answer: string;
  answer_fidelity: number;
  faithfulness: number;
  w_fidelity: number;
  w_faithfulness: number;
  combined_reward: number;
}

export async function fetchRewardAutopsy(
  text: string,
  compressed = "",
  ref = "",
  pred = "",
): Promise<RewardAutopsyResp> {
  const params = new URLSearchParams({ text });
  if (compressed) params.set("compressed", compressed);
  if (ref) params.set("ref", ref);
  if (pred) params.set("pred", pred);
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/reward/autopsy?${params.toString()}`);
  if (!res.ok) throw new Error(`Reward autopsy ${res.status}: ${await res.text()}`);
  return (await res.json()) as RewardAutopsyResp;
}

export interface CandidateItem {
  index: number;
  text: string;
  tokens: number;
  compression_ratio: number;
  reward: number;
  answer_fidelity: number;
  faithfulness: number;
  is_winner: boolean;
}

export interface CompressCandidatesResp {
  original: string;
  candidates: CandidateItem[];
  winner_index: number;
  winner_text: string;
  distilled_cpu_fallback: boolean;
}

export async function fetchCompressCandidates(text: string): Promise<CompressCandidatesResp> {
  const res = await fetchWithTimeout(
    `${GATEWAY_URL}/v1/compress/candidates?text=${encodeURIComponent(text)}`,
  );
  if (!res.ok) throw new Error(`Candidates ${res.status}: ${await res.text()}`);
  return (await res.json()) as CompressCandidatesResp;
}

export interface PromptsResp {
  compress_system_prompt: string;
  compress_user_template: string;
  difficulty_weights: Record<string, number>;
  reward_weights: Record<string, number>;
  budget_params: Record<string, unknown>;
  pricing_date: string;
  commit_sha: string;
}

export async function fetchPrompts(): Promise<PromptsResp> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/prompts`);
  if (!res.ok) throw new Error(`Prompts ${res.status}: ${await res.text()}`);
  return (await res.json()) as PromptsResp;
}

export interface ReceiptResp {
  id: number;
  task_id: string;
  ts: number;
  user_id: string;
  original_tokens: number;
  compressed_tokens: number;
  model_routed: string;
  tier: string;
  difficulty_score: number;
  estimated_cost_savings: number;
  compressed_prompt: string;
  was_correct: boolean | null;
}

export async function fetchReceipt(identifier: string): Promise<ReceiptResp> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/receipt/${encodeURIComponent(identifier)}`);
  if (!res.ok) throw new Error(`Receipt ${res.status}: ${await res.text()}`);
  return (await res.json()) as ReceiptResp;
}

export async function sendFeedback(
  taskId: string,
  wasCorrect: boolean,
): Promise<{ ok: boolean; task_id: string; was_correct: boolean; recalibrated: boolean }> {
  const res = await fetchWithTimeout(`${GATEWAY_URL}/v1/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, was_correct: wasCorrect }),
  });
  if (!res.ok) throw new Error(`Feedback ${res.status}: ${await res.text()}`);
  return (await res.json()) as {
    ok: boolean;
    task_id: string;
    was_correct: boolean;
    recalibrated: boolean;
  };
}
