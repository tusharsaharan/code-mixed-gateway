import json

import pytest

from experiments.token_study import protected_spans as ps
from experiments.token_study.analyze import choose_safe_rate, paired_bootstrap
from experiments.token_study.build_prompts import render_prompt, script_mix_of
from experiments.token_study.download_and_validate import assert_official_url, build_splits, validate_examples
from experiments.token_study.schemas import CompressionAttempt, SourceExample, Turn
from experiments.token_study.score_structured import canonical, flatten_slots, parse_state, score_pair
from experiments.token_study.study_common import pair_id


def test_schemas_forbid_extra_and_bad_arm():
    with pytest.raises(Exception):
        SourceExample(
            source_dialogue_id="d1", turn_index=0, domain="x", history=[], final_user_turn="hi",
            gold_state=None, gold_response="yo", script_mix="romanized", source_revision="r",
            injected="nope",
        )
    with pytest.raises(Exception):
        CompressionAttempt(
            pair_id="p", arm="gpt4", requested_kept_rate=0.5, original_prompt="a",
            compressible_context="a", compressed_context="a", final_prompt="a",
            original_token_count=1, compressed_token_count=1, achieved_kept_ratio=1.0,
            protected_spans=[], span_recall=1.0, compression_status="ok", error_type=None,
        )


def test_pair_id_deterministic_and_shaped():
    a = pair_id("src", "dlg", 3, "v1")
    assert a == pair_id("src", "dlg", 3, "v1")
    assert len(a) == 16
    assert pair_id("src", "dlg", 4, "v1") != a


def test_mask_reinject_roundtrip_and_fail_closed():
    text = "bhejo user@example.com ko, total Rs. 2,500 kal 12-05-2026 tak"
    spans = ps.detect_spans(text)
    assert {s.type for s in spans} >= {"email", "currency", "datetime"}
    masked = ps.mask_text(text, spans)
    assert "user@example.com" not in masked
    final, ok, err = ps.reinject_text(masked, spans)
    assert ok and final == text and err is None
    broken = masked.replace(spans[0].placeholder, "")
    _, ok2, err2 = ps.reinject_text(broken, spans)
    assert not ok2 and err2 == "placeholder_lost"


def test_overlapping_spans_merge_deterministically():
    spans = ps.detect_spans("call +91-98765-43210 now")
    assert len(spans) == 1 and spans[0].type == "phone"


def test_malicious_fake_placeholder_fails_closed():
    spans = ps.detect_spans("pay Rs. 100 now")
    fake = spans[0].placeholder
    tampered = ps.mask_text("pay Rs. 100 now", spans) + " " + fake
    _, ok, _ = ps.reinject_text(tampered, spans)
    assert not ok  # duplicate placeholder must fail closed, not reinject twice


def test_span_recall_empty_spans_is_one():
    assert ps.span_recall("anything", []) == 1.0


def test_canonical_and_slot_scoring():
    assert canonical({"b": 1, "a": {"Y": " X  y "}}) == {"a": {"Y": "x y"}, "b": 1}
    gold = {"domain": "hotel", "slots": {"area": "North", "price": "cheap"}}
    good = json.dumps({"state": {"slots": {"price": "CHEAP ", "area": "north"}, "domain": "hotel"}, "response": "ok"})
    s = score_pair(gold, good)
    assert s["em"] == 1.0 and s["slot_f1"] == 1.0
    bad = json.dumps({"state": {"domain": "hotel", "slots": {"area": "south"}}, "response": "ok"})
    s2 = score_pair(gold, bad)
    assert s2["em"] == 0.0 and s2["slot_f1"] < 1.0
    assert score_pair(gold, "not json at all {{{")["parse"] == "invalid_json"
    # absent-vs-empty rule: predicting nothing extra for absent slots is not penalized as FP
    s3 = score_pair({"a": "1"}, json.dumps({"state": {"a": "1", "b": ""}, "response": "x"}))
    assert s3["slot_p"] == 1.0


def test_prompt_shell_byte_identical_and_offsets_valid():
    hist = [Turn(role="user", text="mujhe refund chahiye"), Turn(role="assistant", text="kitna?")]
    full, offs = render_prompt("SYS", hist, "Rs. 100 wala")
    assert full[offs["system"][0] : offs["system"][1]].endswith("SYS")
    assert "CURRENT USER REQUEST (never compress)\nUSER: Rs. 100 wala" in full
    assert full[offs["history"][0] : offs["history"][1]].startswith("DIALOGUE HISTORY")
    assert script_mix_of("yaar hello") == "romanized"
    assert script_mix_of("नमस्ते hello") == "mixed"


def test_run_one_none_arm_is_identity():
    from experiments.token_study.run_compression import run_one

    hist = "DIALOGUE HISTORY (compressible)\nUSER: hi"
    out, status, spans, recall, err = run_one(hist, "none", 1.0, {"compression": {}})
    assert out == hist and status == "ok" and recall == 1.0 and err is None


def test_run_one_llmlingua2_refuses_without_library(monkeypatch):
    import gateway.modules.m2_compressor.llmlingua2 as m

    monkeypatch.setattr(m, "is_available", lambda: False)
    from experiments.token_study.run_compression import run_one

    with pytest.raises(RuntimeError, match="not installed"):
        run_one("USER: hi", "llmlingua2", 0.5, {"compression": {"checkpoint": "x", "force_tokens": []}})


def test_choose_safe_rate_rule():
    base = {"delta_quality_ci_low": -0.01, "span_recall_ci_low": 0.999,
            "failure_rate_delta": 0.0, "end_to_end_cost_saving": 0.2,
            "median_achieved_token_saving": 0.4, "p95_latency_ms": 100.0}
    assert choose_safe_rate([base])["status"] == "safe"
    bad = {**base, "span_recall_ci_low": 0.90}
    assert choose_safe_rate([bad])["status"] == "no_safe_rate"


def test_paired_bootstrap_bounds_ordered():
    groups = {"d1": [(1.0, 1.0), (0.0, 1.0)], "d2": [(1.0, 0.0)]}
    lo, hi = paired_bootstrap(groups, lambda f: sum(a - b for a, b in f) / len(f), seed=7, replicates=200)
    assert lo <= hi


def test_download_refuses_unofficial_url():
    with pytest.raises(ValueError, match="allowlist"):
        assert_official_url("https://huggingface.co/datasets/random/x-risawoz")


def test_validate_examples_rejects_malformed_and_empty():
    valid, excluded = validate_examples(
        [{"source_dialogue_id": "d", "turn_index": 0, "domain": "x",
          "history": [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "yo"}],
          "final_user_turn": "bye", "gold_state": {"a": 1}, "gold_response": None,
          "script_mix": "romanized"},
         {"source_dialogue_id": "d2", "turn_index": 0},
         {"source_dialogue_id": "d3", "turn_index": 0, "domain": "x", "history": [],
          "final_user_turn": "", "gold_state": None, "gold_response": None, "script_mix": "unknown"}],
        "rev1",
    )
    assert len(valid) == 1 and len(excluded) == 2


def test_splits_are_dialogue_level():
    ids = [f"d{i}" for i in range(200)]
    phen = {f"d{i}": ("code-mixing" if i < 100 else "") for i in range(200)}
    splits = build_splits(ids, {
        "data": {"split_seed": 20260926, "smoke_n": 20, "dev_n": 150,
                 "test_n": 50, "test_phenomenon": "code-mixing"}}, phen)
    assert len(splits["smoke"]) == 20 and len(splits["dev"]) == 130
    assert len(splits["test"]) == 50
    assert all(phen[d] == "code-mixing" for d in splits["test"])
    assert not (set(splits["smoke"]) & set(splits["dev"]))
    assert not (set(splits["smoke"]) & set(splits["test"]))
    assert not (set(splits["dev"]) & set(splits["test"]))


def test_run_all_refuses_test_with_mocks_and_unlocked(tmp_path):
    from experiments.token_study.run_all import main as run_main
    import sys

    cfg = {"study": {"locked_test": True}, "data": {}, "compression": {}, "answering": {}}
    cfg_path = tmp_path / "config.yaml"
    import yaml

    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    sys.argv = ["run_all", "--config", str(cfg_path), "--split", "test", "--run-id", "x", "--mock-answers"]
    with pytest.raises(ValueError, match="mock"):
        run_main()


def test_verify_run_fails_on_empty_dir(tmp_path):
    from experiments.token_study.verify_run import check_compression_smoke

    ok, _ = check_compression_smoke(tmp_path, {})
    assert ok is False


def test_groq_keys_parsing_and_dedup(monkeypatch):
    import os as _os

    from experiments.token_study.study_common import groq_keys

    monkeypatch.setenv("GROQ_API_KEY", "gsk_A,gsk_B, gsk_A ")
    monkeypatch.setenv("GROQ_API_KEY2", "gsk_C")
    monkeypatch.delenv("GROQ_API_KEY3", raising=False)
    assert groq_keys() == ["gsk_A", "gsk_B", "gsk_C"]
    assert _os.environ["GROQ_API_KEY"].startswith("gsk_")  # values untouched in env


def test_presto_adapter_parses_targets_and_filters(tmp_path):
    import json as _json

    from experiments.token_study.adapters.presto_adapter import adapt_file, parse_targets, script_mix_of

    intent, slots = parse_targets("Create_note ( trigger_time « 9pm » )")
    assert intent == "Create_note" and slots == {"trigger_time": "9pm"}
    with pytest.raises(ValueError):
        parse_targets("(((not a parse")
    assert script_mix_of("Make a memo") == "romanized"
    assert script_mix_of("Make a memo क्रिएट") == "mixed"

    raw = [
        {"inputs": "9pm पर याद दिलाओ", "targets": "Create_note ( trigger_time « 9pm » )",
         "metadata": {"example_id": "e1", "locale": "hi-IN", "linguistic_phenomena": "code-mixing",
                      "previous_turns": [{"user_query": "pehla", "response_text": "dusra"},
                                         {"user_query": "teesra", "response_text": ""}]}},
        {"inputs": "short", "targets": "Other ()",
         "metadata": {"example_id": "e2", "locale": "hi-IN", "linguistic_phenomena": "",
                      "previous_turns": [{"user_query": "only one", "response_text": ""}]}},
        {"inputs": "english only here", "targets": "Other ()",
         "metadata": {"example_id": "e3", "locale": "en-US", "linguistic_phenomena": "",
                      "previous_turns": [{"user_query": "a", "response_text": "b"},
                                         {"user_query": "c", "response_text": "d"}]}},
    ]
    src = tmp_path / "in.jsonl"
    src.write_text("\n".join(_json.dumps(r, ensure_ascii=False) for r in raw), encoding="utf-8")
    rows, rep = adapt_file(src, 2, "rev-test")
    assert [r["source_dialogue_id"] for r in rows] == ["e1"]  # e2 short ctx, e3 wrong locale
    assert rows[0]["gold_state"] == {"intent": "Create_note", "slots": {"trigger_time": "9pm"}}
    assert rows[0]["phenomenon"] == "code-mixing"
    assert rep["kept"] == 1
