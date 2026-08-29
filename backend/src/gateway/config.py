from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class TierConfig(BaseModel):
    model: str
    base_url: str
    api_key: str = ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="GATEWAY_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    dry_run: bool = True
    alpha: float = 0.05
    data_dir: Path = Path("data")
    pilot_db: Path = Path("data/pilot.sqlite")
    fx_rate_inr_per_usd: float = 83.5
    log_requests: bool = True
    cors_origins: list[str] = ["*"]
    compressor_method: str = "heuristic"
    distilled_checkpoint: Path = Path("data/checkpoints/distilled.json")
    pricing_date: str = "2026-08-28"
    timeout_s: float = 30.0
    telegram_webhook_secret: str = ""

    cheap: TierConfig = TierConfig(
        model="llama-3.1-8b-instant", base_url="https://api.groq.com/openai/v1"
    )
    premium: TierConfig = TierConfig(model="gpt-4o", base_url="https://api.openai.com/v1")
    local: TierConfig = TierConfig(model="qwen3.6", base_url="http://localhost:11434/v1")

    telegram_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()