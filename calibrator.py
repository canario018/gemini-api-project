from __future__ import annotations
import math


def brier_score(probabilities, outcomes) -> float:
    pairs = list(zip(probabilities, outcomes))
    if not pairs:
        return float("nan")
    return sum((float(p) - int(y)) ** 2 for p, y in pairs) / len(pairs)


def log_loss(probabilities, outcomes, eps: float = 1e-15) -> float:
    pairs = list(zip(probabilities, outcomes))
    if not pairs:
        return float("nan")
    total = 0.0
    for p, y in pairs:
        p = max(eps, min(1 - eps, float(p)))
        total += -(int(y) * math.log(p) + (1 - int(y)) * math.log(1 - p))
    return total / len(pairs)


def expected_calibration_error(probabilities, outcomes, bins: int = 10) -> float:
    pairs = list(zip(probabilities, outcomes))
    if not pairs:
        return float("nan")
    total = 0.0
    n = len(pairs)
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        bucket = [(p, y) for p, y in pairs if lo <= p < hi or (b == bins - 1 and p == hi)]
        if bucket:
            conf = sum(p for p, _ in bucket) / len(bucket)
            acc = sum(y for _, y in bucket) / len(bucket)
            total += len(bucket) / n * abs(conf - acc)
    return total


def calibrate_identity(probability: float) -> float:
    return max(1e-6, min(1 - 1e-6, float(probability)))
