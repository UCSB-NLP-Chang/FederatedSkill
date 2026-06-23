#!/usr/bin/env python3
"""Reference implementation for inventory load planning calculations."""

from datetime import date, timedelta
from math import ceil, floor


def calculate_days_on_hand(on_floor: float, daily_sales: float) -> float:
    """Calculate current days on hand. Returns 0 if daily_sales is 0."""
    if daily_sales <= 0:
        return 0
    return on_floor / daily_sales


def calculate_oos_date(as_of_date: date, days_on_hand: float) -> date:
    """Calculate projected out-of-stock date."""
    return as_of_date + timedelta(days=floor(days_on_hand))


def calculate_remaining_demand(
    daily_sales: float,
    planning_days: int,
    on_floor: float,
    inbound_cases: float
) -> float:
    """Calculate remaining demand after current stock and scheduled inbounds."""
    total_demand = daily_sales * planning_days
    return total_demand - on_floor - inbound_cases


def calculate_additional_cases_needed(remaining_demand: float) -> float:
    """Calculate additional cases needed (non-negative)."""
    return max(0, remaining_demand)


def calculate_pallets_required(additional_cases: float, cases_per_pallet: int) -> int:
    """Calculate pallets required using ceiling to ensure full coverage."""
    if additional_cases <= 0:
        return 0
    return ceil(additional_cases / cases_per_pallet)


def calculate_earlier_delivery_required(
    inbound_arrival_date: date | None,
    required_delivery_date: date
) -> bool:
    """Check if scheduled inbound arrives after required delivery date."""
    if inbound_arrival_date is None:
        return True  # No inbound scheduled, need earlier delivery
    return inbound_arrival_date > required_delivery_date


def calculate_item_load_plan(
    item_code: str,
    on_floor: float,
    daily_sales: float,
    as_of_date: date,
    horizon_end: date,
    inbound_cases: float,
    inbound_arrival_date: date | None,
    cases_per_pallet: int
) -> dict:
    """Calculate complete load plan for a single item."""
    planning_days = (horizon_end - as_of_date).days + 1

    days_on_hand = calculate_days_on_hand(on_floor, daily_sales)
    oos_date = calculate_oos_date(as_of_date, days_on_hand)

    delivered_doh = (on_floor + inbound_cases) / daily_sales if daily_sales > 0 else 0

    remaining_demand = calculate_remaining_demand(
        daily_sales, planning_days, on_floor, inbound_cases
    )
    additional_needed = calculate_additional_cases_needed(remaining_demand)
    pallets = calculate_pallets_required(additional_needed, cases_per_pallet)

    required_delivery = oos_date
    earlier_delivery = calculate_earlier_delivery_required(
        inbound_arrival_date, required_delivery
    )

    return {
        'item_code': item_code,
        'on_floor_cases': on_floor,
        'daily_sales': daily_sales,
        'current_days_on_hand': days_on_hand,
        'projected_oos_date': oos_date,
        'inbound_cases': inbound_cases,
        'delivered_days_on_hand': delivered_doh,
        'remaining_demand_cases': remaining_demand,
        'additional_cases_needed': additional_needed,
        'pallets_required': pallets,
        'required_delivery_date': required_delivery,
        'earlier_delivery_required': earlier_delivery
    }