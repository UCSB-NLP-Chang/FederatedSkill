#!/usr/bin/env python3
"""
Price reconciliation helper for catalog vs transaction data.

Usage in pandas:
    df['UNIT_PRICE_FINAL'], df['PRICE_STATUS'], df['RECONCILIATION_ACTION'] = zip(*df.apply(
        lambda row: reconcile_price(row, catalog_lookup.get(row['PRODUCT_ID'])), axis=1
    ))
"""

def reconcile_price(transaction_price, catalog_price, tolerance=0.01):
    """
    Reconcile transaction price against catalog price.
    
    Args:
        transaction_price: The price from transaction record
        catalog_price: The price from catalog (may be None/NaN)
        tolerance: Float comparison tolerance for "equal" prices
    
    Returns:
        (final_price, status, action) tuple
    """
    import pandas as pd
    import math
    
    if pd.isna(catalog_price):
        return transaction_price, 'transaction_only', 'no_catalog_match'
    
    if math.isclose(transaction_price, catalog_price, abs_tol=tolerance):
        return transaction_price, 'transaction_price', 'prices_match'
    
    # Default: prefer transaction price (actual charged amount)
    return transaction_price, 'transaction_override', 'used_transaction_unit_price'


def reconcile_price_prefer_catalog(transaction_price, catalog_price, tolerance=0.01):
    """Alternative: prefer catalog price when different."""
    import pandas as pd
    import math
    
    if pd.isna(catalog_price):
        return transaction_price, 'transaction_only', 'no_catalog_match'
    
    if math.isclose(transaction_price, catalog_price, abs_tol=tolerance):
        return transaction_price, 'matched', 'prices_match'
    
    return catalog_price, 'catalog_override', 'used_catalog_unit_price'


if __name__ == '__main__':
    # Test cases
    import pandas as pd
    
    test_cases = [
        (100.0, 100.0, 'prices_match'),
        (100.0, 100.005, 'prices_match'),  # within tolerance
        (100.0, 95.0, 'transaction_override'),
        (100.0, None, 'no_catalog_match'),
        (100.0, float('nan'), 'no_catalog_match'),
    ]
    
    for trans, cat, expected in test_cases:
        result = reconcile_price(trans, cat)
        assert result[2] == expected, f"Failed: {trans}, {cat} -> {result}, expected {expected}"
    
    print("All tests passed.")