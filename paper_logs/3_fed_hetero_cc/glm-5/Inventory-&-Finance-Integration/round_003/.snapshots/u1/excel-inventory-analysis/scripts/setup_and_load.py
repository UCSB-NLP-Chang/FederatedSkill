#!/usr/bin/env python3
"""Robust Excel loader for resource planning analysis tasks."""
import subprocess
import sys
from datetime import datetime, date, timedelta
import math

def ensure_openpyxl():
    """Install openpyxl if missing, handling externally-managed environments."""
    try:
        import openpyxl
        return openpyxl
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "-q", "--break-system-packages"])
        import openpyxl
        return openpyxl

def parse_date(val):
    """Normalize Excel cell values to date objects.

    CRITICAL: Excel dates may be datetime objects OR strings. Always use this
    function—never assume datetime type. Handles:
    - datetime.datetime -> date
    - datetime.date -> date
    - string 'YYYY-MM-DD' -> date
    - string 'MM/DD/YYYY' -> date
    - string 'DD-Mon-YYYY' -> date
    """
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return val

def extract_formula_multiplier(cell_val):
    """Extract numeric multiplier from formula strings like '=80*C2' or '=24*A1'."""
    if isinstance(cell_val, str) and cell_val.startswith("="):
        parts = cell_val.replace("=", "").replace("*", " ").split()
        for p in parts:
            try:
                return float(p)
            except ValueError:
                continue
    return None

def parse_date_cell(ws, cell_ref, default=None):
    """Safely parse a date from a worksheet cell, handling string/datetime types."""
    val = ws[cell_ref].value
    if val is None:
        return default
    parsed = parse_date(val)
    return parsed if isinstance(parsed, date) else default


def calculate_coverage_gap(current_units, daily_rate, as_of_date, horizon_end,
                           inbound_items, unit_multiplier):
    """Calculate resource planning gap metrics.

    Args:
        current_units: Current stock/hours available
        daily_rate: Daily consumption/requirement rate
        as_of_date: Analysis start date (date object)
        horizon_end: Planning horizon end date (date object)
        inbound_items: List of dicts with 'date' (date) and 'units' (numeric)
        unit_multiplier: Conversion factor (cases/pallet or hours/shift)

    Returns:
        dict with coverage_days, shortfall_date, inbound_units,
        additional_units_needed, output_units_required, required_date, etc.
    """
    remaining_days = (horizon_end - as_of_date).days

    if daily_rate == 0:
        coverage_days = None
        shortfall_date = None
    else:
        coverage_days = current_units / daily_rate
        shortfall_date = as_of_date + timedelta(days=coverage_days)

    # Sum inbound within horizon
    inbound_within_horizon = sum(
        item['units'] for item in inbound_items
        if item['date'] <= horizon_end
    )

    remaining_demand = daily_rate * remaining_days
    total_available = current_units + inbound_within_horizon
    additional_needed = max(0, remaining_demand - total_available)

    output_units = math.ceil(additional_needed / unit_multiplier) if unit_multiplier else 0
    rounding_applied = output_units > 0

    if daily_rate > 0 and additional_needed > 0:
        required_date = as_of_date + timedelta(days=additional_needed / daily_rate)
    else:
        required_date = None

    # Find earliest scheduled inbound
    earliest_inbound = min((item['date'] for item in inbound_items), default=None)
    earlier_required = (required_date is not None and earliest_inbound is not None
                       and required_date < earliest_inbound)

    return {
        'coverage_days': coverage_days,
        'shortfall_date': shortfall_date,
        'inbound_within_horizon': inbound_within_horizon,
        'remaining_demand': remaining_demand,
        'additional_needed': additional_needed,
        'output_units_required': output_units,
        'rounding_applied': rounding_applied,
        'required_date': required_date,
        'earliest_inbound': earliest_inbound,
        'earlier_required': earlier_required
    }


if __name__ == "__main__":
    # Self-test
    openpyxl = ensure_openpyxl()
    print("openpyxl ready:", openpyxl.__version__)

    # Test date parsing
    assert parse_date(datetime(2025, 8, 5)) == date(2025, 8, 5)
    assert parse_date("2025-08-05") == date(2025, 8, 5)
    assert parse_date("08/05/2025") == date(2025, 8, 5)
    print("Date parsing: OK")

    # Test formula extraction
    assert extract_formula_multiplier("=24*A2") == 24.0
    assert extract_formula_multiplier("=80*C2") == 80.0
    print("Formula extraction: OK")

    # Test gap calculation
    result = calculate_coverage_gap(
        current_units=320, daily_rate=80,
        as_of_date=date(2025, 8, 5), horizon_end=date(2025, 8, 31),
        inbound_items=[
            {'date': date(2025, 8, 7), 'units': 96},
            {'date': date(2025, 8, 20), 'units': 48}
        ],
        unit_multiplier=24
    )
    assert result['coverage_days'] == 4.0
    assert result['output_units_required'] == 68
    print("Gap calculation: OK")

    print("\nAll tests passed!")
