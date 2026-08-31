import { describe, expect, it, vi } from "vitest";
import {
  fetchDifficultyFeatures,
  fetchRewardAutopsy,
  fetchCompressCandidates,
  fetchPrompts,
  fetchReceipt,
  sendFeedback,
  fetchCalibrationMetrics,
} from "../gateway";

describe("gateway client API functions", () => {
  it("fetches difficulty features with url encoding", async () => {
    const mockResp = {
      text: "yaar 15*8 kya hoga",
      char_count: 18,
      token_count: 5,
      code_mix_ratio: 0.5,
      entity_density: 0.0,
      math_marker_count: 1,
      w_code_mix: 0.4,
      w_entity: 0.3,
      w_math: 0.2,
      w_length: 0.1,
      contrib_code_mix: 0.2,
      contrib_entity: 0.0,
      contrib_math: 0.2,
      contrib_length: 0.018,
      difficulty_score: 0.418,
      threshold: 0.355,
      tier: "premium",
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResp,
    } as unknown as Response);

    const res = await fetchDifficultyFeatures("yaar 15*8 kya hoga");
    expect(res.difficulty_score).toBe(0.418);
    expect(res.tier).toBe("premium");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/v1/difficulty/features?text=yaar%2015*8%20kya%20hoga"),
      expect.any(Object),
    );
  });

  it("fetches reward autopsy with decomposed terms", async () => {
    const mockAutopsy = {
      original: "yaar mera phone charge nahi ho raha",
      compressed: "mera phone charge nahi ho raha",
      reference_answer: "check charger",
      predicted_answer: "check charger",
      answer_fidelity: 0.95,
      faithfulness: 0.9,
      w_fidelity: 0.7,
      w_faithfulness: 0.3,
      combined_reward: 0.935,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockAutopsy,
    } as unknown as Response);

    const res = await fetchRewardAutopsy(
      "yaar mera phone charge nahi ho raha",
      "mera phone charge nahi ho raha",
    );
    expect(res.combined_reward).toBe(0.935);
    expect(res.w_fidelity).toBe(0.7);
  });

  it("fetches compress candidates", async () => {
    const mockCandidates = {
      original: "yaar 15*8 kya hoga",
      candidates: [
        {
          index: 0,
          text: "15*8 kya hoga",
          tokens: 4,
          compression_ratio: 0.8,
          reward: 0.92,
          answer_fidelity: 1.0,
          faithfulness: 0.9,
          is_winner: true,
        },
      ],
      winner_index: 0,
      winner_text: "15*8 kya hoga",
      distilled_cpu_fallback: true,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockCandidates,
    } as unknown as Response);

    const res = await fetchCompressCandidates("yaar 15*8 kya hoga");
    expect(res.candidates).toHaveLength(1);
    expect(res.winner_text).toBe("15*8 kya hoga");
  });

  it("fetches prompts & system parameters", async () => {
    const mockPrompts = {
      compress_system_prompt: "You are a Hinglish prompt compressor.",
      compress_user_template: "Compress: {text}",
      difficulty_weights: { w_code_mix: 0.4, w_entity: 0.3, w_math: 0.2, w_length: 0.1 },
      reward_weights: { w_fidelity: 0.7, w_faithfulness: 0.3 },
      budget_params: {},
      pricing_date: "2026-08-28",
      commit_sha: "003d033",
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockPrompts,
    } as unknown as Response);

    const res = await fetchPrompts();
    expect(res.commit_sha).toBe("003d033");
    expect(res.difficulty_weights["w_code_mix"]).toBe(0.4);
  });

  it("fetches receipts and sends user feedback", async () => {
    const mockReceipt = {
      id: 1,
      task_id: "cmg-test-123",
      ts: 1724889600,
      user_id: "anon_test",
      original_tokens: 20,
      compressed_tokens: 14,
      model_routed: "llama-3.1-8b-instant",
      tier: "cheap",
      difficulty_score: 0.22,
      estimated_cost_savings: 0.00045,
      compressed_prompt: "mera phone charge nahi ho raha",
      was_correct: null,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockReceipt,
    } as unknown as Response);

    const r = await fetchReceipt("cmg-test-123");
    expect(r.task_id).toBe("cmg-test-123");
    expect(r.tier).toBe("cheap");

    // Send feedback
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ok: true,
        task_id: "cmg-test-123",
        was_correct: true,
        recalibrated: true,
      }),
    } as unknown as Response);

    const fb = await sendFeedback("cmg-test-123", true);
    expect(fb.ok).toBe(true);
    expect(fb.recalibrated).toBe(true);
  });

  it("fetches calibration metrics with sweep parameters", async () => {
    const mockCal = {
      n: 200,
      alpha: 0.05,
      threshold: 0.355,
      error_bound: 0.048,
      error_bound_simple: 0.005,
      error_bound_hoeffding: 0.048,
      risk_hat: 0.015,
      ece: 0.023,
      reliability: [],
      sweep: [
        { tau: 0.0, risk_hat: 0.0, risk_bound: 0.033, feasible: true },
        { tau: 0.355, risk_hat: 0.015, risk_bound: 0.048, feasible: true, is_selected: true },
      ],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockCal,
    } as unknown as Response);

    const cal = await fetchCalibrationMetrics(true, 200);
    expect(cal.sweep).toHaveLength(2);
    expect(cal.threshold).toBe(0.355);
  });
});
