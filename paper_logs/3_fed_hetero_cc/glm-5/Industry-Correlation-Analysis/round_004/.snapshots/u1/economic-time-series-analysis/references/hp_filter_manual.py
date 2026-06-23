"""
Manual Hodrick-Prescott filter implementation.

Use when statsmodels is unavailable or as a fallback.
The HP filter decomposes a time series y into trend (tau) and cyclical (c) components:
    y = tau + c

Minimizes: sum((y - tau)^2) + lambda * sum((tau_{t+1} - 2*tau_t + tau_{t-1})^2)

Returns: trend, cyclical (cyclical = y - trend)
"""

import numpy as np

def hp_filter(y, lamb=100):
    """
    Hodrick-Prescott filter implementation.
    
    Parameters
    ----------
    y : array_like
        Time series data (typically log-transformed real values)
    lamb : float
        Smoothing parameter:
        - 100 for annual data
        - 1600 for quarterly data  
        - 14400 for monthly data
    
    Returns
    -------
    trend : ndarray
        Trend component
    cycle : ndarray
        Cyclical component (y - trend)
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    
    if n < 3:
        return y.copy(), np.zeros(n)
    
    # Build second difference matrix D2 (n-2 x n)
    # D2[i, i] = 1, D2[i, i+1] = -2, D2[i, i+2] = 1
    D2 = np.zeros((n - 2, n))
    for i in range(n - 2):
        D2[i, i] = 1
        D2[i, i + 1] = -2
        D2[i, i + 2] = 1
    
    # Solve: (I + lambda * D2' @ D2) @ trend = y
    I = np.eye(n)
    A = I + lamb * (D2.T @ D2)
    trend = np.linalg.solve(A, y)
    cycle = y - trend
    
    return trend, cycle


# Example usage matching statsmodels API
def hpfilter(y, lamb=1600):
    """
    Statsmodels-compatible wrapper.
    Returns: cycle, trend (note: order reversed from hp_filter!)
    """
    trend, cycle = hp_filter(y, lamb)
    return cycle, trend


if __name__ == '__main__':
    # Verify against known properties
    np.random.seed(42)
    y = np.cumsum(np.random.randn(100)) + 100
    
    trend, cycle = hp_filter(y, lamb=100)
    
    # Cyclical should sum to approximately zero
    print(f"Cyclical mean: {np.mean(cycle):.2e}")
    print(f"Cyclical std: {np.std(cycle):.4f}")
    print(f"Reconstruction error: {np.max(np.abs(y - trend - cycle)):.2e}")
    
    # Verify statsmodels compatibility if available
    try:
        from statsmodels.tsa.filters.hp_filter import hpfilter as sm_hpfilter
        sm_cycle, sm_trend = sm_hpfilter(y, lamb=100)
        print(f"Match with statsmodels: {np.allclose(cycle, sm_cycle)}")
    except ImportError:
        print("statsmodels not available for comparison")