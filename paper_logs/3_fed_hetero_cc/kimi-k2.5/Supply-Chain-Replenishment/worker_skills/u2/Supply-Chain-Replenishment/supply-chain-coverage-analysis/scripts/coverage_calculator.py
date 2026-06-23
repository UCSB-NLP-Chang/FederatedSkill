#!/usr/bin/env python3
"""
Inventory coverage calculator helper.
Import functions or run standalone with JSON input.
"""
from datetime import datetime, timedelta
from math import ceil
from typing import Dict, List, Tuple, Any

def calculate_coverage(
    as_of_date: datetime,
    horizon_end: datetime,
    stock_row: Dict[str, Any],
    inbound_list: List[Dict[str, Any]],
    pallet_size: int = 50
) -> Dict[str, Any]:
    """
    Calculate coverage metrics for a single Zone/SKU.

    Args:
        as_of_date: Planning start date
        horizon_end: Planning end date
        stock_row: Dict with 'On_Hand', 'Daily_Demand'
        inbound_list: List of dicts with 'ETA', 'Units'
        pallet_size: Units per pallet

    Returns:
        Dict with all calculated fields
    """
    on_hand = float(stock_row.get('On_Hand', 0))
    daily_demand = float(stock_row.get('Daily_Demand', 1))  # avoid div/0

    planning_days = (horizon_end - as_of_date).days

    # Current state
    current_doh = on_hand / daily_demand
    oos_date = as_of_date + timedelta(days=current_doh)

    # Inbound within horizon
    inbound_total = sum(
        float(item['Units']) for item in inbound_list
        if item['ETA'] <= horizon_end
    )

    delivered_doh = (on_hand + inbound_total) / daily_demand
    remaining_demand = planning_days * daily_demand

    additional_needed = max(0, remaining_demand - on_hand - inbound_total)
    pallets = ceil(additional_needed / pallet_size) if additional_needed > 0 else 0

    # Earlier delivery check
    earlier_required = False
    if additional_needed > 0:
        earlier_required = True
        # Also true if inbound exists but arrives after OOS
        for item in inbound_list:
            if item['ETA'] > oos_date and item['ETA'] <= horizon_end:
                earlier_required = True
                break

    return {
        'Current_Days_On_Hand': current_doh,
        'Projected_OOS_Date': oos_date.date(),
        'Inbound_Units_By_Horizon': inbound_total,
        'Delivered_Days_On_Hand': delivered_doh,
        'Remaining_Demand_Units': remaining_demand,
        'Additional_Units_Needed': additional_needed,
        'Pallets_Required': pallets,
        'Required_Delivery_Date': oos_date.date() if additional_needed > 0 else None,
        'Earlier_Delivery_Required': earlier_required
    }

def deduplicate_inbound(feed_rows: List[Dict]) -> List[Dict]:
    """
    Deduplicate feed rows by Dispatch Ref, keeping max Revision.
    Assumes rows have 'Dispatch_Ref' and 'Revision' keys.
    """
    by_ref = {}
    for row in feed_rows:
        ref = row.get('Dispatch_Ref')
        if ref not in by_ref:
            by_ref[ref] = row
        else:
            if row.get('Revision', 0) > by_ref[ref].get('Revision', 0):
                by_ref[ref] = row
    return list(by_ref.values())

def filter_valid_inbound(
    rows: List[Dict],
    alias_map: Dict[str, str],
    horizon_end: datetime,
    valid_states: List[str] = None
) -> List[Dict]:
    """
    Filter and validate inbound rows.

    Returns list of validated rows with 'Zone' resolved from alias.
    """
    if valid_states is None:
        valid_states = ['Released', 'Staged']

    valid = []
    for row in rows:
        # State check
        if row.get('Release_State') not in valid_states:
            continue

        # Alias resolution
        alias = row.get('Zone_Alias')
        if alias not in alias_map:
            continue
        row['Zone'] = alias_map[alias]

        # SKU validation
        if not row.get('SKU_Code'):
            continue

        # ETA validation
        eta = row.get('ETA')
        if not isinstance(eta, datetime):
            continue
        if eta > horizon_end:
            continue

        valid.append(row)

    return valid

if __name__ == '__main__':
    print("Import these functions or use as reference for coverage calculations.")
