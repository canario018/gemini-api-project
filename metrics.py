from __future__ import annotations
import math
from app.calibration.calibrator import brier_score, log_loss, expected_calibration_error

def roi(returns):
    values = list(returns)
    return sum(values) / len(values) if values else 0.0

def max_drawdown(returns):
    peak = equity = 0.0
    dd = 0.0
    for r in returns:
        equity += float(r)
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return dd

def sharpe(returns):
    values = list(map(float, returns))
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return mean / math.sqrt(var) if var > 0 else 0.0

def classification_metrics(probabilities, outcomes):
    return {
        "brier_score": brier_score(probabilities, outcomes),
        "log_loss": log_loss(probabilities, outcomes),
        "ece": expected_calibration_error(probabilities, outcomes),
    }
