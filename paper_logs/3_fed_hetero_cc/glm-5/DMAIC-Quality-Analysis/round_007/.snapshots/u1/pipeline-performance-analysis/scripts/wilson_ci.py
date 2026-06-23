#!/usr/bin/env python3
"""Wilson score confidence interval for binomial proportion - pure numpy implementation.

Use when scipy is not available. This is the standard Wilson score interval.
"""

import numpy as np


def wilson_confidence_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple:
    """
    Calculate Wilson score confidence interval for a binomial proportion.
    
    Args:
        successes: Number of successes (e.g., bugs found)
        trials: Number of trials (e.g., lines of code)
        confidence: Confidence level (default 0.95 for 95% CI)
    
    Returns:
        tuple: (lower_bound, upper_bound) as proportions
    
    Note:
        This implementation uses the standard normal approximation.
        For 95% CI, z ≈ 1.96.
    """
    if trials == 0:
        return (0.0, 1.0)
    
    # Z-score for confidence level
    # For 95% CI: z = 1.96
    # For other levels, use inverse normal CDF approximation
    z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)
    
    p = successes / trials
    n = trials
    
    # Wilson score formula
    denominator = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denominator
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
    
    lower = max(0, center - margin)
    upper = min(1, center + margin)
    
    return (lower, upper)


def wilson_ci_percent(successes: int, trials: int, confidence: float = 0.95) -> tuple:
    """Return Wilson CI as percentages (0-100 scale)."""
    lower, upper = wilson_confidence_interval(successes, trials, confidence)
    return (lower * 100, upper * 100)


if __name__ == "__main__":
    # Example: 1365 bugs in 51111 lines
    bugs = 1365
    lines = 51111
    lower, upper = wilson_ci_percent(bugs, lines)
    print(f"Bug rate: {bugs/lines*100:.4f}%")
    print(f"Wilson 95% CI: [{lower:.4f}%, {upper:.4f}%]")
