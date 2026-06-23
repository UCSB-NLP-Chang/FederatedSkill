#!/usr/bin/env python3
"""
Calculate statistics using only standard library for verifying Excel formulas.
Use when numpy/pandas unavailable and you need to validate expected formula outputs.
"""
import statistics
import sys
import json

def calculate_all(values, weights=None):
    """
    Calculate common statistics for Excel verification.

    Args:
        values: List of numbers
        weights: Optional list of weights for weighted mean

    Returns:
        dict with min, max, median, mean, percentile_25, percentile_75, weighted_mean
    """
    if not values:
        return {}

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    # Percentile calculation (method matches Excel's PERCENTILE.INC)
    def percentile(p):
        if n == 1:
            return sorted_vals[0]
        k = (n - 1) * p
        f = int(k)
        c = f + 1 if f + 1 < n else f
        return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])

    result = {
        'min': min(values),
        'max': max(values),
        'median': statistics.median(values),
        'mean': statistics.mean(values),
        'percentile_25': percentile(0.25),
        'percentile_75': percentile(0.75)
    }

    if weights and len(weights) == len(values):
        weighted_sum = sum(v * w for v, w in zip(values, weights))
        weight_total = sum(weights)
        result['weighted_mean'] = weighted_sum / weight_total if weight_total != 0 else 0

    return result

if __name__ == "__main__":
    # Example usage: python calculate_stats.py '[1,2,3,4,5]' '[10,20,30,20,10]'
    if len(sys.argv) > 1:
        values = json.loads(sys.argv[1])
        weights = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
        print(json.dumps(calculate_all(values, weights), indent=2))
    else:
        print("Usage: python calculate_stats.py '[values]' '[weights]'")
