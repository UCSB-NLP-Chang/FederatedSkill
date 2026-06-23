#!/usr/bin/env python3
"""
Calculate production catch-up schedule stepping down from 6-day to 4-day weeks.

Usage:
    python3 calculate_catchup.py <excel_path> <demand_label> <backlog_source>

Args:
    excel_path: Path to capacity Excel file
    demand_label: Row label to find demand (e.g., 'MIG weld Demand Total')
    backlog_source: Either a row label (e.g., 'MIG PLT 2') or numeric value for initial backlog

Example:
    python3 calculate_catchup.py capacity.xlsx 'MIG weld Demand Total' 'MIG PLT 2'
"""

import pandas as pd
import sys
from pathlib import Path

def extract_numeric_data(df, header_row_idx=3):
    """Extract weeks and valid numeric mask, filtering out 'Total' columns."""
    weeks = pd.to_numeric(df.iloc[header_row_idx, 1:], errors='coerce')
    valid_mask = weeks.notna()
    return weeks[valid_mask].astype(int), valid_mask

def get_initial_backlog(df, valid_mask, backlog_source):
    """Extract initial backlog from row label or use provided float."""
    if isinstance(backlog_source, (int, float)):
        return float(backlog_source)

    backlog_row = df[df[0] == backlog_source].iloc[0, 1:][valid_mask]
    return float(backlog_row.iloc[0])

def calculate_schedule(weeks, demand, initial_backlog,
                       capacity_rules=None, step_down_threshold=120):
    """
    Calculate catch-up schedule.

    Args:
        weeks: Series of week numbers
        demand: Array of demand values
        initial_backlog: Starting past due hours
        capacity_rules: Dict of {days: (capacity, ot_hours)}, defaults to standard
        step_down_threshold: Demand threshold for 4-day week transition
    """
    if capacity_rules is None:
        capacity_rules = {
            6: (180, 20),  # (capacity, overtime)
            5: (150, 10),
            4: (120, 0)
        }

    results = []
    past_due = initial_backlog
    current_days = 6
    weeks_at_5_days = 0

    for i, (week, dem) in enumerate(zip(weeks, demand)):
        cap, ot = capacity_rules[current_days]

        # Calculate flow
        start_past = past_due if past_due > 0 else 0
        end_backlog = start_past + dem - cap

        # Store raw float values - no rounding
        results.append({
            'Week': int(week),
            'Days Worked': current_days,
            'Scheduled Demand (Std Hrs)': dem,
            'Weekly Capacity (Std Hrs)': cap,
            'Start of Week Past Due (Std Hrs)': start_past,
            'End of Week Backlog/Buffer (Std Hrs)': end_backlog,
            'Overtime Hours': ot
        })

        past_due = end_backlog

        # Transition logic
        if current_days == 6 and past_due <= 0:
            current_days = 5
            weeks_at_5_days = 1
        elif current_days == 5:
            if past_due > 0:
                # Backlog resurfaced, return to 6 days
                current_days = 6
                weeks_at_5_days = 0
            elif dem < step_down_threshold and weeks_at_5_days >= 1:
                # Sustained low demand, step to 4 days
                current_days = 4
            else:
                weeks_at_5_days += 1
        # Once at 4 days, stay there (or add logic to step up if needed)

    return pd.DataFrame(results)

def generate_summary(df, capacity_rules):
    """Generate summary statistics from results."""
    first_5 = df[df['Days Worked'] == 5]['Week'].min()
    first_4 = df[df['Days Worked'] == 4]['Week'].min()

    # Check if we ever went back to 6 days after stepping down
    reverts = df[(df['Days Worked'] == 6) & (df['Week'] > first_5)]

    summary = f"First_Week_5_Days: {int(first_5) if pd.notna(first_5) else 'N/A'}\n"
    summary += f"First_Week_4_Days: {int(first_4) if pd.notna(first_4) else 'N/A'}\n"

    if not reverts.empty:
        summary += f"Note: Schedule reverts to 6 days in weeks {list(reverts['Week'])} due to demand spikes\n"

    return summary

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 calculate_catchup.py <excel> <demand_label> <backlog_source>")
        sys.exit(1)

    excel_path = sys.argv[1]
    demand_label = sys.argv[2]
    backlog_source = sys.argv[3]

    # Try to convert backlog_source to float, else treat as label
    try:
        backlog_source = float(backlog_source)
    except ValueError:
        pass

    # Read data
    df = pd.read_excel(excel_path, header=None)
    weeks, valid_mask = extract_numeric_data(df)

    # Get demand
    demand_row = df[df[0] == demand_label].iloc[0, 1:][valid_mask]
    demand = pd.to_numeric(demand_row, errors='coerce').values

    # Get initial backlog
    initial_backlog = get_initial_backlog(df, valid_mask, backlog_source)

    # Calculate
    results_df = calculate_schedule(weeks, demand, initial_backlog)

    # Output
    results_df.to_excel('catch_up_plan.xlsx', index=False)

    summary = generate_summary(results_df, {6: (180, 20), 5: (150, 10), 4: (120, 0)})
    with open('catch_up_summary.txt', 'w') as f:
        f.write(summary)

    print(f"Created catch_up_plan.xlsx with {len(results_df)} weeks")
    print(f"Summary:\n{summary}")

if __name__ == '__main__':
    main()