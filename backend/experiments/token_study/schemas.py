from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

Arm = Literal["none", "llmlingua2", "llmlingua2_protected", "heuristic"]
CompressionStatus = Literal["ok", "fallback_original", "failed"]
AnswerStatus = Literal["ok", "api_error", "timeout", "invalid_output", "rate_limited"]


class StrictModel(BaseModel):
    model_config = {"extra": "forbid"}


class Turn(StrictModel):
    role: Literal["user", "assistant"]
    text: str


class ProtectedSpan(StrictModel):
    type: str
    value: str
    start: int
    end: int
    placeholder: str


class SourceExample(StrictModel):
    source_dialogue_id: str
    turn_index: int
    domain: str
    history: list[Turn]
    final_user_turn: str
    gold_state: dict[str, Any] | None
    gold_response: str | None
    script_mix: Literal["romanized", "devanagari", "mixed", "unknown"]
    source_revision: str
    locale: str = ""
    phenomenon: str = ""


class CompressionAttempt(StrictModel):
    pair_id: str
    arm: Arm
    requested_kept_rate: float
    original_prompt: str
    compressible_context: str
    compressed_context: str
    final_prompt: str
    original_token_count: int
    compressed_token_count: int
    achieved_kept_ratio: float
    protected_spans: list[ProtectedSpan]
    span_recall: float
    compression_status: CompressionStatus
    error_type: str | None


class AnswerAttempt(StrictModel):
    pair_id: str
    arm: str
    requested_kept_rate: float
    model: str
    model_version: str | None
    response: str | None
    raw_provider_usage: dict[str, Any] | None
    prompt_tokens: int | None
    completion_tokens: int | None
    answer_cost_usd: Decimal | None
    latency_ms: float | None
    status: AnswerStatus
    retry_count: int
    error_note: str | None = None


class JudgeAttempt(StrictModel):
    pair_id: str
    arm: str
    requested_kept_rate: float
    judge_model: str
    label: Literal["correct", "partially_correct", "incorrect"]
    error_tags: list[str]
    rationale: str = Field(max_length=500)
    score: float
