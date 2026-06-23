#!/usr/bin/env python3
"""
Hodrick-Prescott filter for business cycle extraction.

Usage:
    from hp_filter import hp_filter
    trend, cycle = hp_filter(np.log(real_values), lamb=100)
"""

import numpy as np


def hp_filter(y, lamb=100):
    """
    Apply Hodrick-Prescott filter to separate trend and cyclical components.
    
    Args:
        y: array-like, time series data (typically log of real values)
        lamb: smoothing parameter (100 for annual, 1600 for quarterly, 14400 for monthly)
    
    Returns:
        tuple: (trend, cycle) where cycle = y - trend
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    
    if n < 3:
        return y.copy(), np.zeros_like(y)
    
    # Build second difference matrix
    I = np.eye(n)
    D2 = np.zeros((n-2, n))
    for i in range(n-2):
        D2[i, i] = 1
        D2[i, i+1] = -2
        D2[i, i+2] = 1
    
    # Solve (I + lamb*D'D)trend = y
    trend = np.linalg.solve(I + lamb * D2.T @ D2, y)
    cycle = y - trend
    
    return trend, cycle


if __name__ == "__main__":
    # Simple test
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        x = np.arange(100)
        y = np.log(x + 10) + 0.5 * np.sin(x / 5)  # trend + cycle
        trend, cycle = hp_filter(y, lamb=100)
        print(f"Input variance: {np.var(y):.4f}")
        print(f"Trend variance: {np.var(trend):.4f}")
        print(f"Cycle variance: {np.var(cycle):.4f}")
        print(f"Mean cycle (should be ~0): {np.mean(cycle):.6f}")
