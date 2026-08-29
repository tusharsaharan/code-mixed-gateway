import pytest

from gateway.modules.m6_telegram import bot
from gateway.modules.m6_telegram.bot import TelegramBot, token_path


def test_db_log_and_stats(db):
    db.log("u1", 100, 40, "cheap-model", 0.0005)
    db.log("u2", 80, 20, "premium-model", 0.0)
    stats = db.stats()
    assert stats["queries"] == 2
    assert stats["total_original_tokens"] == 180
    assert stats["total_compressed_tokens"] == 60
    assert stats["total_cost_savings"] == pytest.approx(0.0005)


def test_token_path():
    assert token_path("abc") == "webhook/abc"


def test_bot_reply_format():
    meta = {"original_tokens": 100, "compressed_tokens": 40, "model_routed": "gpt-4o"}
    assert "100" in bot.bot_reply(meta)
    assert "40" in bot.bot_reply(meta)
    assert "gpt-4o" in bot.bot_reply(meta)


@pytest.mark.asyncio
async def test_handle_text_logs_to_db(db, monkeypatch):
    async def fake_gateway(text, gateway_url, model="cascade"):
        return "ye lo jawab", {
            "original_tokens": 120,
            "compressed_tokens": 50,
            "model_routed": "llama-3.1-8b-instant",
            "estimated_cost_savings_usd": 0.0001,
        }

    monkeypatch.setattr(bot, "call_gateway", fake_gateway)
    tb = TelegramBot(token="x", db=db)
    reply = await tb.handle_text("42", "physics ka numerical batao")
    assert reply == "ye lo jawab"
    stats = db.stats()
    assert stats["queries"] == 1
    assert stats["total_cost_savings"] == pytest.approx(0.0001)