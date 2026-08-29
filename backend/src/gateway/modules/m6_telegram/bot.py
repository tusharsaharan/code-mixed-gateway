from __future__ import annotations

from pathlib import Path

import httpx

from gateway.modules.m6_telegram.db import LogDB

DEFAULT_GATEWAY_URL = "http://127.0.0.1:8000"


async def call_gateway(
    text: str,
    gateway_url: str = DEFAULT_GATEWAY_URL,
    model: str = "cascade",
) -> tuple[str, dict]:
    """Forward a student query to the gateway; returns (reply_text, gateway_meta)."""
    payload = {"model": model, "messages": [{"role": "user", "content": text}]}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{gateway_url}/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
    reply = data["choices"][0]["message"]["content"]
    meta = data.get("x_gateway", {}) or {}
    return reply, meta


def bot_reply(meta: dict) -> str:
    return (
        f"tokens {meta.get('original_tokens', 0)} -> {meta.get('compressed_tokens', 0)} | "
        f"routed: {meta.get('model_routed', '?')}"
    )


class TelegramBot:
    """python-telegram-bot webhook/polling bridge to the FastAPI gateway."""

    def __init__(
        self,
        token: str,
        db: LogDB,
        gateway_url: str = DEFAULT_GATEWAY_URL,
    ) -> None:
        self.token = token
        self.db = db
        self.gateway_url = gateway_url

    async def handle_text(self, user_id: str, text: str) -> str:
        reply, meta = await call_gateway(text, self.gateway_url)
        self.db.log(
            user_id=user_id,
            original_tokens=int(meta.get("original_tokens", 0)),
            compressed_tokens=int(meta.get("compressed_tokens", 0)),
            model_routed=str(meta.get("model_routed", "")),
            estimated_cost_savings=float(meta.get("estimated_cost_savings_usd", 0.0)),
        )
        return reply

    async def handle_update(self, update, context) -> None:
        user_id = str(update.effective_user.id)
        text = update.message.text or ""
        try:
            reply = await self.handle_text(user_id, text)
        except Exception as exc:  # noqa: BLE001
            reply = f"sorry, gateway error: {exc}"
        await update.message.reply_text(reply)

    def build_app(self):
        from telegram.ext import ApplicationBuilder

        return ApplicationBuilder().token(self.token).build()

    def run_polling(self) -> None:
        app = self.build_app()
        from telegram.ext import CommandHandler, MessageHandler, filters

        start = CommandHandler(
            "start", lambda u, c: u.message.reply_text("namaste! apna sawal bhejo.")
        )
        text = MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_update)
        app.add_handler(start)
        app.add_handler(text)
        app.run_polling()

    def run_webhook(
        self, url: str, listen: str = "0.0.0.0", port: int = 8443, secret: str | None = None
    ) -> None:
        app = self.build_app()
        from telegram.ext import CommandHandler, MessageHandler, filters

        start = CommandHandler(
            "start", lambda u, c: u.message.reply_text("namaste! apna sawal bhejo.")
        )
        text = MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_update)
        app.add_handler(start)
        app.add_handler(text)
        # Use explicit secret, not full bot token, in URL path
        path_secret = secret or _derive_secret(self.token)
        app.run_webhook(
            listen=listen,
            port=port,
            url_path=token_path(path_secret),
            webhook_url=f"{url}/{token_path(path_secret)}",
            secret_token=path_secret if secret else None,
        )


def _derive_secret(token: str) -> str:
    # Fallback: last 8 chars, but prefer explicit webhook_secret via config
    return token[-8:] if token else ""


def token_path(secret: str) -> str:
    return f"webhook/{secret}"


def build_db(path: str | Path) -> LogDB:
    return LogDB(path)