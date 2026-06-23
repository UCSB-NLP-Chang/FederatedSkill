#!/usr/bin/env python3
"""
Pallet calculation utilities for inventory/shipment planning.
Use for: cases-to-pallets, round-up logic, partial pallet handling.
"""

import numpy as np
import pandas as pd


def calculate_pallets(cases: float, cases_per_pallet: float, round_up: bool = True) -> int:
    """
    Convert cases to pallets.
    
    Args:
        cases: Number of cases (can be float for calculated values)
        cases_per_pallet: Conversion ratio (e.g., 80)
        round_up: If True, use ceiling; if False, use floor
    
    Returns:
        Integer number of pallets
    """
    if pd.isna(cases) or cases <= 0:
        return 0
    
    pallets = cases / cases_per_pallet
    if round_up:
        return int(np.ceil(pallets))
    return int(np.floor(pallets))


def add_pallet_columns(df: pd.DataFrame, 
                       cases_column: str,
                       cases_per_pallet: float,
                       output_column: str = 'Pallets_Required_Rounded_Up',
                       rounding_flag_column: str = 'Rounding_Applied') -> pd.DataFrame:
    """
    Add pallet calculation columns to DataFrame in-place.
    
    Adds:
    - output_column: Integer pallets (rounded up)
    - rounding_flag_column: Boolean indicating if rounding was applied
    """
    df[output_column] = df[cases_column].apply(
        lambda x: calculate_pallets(x, cases_per_pallet)
    )
    
    # True if fractional pallets existed (rounding was actually needed)
    df[rounding_flag_column] = (
        (df[cases_column] / cases_per_pallet) != 
        df[output_column]
    ).where(df[cases_column].notna(), False)
    
    return df


def check_earlier_delivery_required(required_date, earliest_inbound_date) -> bool:
    """
    Determine if earliest scheduled inbound is after required delivery date.
    
    Returns True if inventory will arrive too late.
    """
    if pd.isna(required_date) or pd.isna(earliest_inbound_date):
        return False
    return earliest_inbound_date > required_date


if __name__ == '__main__':
    # Example usage
    df = pd.DataFrame({
        'SKU': ['A', 'B', 'C'],
        'Additional_Cases_Needed': [1157.6, 282.3, 0]
    })
    
    df = add_pallet_columns(df, 'Additional_Cases_Needed', 80.0)
    print(df)
    # Output: Pallets_Required_Rounded_Up = [15, 4, 0]
    #         Rounding_Applied = [True, True, False]