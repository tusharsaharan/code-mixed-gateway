from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

TIER = Literal["cheap", "premium"]
METHOD = Literal["heuristic", "model", "passthrough", "distilled"]


class PromptRecord(BaseModel):
    id: str
    text: str
    lang_tag: str = "hi-en"
    domain: str = "support"
    fluff_ratio: float = 0.0
    meta: dict[str, Any] = Field(default_factory=dict)


class TokenizerReport(BaseModel):
    id: str
    tokenizer: str
    num_tokens: int
    chars: int
    tokens_per_char: float


class SafetySpan(BaseModel):
    kind: str
    text: str
    start: int
    end: int


class CompressResult(BaseModel):
    original: str
    compressed: str
    spans: list[SafetySpan] = Field(default_factory=list)
    token_original: int = 0
    token_compressed: int = 0
    ratio: float = 1.0
    method: METHOD = "heuristic"


class CalibSample(BaseModel):
    id: str
    nonconformity: float = Field(ge=0.0, le=1.0)
    cheap_success: bool


class DifficultyFeature(BaseModel):
    char_count: int = 0
    token_count: int = 0
    code_mix_ratio: float = 0.0
    entity_density: float = 0.0
    math_marker_count: int = 0


class DispatchResult(BaseModel):
    task_id: str
    model_routed: str
    score: float
    threshold: float
    tier: TIER
    response: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_est_usd: float = 0.0
    latency_ms: float = 0.0
    dry_run: bool = True


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "function", "tool"]
    content: str | list[dict[str, Any]]
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float = 1.0
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    max_tokens: int | None = None
    stop: str | list[str] | None = None
    user: str | None = None


class ReasoningBudget(BaseModel):
    reasoning_tokens: int = 0
    code_mix_ratio: float = 0.0
    math_marker_count: int = 0
    logic_marker_count: int = 0


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage = Field(default_factory=lambda: ChatMessage(role="assistant", content=""))
    finish_reason: str = "stop"


class GatewayMeta(BaseModel):
    original_tokens: int = 0
    compressed_tokens: int = 0
    compression_ratio: float = 1.0
    compressed_prompt: str = ""
    difficulty_score: float = 0.0
    conformal_threshold: float = 0.0
    tier: str = "cheap"
    model_routed: str = ""
    estimated_cost_usd: float = 0.0
    estimated_cost_savings_usd: float = 0.0
    reasoning_budget: int = 0
    budget_delta_hinglish_en: int | None = None
    error_bound: float = 0.05
    calibration_n: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    x_gateway: GatewayMeta | None = None


class ErrorDetail(BaseModel):
    message: str
    type: str = "invalid_request_error"
    param: str | None = None
    code: int | None = None


class OpenAIErrorResponse(BaseModel):
    error: ErrorDetail


class EvalRecord(BaseModel):
    id: str
    original: str
    compressed: str
    reference_answer: str
    predicted_answer: str = ""
    protected: list[str] = Field(default_factory=list)


class EvalResult(BaseModel):
    id: str
    token_savings_ratio: float
    bleu: float
    rouge_l: float
    task_success: float
    span_preserved: bool
    cost_usd: float
    baseline_cost_usd: float
    savings_usd: float
    cost_inr: float


class EvalSummary(BaseModel):
    n: int = 0
    mean_token_savings_ratio: float = 0.0
    mean_bleu: float = 0.0
    mean_rouge_l: float = 0.0
    mean_task_success: float = 0.0
    span_preserved_rate: float = 0.0
    total_cost_usd: float = 0.0
    total_baseline_usd: float = 0.0
    total_savings_usd: float = 0.0
    total_cost_inr: float = 0.0
    total_savings_inr: float = 0.0
    pricing_date: str = "2026-08-28"
    results: list[EvalResult] = Field(default_factory=list)


class DashboardStats(BaseModel):
    queries: int = 0
    total_original_tokens: int = 0
    total_compressed_tokens: int = 0
    total_cost_savings_usd: float = 0.0
    total_cost_savings_inr: float = 0.0
    tier_split: dict[str, int] = Field(default_factory=dict)


class SeriesPoint(BaseModel):
    bucket: str
    queries: int = 0
    savings_usd: float = 0.0