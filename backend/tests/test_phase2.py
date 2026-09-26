"""Phase 2 tests: CRC fidelity control, isotonic calibration, LTT/Mondrian, alpha sweep."""

import pytest

from gateway.modules.m3_conformal.conformal import (
    ConformalCalibrator,
    _binomial_ub,
    _fixed_sequence_threshold,
    _knee_detection,
)
from gateway.modules.m3_conformal.crc import ConformalFidelityControl, CRCSample, _pava
from gateway.modules.m3_conformal.isotonic import IsotonicCalibrator, pava_isotonic
from gateway.schemas import CalibSample

# --- CRC fidelity control ----------------------------------------------------
#
# NOTE: the CRC fixed point carries a 1/(n+1) term, so certifying alpha=0.05
# needs n >= 19 samples. The tests below therefore replicate observations;
# this mirrors reality (small calibration sets correctly stay uncertified).


def test_crc_fixed_point_selects_max_aggressive_within_budget():
    # monotone loss family: lambda -> loss, 25 observations per level
    samples = [
        CRCSample(lam=0.2, loss=0.01),
        CRCSample(lam=0.4, loss=0.02),
        CRCSample(lam=0.6, loss=0.03),
        CRCSample(lam=0.8, loss=0.06),  # exceeds 0.05 budget in expectation
    ] * 25
    crc = ConformalFidelityControl(alpha=0.05)
    res = crc.calibrate(samples)
    assert res.lam_hat == pytest.approx(0.6)
    assert res.feasible is True
    assert res.monotone is True
    assert res.risk_bound <= 0.05 + 1e-9


def test_crc_infeasible_when_even_mildest_level_exceeds():
    samples = [CRCSample(lam=0.1, loss=0.4)] * 30
    res = ConformalFidelityControl(alpha=0.05).calibrate(samples)
    assert res.feasible is False
    assert res.lam_hat == 0.0


def test_crc_small_n_refuses_to_certify():
    # 4 samples -> 1/(n+1) = 0.2 floor > alpha -> correctly uncertified
    samples = [
        CRCSample(lam=0.2, loss=0.01),
        CRCSample(lam=0.4, loss=0.02),
        CRCSample(lam=0.6, loss=0.03),
        CRCSample(lam=0.8, loss=0.06),
    ]
    res = ConformalFidelityControl(alpha=0.05).calibrate(samples)
    assert res.feasible is False or res.lam_hat == 0.0


def test_crc_averages_multiple_observations_per_lambda():
    samples = [CRCSample(lam=0.5, loss=loss) for loss in (0.01, 0.03, 0.05)] * 10
    res = ConformalFidelityControl(alpha=0.10).calibrate(samples)
    assert res.lam_hat == pytest.approx(0.5)
    assert res.risk_hat == pytest.approx(0.03, abs=1e-6)


def test_crc_regularizes_non_monotone_input():
    # 0.4 has HIGHER loss than 0.6 — non-monotone; PAVA must pool and flag
    base = [
        CRCSample(lam=0.2, loss=0.01),
        CRCSample(lam=0.4, loss=0.20),
        CRCSample(lam=0.6, loss=0.02),
    ]
    res = ConformalFidelityControl(alpha=0.05).calibrate(base * 25)
    assert res.monotone is False
    # pooled risks at (0.4, 0.6) = 0.11 -> infeasible at alpha 0.05; only 0.2 passes
    assert res.lam_hat == pytest.approx(0.2)


def test_crc_from_rewards_helper():
    lambdas = [0.3, 0.5, 0.7] * 25
    rewards = [0.95, 0.90, 0.70] * 25
    res = ConformalFidelityControl(alpha=0.10).calibrate_from_rewards(lambdas, rewards)
    # losses: 0.05, 0.10, 0.30. At lam=0.5 risk equals alpha exactly, so the
    # fixed-point bound (n/(n+1))R + 1/(n+1) = 0.1118 > 0.10 — correctly
    # rejected; the certified level is lam=0.3.
    assert res.lam_hat == pytest.approx(0.3)
    assert res.risk_hat == pytest.approx(0.05, abs=1e-6)


def test_crc_empty_samples():
    res = ConformalFidelityControl(alpha=0.05).calibrate([])
    assert res.lam_hat == 0.0
    assert res.n == 0


def test_pava_monotone_passthrough_and_pooling():
    vals, mono = _pava([0.1, 0.2, 0.3])
    assert mono is True
    assert vals == [0.1, 0.2, 0.3]
    vals2, mono2 = _pava([0.3, 0.1, 0.2])
    assert mono2 is False
    # pooled: first two average to 0.2, then 0.2, 0.2
    assert vals2 == pytest.approx([0.2, 0.2, 0.2])


# --- isotonic calibration ------------------------------------------------------


def test_isotonic_fit_and_predict():
    scores = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    failures = [False, False, False, True, False, True, True, True]
    iso = IsotonicCalibrator().fit(scores, failures)
    assert iso.fitted
    assert iso.predict(0.05) == pytest.approx(iso.predict(0.1))
    assert iso.predict(0.95) >= iso.predict(0.15)  # non-decreasing
    mid = iso.predict(0.45)
    assert 0.0 <= mid <= 1.0


def test_isotonic_ece_zero_on_perfectly_calibrated():
    # scores exactly equal realized failure rates in two strata
    scores = [0.2] * 10 + [0.8] * 10
    failures = [False] * 8 + [True] * 2 + [True] * 8 + [False] * 2
    iso = IsotonicCalibrator().fit(scores, failures)
    ece = iso.ece(scores, failures)
    assert ece <= 0.05


def test_pava_isotonic_ties_averaged():
    xs, ys = pava_isotonic([0.5, 0.5, 0.5, 1.0], [0.0, 1.0, 0.0, 1.0])
    assert len(xs) == 2
    assert xs[0] == 0.5 and xs[1] == 1.0
    assert ys[0] == pytest.approx(1.0 / 3.0)


# --- fixed-sequence LTT --------------------------------------------------------


def test_fixed_sequence_dominates_hoeffding():
    import random

    rng = random.Random(11)
    scores = [rng.uniform(0, 1) for _ in range(400)]
    failures = [s < 0.30 for s in scores]  # cheap fails below 0.30
    alpha, delta = 0.10, 0.05
    tau_fs, risk_fs, bound_fs = _fixed_sequence_threshold(scores, failures, alpha, delta)
    cal_h = ConformalCalibrator(alpha=alpha, delta=delta, method="hoeffding").from_pairs(scores, failures)
    assert tau_fs >= cal_h.threshold, "fixed-sequence must dominate Hoeffding"
    assert bound_fs <= alpha + 1e-9


def test_binomial_ub_sane_without_scipy():
    # Chernoff fallback: n=100, k=0, delta=0.05 -> sqrt(log(20)/200) ≈ 0.122
    ub = _binomial_ub(100, 0.0, 0.05)
    assert 0.0 < ub < 0.15
    ub2 = _binomial_ub(100, 50.0, 0.05)
    assert 0.5 <= ub2 <= 1.0
    # larger n tightens the zero-count bound
    ub3 = _binomial_ub(10_000, 0.0, 0.05)
    assert ub3 < 0.02


def test_route_premium_monotone():
    scores = [0.1, 0.3, 0.5, 0.7, 0.9]
    labels = [True, True, True, False, False]
    cal = ConformalCalibrator(alpha=0.10).from_pairs(scores, labels)
    t = cal.threshold
    assert not cal.route_premium(t - 0.01)
    assert cal.route_premium(t + 0.01)


# --- Mondrian -------------------------------------------------------------------


def _mondrian_samples():
    # low-mix group: cheap tier is safe up to high difficulty
    # high-mix group: cheap tier fails earlier
    rows = []
    for i in range(40):
        rows.append(CalibSample(id=f"lo-{i}", nonconformity=i / 40, cheap_success=True, group="low"))
    for i in range(40):
        ok = i < 10
        rows.append(CalibSample(id=f"hi-{i}", nonconformity=i / 40, cheap_success=ok, group="high"))
    return rows


def test_mondrian_per_group_thresholds():
    rows = _mondrian_samples()
    cal = ConformalCalibrator(alpha=0.10, delta=0.10).calibrate(rows)
    assert cal.is_mondrian
    assert set(cal.group_thresholds) == {"low", "high"}
    # low group should tolerate a higher tau (cheap safe) than high group
    assert cal.group_thresholds["low"] >= cal.group_thresholds["high"]
    # per-group routing respects its own threshold
    assert cal.route_premium(0.5, group="low") is False or cal.group_thresholds["low"] <= 0.5
    assert cal.route_premium(0.5, group="high") is True  # tau_high <= 0.25-ish


def test_mondrian_sweep_by_group():
    rows = _mondrian_samples()
    cal = ConformalCalibrator(alpha=0.10, delta=0.10).calibrate(rows)
    sw = cal.sweep_by_group()
    assert set(sw) == {"low", "high"}
    assert len(sw["low"]) == 201 and len(sw["high"]) == 201
    for _g, pts in sw.items():
        assert any(p["is_selected"] for p in pts)


def test_single_group_is_not_mondrian():
    rows = [CalibSample(id=f"a{i}", nonconformity=i / 10, cheap_success=i < 5) for i in range(10)]
    cal = ConformalCalibrator(alpha=0.2).calibrate(rows)
    assert not cal.is_mondrian
    assert cal.group_thresholds == {}


# --- alpha sweep / knee -----------------------------------------------------------


def test_alpha_sweep_rows_and_knee():
    rows = _mondrian_samples() + _mondrian_samples()
    cal = ConformalCalibrator(alpha=0.10, delta=0.10).calibrate(rows)
    sweep = cal.alpha_sweep(alphas=[0.05, 0.10, 0.20, 0.40])
    assert len(sweep["rows"]) == 4
    for r in sweep["rows"]:
        assert 0 <= r["threshold"] <= 1.0
        assert 0 <= r["risk_hat"] <= 1.0
        assert r["risk_bound"] >= r["risk_hat"] - 1e-9
    # monotone: larger alpha permits weakly more cheap routing
    shares = [r["cheap_share"] for r in sweep["rows"]]
    assert all(a <= b + 1e-9 for a, b in zip(shares, shares[1:], strict=False))
    # at generous alpha=0.40 the low group must be routable cheap
    assert sweep["rows"][-1]["cheap_share"] > 0.0


def test_knee_detection_basic():
    # concave curve with knee at x=0.5
    xs = [0.0, 0.25, 0.5, 0.75, 1.0]
    ys = [0.0, 0.45, 0.7, 0.85, 1.0]
    knee = _knee_detection(xs, ys)
    assert knee is not None
    assert 0.25 <= knee <= 0.75


# --- endpoint ----------------------------------------------------------------------


def test_threshold_sweep2d_endpoint():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    with TestClient(app) as client:
        r = client.post("/v1/threshold/sweep2d", json={})
        assert r.status_code == 200
        body = r.json()
        assert "rows" in body
        assert "knee_alpha" in body
        assert "isotonic" in body
        assert "current_alpha" in body
        for row in body["rows"]:
            assert {"alpha", "threshold", "risk_hat", "risk_bound", "cheap_share"} <= set(row)
        iso = body["isotonic"]
        assert "ece" in iso
        assert "calibration_curve" in iso


def test_threshold_sweep2d_custom_alphas():
    from fastapi.testclient import TestClient

    from gateway.modules.m5_gateway.main import app

    with TestClient(app) as client:
        r = client.post("/v1/threshold/sweep2d", json={"alphas": [0.02, 0.08], "include_isotonic": False})
        assert r.status_code == 200
        body = r.json()
        assert [row["alpha"] for row in body["rows"]] == [0.02, 0.08]
        assert "isotonic" not in body
