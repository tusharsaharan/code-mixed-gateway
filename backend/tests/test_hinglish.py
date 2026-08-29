from gateway.modules.m1_pipeline.hinglish import code_mix_ratio


def test_romanized_hinglish_is_detected():
    assert code_mix_ratio("yaar mera phone charge nahi ho raha hai") > 0.3


def test_english_has_zero_code_mix():
    assert code_mix_ratio("solve this equation for x") == 0.0


def test_devanagari_is_detected():
    assert code_mix_ratio("ये equation solve karo") > 0.0


def test_preset_hosts_wifi_hinglish():
    assert code_mix_ratio("hostel ka wifi bahut slow chal raha hai, complaint kahan karni hai?") > 0.3


def test_bilingual_difficulty_reflects_hinglish():
    from gateway.modules.m4_router.difficulty import DifficultyScorer

    en = DifficultyScorer().score("solve this equation for x please")
    hi = DifficultyScorer().score("yaar ye equation solve karo x ke liye please")
    assert hi > en


def test_reasoning_budget_reflects_hinglish():
    from gateway.modules.m9_reasoning.budget import ReasoningBudgetEstimator

    est = ReasoningBudgetEstimator()
    en = est.estimate("solve this equation for x")
    hi = est.estimate("yaar ye equation solve karo x ke liye")
    assert hi.code_mix_ratio > 0.0
    assert en.code_mix_ratio == 0.0
    assert hi.reasoning_tokens > en.reasoning_tokens
