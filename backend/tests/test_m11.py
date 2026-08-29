from gateway.modules.m11_calibration.ece import (
    expected_calibration_error,
    reliability_diagram,
)


def test_ece_perfect_calibration_is_zero():
    # Predicted p = 0.9 for successes, 0.1 for failures → well-calibrated
    scores = [0.1] * 50 + [0.9] * 50
    labels = [True] * 50 + [False] * 50
    ece = expected_calibration_error(scores, labels, n_bins=10)
    assert ece < 0.15


def test_ece_miscalibrated_is_high():
    # Inverted: high confidence for failures
    scores = [0.9] * 50 + [0.1] * 50
    labels = [True] * 50 + [False] * 50
    ece_bad = expected_calibration_error(scores, labels, n_bins=10)
    assert ece_bad > 0.3


def test_ece_empty_returns_zero():
    assert expected_calibration_error([], [], n_bins=10) == 0.0


def test_reliability_diagram_has_bins():
    scores = [0.1, 0.9, 0.1, 0.9]
    labels = [True, False, True, False]
    diag = reliability_diagram(scores, labels, n_bins=2)
    assert len(diag) == 2
    assert all("accuracy" in b and "confidence" in b for b in diag)