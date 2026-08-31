from __future__ import annotations

import math
from collections.abc import Iterable

from gateway.schemas import CalibSample

_GRID_SIZE = 200


class ConformalCalibrator:
    """Conformal risk control (CRC) for the cascade error rate.

    Chooses a difficulty threshold ``tau`` for a monotone deferral rule
    ``route to premium iff score >= tau`` so the *unconditional* error rate
    (queries routed to the cheap tier that would have been handled incorrectly)
    is bounded by ``alpha`` with confidence ``1 - delta``.

    Finite-sample bound is a Bonferroni-corrected Hoeffding upper confidence
    bound over a fixed grid of thresholds:

        R_hat(tau) = (1/n) * #{ i : s_i < tau and failure_i }
        R_ub(tau)  = R_hat(tau) + sqrt( log(m / delta) / (2 n) )

    where ``m`` is the grid size. ``tau`` is the largest grid point whose upper
    confidence bound is still within ``alpha`` (monotone non-decreasing risk),
    i.e. it maximizes cheap-tier coverage subject to the error guarantee.
    """

    def __init__(self, alpha: float = 0.05, delta: float = 0.05) -> None:
        self.alpha = alpha
        self.delta = delta
        self.threshold: float = 0.0
        self.n_calib: int = 0
        self.n_fail: int = 0
        self.risk_hat: float = 0.0
        self.risk_bound: float = 0.0
        self.samples: list[CalibSample] = []

    def calibrate(self, samples: Iterable[CalibSample]) -> ConformalCalibrator:
        rows = list(samples)
        self.samples = rows
        self.n_calib = len(rows)
        self.n_fail = sum(1 for s in rows if not s.cheap_success)
        if self.n_calib == 0:
            self.threshold = 0.0
            return self

        correction = math.sqrt(math.log(_GRID_SIZE / self.delta) / (2 * self.n_calib))
        best = 0.0
        for i in range(_GRID_SIZE + 1):
            tau = i / _GRID_SIZE
            risk = sum(
                1 for s in rows if s.nonconformity < tau and not s.cheap_success
            ) / self.n_calib
            if risk + correction <= self.alpha:
                best = tau

        self.threshold = best
        self.risk_hat = (
            sum(1 for s in rows if s.nonconformity < best and not s.cheap_success)
            / self.n_calib
        )
        self.risk_bound = self.risk_hat + correction
        return self

    def sweep(self) -> list[dict]:
        """Evaluate R_hat(tau) and R_ub(tau) across the 200-point grid.

        Exposes the full threshold scan so the threshold-sweep visualizer can
        render the selection frontier rather than a single black-box number.
        """
        if self.n_calib == 0 or not self.samples:
            return []
        correction = math.sqrt(math.log(_GRID_SIZE / self.delta) / (2 * self.n_calib))
        points: list[dict] = []
        for i in range(_GRID_SIZE + 1):
            tau = round(i / _GRID_SIZE, 4)
            risk = sum(
                1 for s in self.samples if s.nonconformity < tau and not s.cheap_success
            ) / self.n_calib
            bound = risk + correction
            points.append(
                {
                    "tau": tau,
                    "risk_hat": round(risk, 6),
                    "risk_bound": round(bound, 6),
                    "feasible": bound <= self.alpha,
                    "is_selected": abs(tau - self.threshold) < 1e-4,
                }
            )
        return points

    @classmethod
    def from_pairs(
        cls,
        scores: list[float],
        cheap_success: list[bool],
        alpha: float = 0.05,
        delta: float = 0.05,
    ) -> ConformalCalibrator:
        samples = [
            CalibSample(id=str(i), nonconformity=s, cheap_success=ok)
            for i, (s, ok) in enumerate(zip(scores, cheap_success, strict=True))
        ]
        return cls(alpha=alpha, delta=delta).calibrate(samples)

    def route_premium(self, score: float) -> bool:
        return score >= self.threshold

    def tier(self, score: float) -> str:
        return "premium" if self.route_premium(score) else "cheap"