#!/usr/bin/env python3
"""
Calculate catch-up capacity plan with step-down scheduling.
Policy: 6-day weeks until backlog cleared, then 5-day, then 4-day.
"""

import sys
import json

# Capacity constants (30 hrs/day base)
CAPACITY = {
    4: 120,   # 4 days
    5: 150,   # 5 days  
    6: 180    # 6 days
}

OVERTIME = {
    4: 0,
    5: 10,
    6: 20
}

def calculate_catchup(weeks_demand, initial_backlog):
    """
    Calculate week-by-week schedule.
    
    Args:
        weeks_demand: list of (week, demand) tuples
        initial_backlog: starting backlog hours
    
    Returns:
        dict with 'schedule', 'first_week_5_days', 'first_week_4_days', 'total_overtime_weeks'
    """
    schedule = []
    backlog = round(float(initial_backlog), 2)
    first_5 = None
    first_4 = None
    overtime_weeks = 0
    
    for week, demand in weeks_demand:
        demand = round(float(demand), 2)
        
        # Determine days based on state
        if backlog > 0:
            days = 6  # Maximum capacity to clear backlog
        elif first_5 is None:
            days = 5  # First week after clearing
        else:
            days = 4  # Stepped down
        
        capacity = CAPACITY[days]
        overtime = OVERTIME[days]
        
        start_past_due = round(backlog, 2) if backlog > 0 else 0.0
        
        # Calculate new backlog
        total_capacity = capacity + overtime
        new_backlog = round(backlog + demand - total_capacity, 2)
        
        # Record transitions
        if days == 5 and first_5 is None:
            first_5 = week
        if days == 4 and first_4 is None:
            first_4 = week
        
        if overtime > 0:
            overtime_weeks += 1
        
        schedule.append({
            'week': week,
            'days_worked': days,
            'scheduled_demand': demand,
            'weekly_capacity': capacity,
            'start_past_due': start_past_due,
            'end_backlog': round(new_backlog, 2),
            'overtime_hours': overtime
        })
        
        backlog = new_backlog
    
    return {
        'schedule': schedule,
        'first_week_5_days': first_5,
        'first_week_4_days': first_4,
        'total_overtime_weeks': overtime_weeks
    }

def format_summary(result, initial_backlog):
    """Format summary with constraints: 60 words max, 3 sentences max."""
    first_5 = result['first_week_5_days']
    first_4 = result['first_week_4_days']
    ot_weeks = result['total_overtime_weeks']
    
    summary = (
        f"With {int(round(initial_backlog))} hours initial backlog, "
        f"welding runs 6-day weeks until Week {first_5}, then steps down to 5 days, "
        f"and 4 days in Week {first_4}. Backlog clears by Week {first_4}. "
        f"{ot_weeks} overtime weeks required."
    )
    
    return summary

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: catchup_calculator.py <json_weeks_demand> <initial_backlog>", file=sys.stderr)
        sys.exit(1)
    
    weeks_demand = json.loads(sys.argv[1])
    initial_backlog = float(sys.argv[2])
    
    result = calculate_catchup(weeks_demand, initial_backlog)
    result['summary'] = format_summary(result, initial_backlog)
    print(json.dumps(result, indent=2))
