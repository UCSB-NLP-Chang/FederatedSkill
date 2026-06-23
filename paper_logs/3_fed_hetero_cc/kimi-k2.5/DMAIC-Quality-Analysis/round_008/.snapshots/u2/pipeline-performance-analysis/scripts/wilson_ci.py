#!/usr/bin/env python3
"""Wilson score confidence interval for binomial proportions.

Pure numpy implementation - use when scipy is not available.
"""
import numpy as np

Z_95 = 1.959963984540054


def wilson_confidence_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple:
    """Wilson score confidence interval for binomial proportion.

    Args:
        successes: Number of successes (e.g., bugs found)
        trials: Number of trials (e.g., lines reviewed)
        confidence: Confidence level (default 0.95)

    Returns:
        (lower, upper) as floats in [0, 1]
    """
    if trials == 0:
        return 0.0, 1.0

    z = {0.90: 1.645, 0.95: Z_95, 0.99: 2.576}.get(confidence, Z_95)
    p = successes / trials
    n = trials

    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom

    return max(0.0, center - margin), min(1.0, center + margin)


def wilson_ci_percent(successes: int, trials: int, confidence: float = 0.95) -> tuple:
    """Return Wilson CI as percentages (0-100 scale)."""
    lower, upper = wilson_confidence_interval(successes, trials, confidence)
    return lower * 100, upper * 100


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        bugs = int(sys.argv[1])
        lines = int(sys.argv[2])
        lo, hi = wilson_ci_percent(bugs, lines)
        print(f"Rate: {bugs/lines*100:.4f}%")
        print(f"Wilson 95% CI: [{lo:.4f}%, {hi:.4f}%]")
