#!/usr/bin/env python3
"""
Extract week/demand data from JSON with automatic structure detection and priority filtering.
Handles chemical/reactor style JSON with duplicate phases and priority levels.

Priority ranking (lower = higher priority): HIGH < MED < NORMAL < LOW
"""

import json
import sys

PRIORITY_RANK = {
    'HIGH': 0,
    'MED': 1,
    'MEDIUM': 1,
    'NORMAL': 2,
    'LOW': 3
}

def get_priority_rank(priority):
    """Get numeric priority rank, defaulting to lowest."""
    return PRIORITY_RANK.get(str(priority).upper(), 99)

def extract_json_demand(filepath):
    """
    Extract (week, demand) pairs from JSON file.
    
    Expected JSON format:
    [
      {"week": 10, "data": {"demand_per_week": 253.06}, "priority": "HIGH"},
      {"week": 10, "data": {"demand_per_week": 310.0}, "priority": "LOW"},  # duplicate
      ...
    ]
    
    Returns: list of (week, demand) tuples, sorted by week
    """
    with open(filepath) as f:
        raw = json.load(f)
    
    phases = {}  # week -> {'demand': value, 'priority': str}
    
    for entry in raw:
        week = entry.get('week')
        if week is None:
            continue
        
        # Extract demand, handling null/None
        data = entry.get('data', {})
        demand = data.get('demand_per_week') if isinstance(data, dict) else None
        
        if demand is None:
            continue  # Skip null demands
        
        priority = entry.get('priority', 'NORMAL')
        
        # Keep if first occurrence or higher priority
        if week not in phases:
            phases[week] = {'demand': float(demand), 'priority': priority}
        elif get_priority_rank(priority) < get_priority_rank(phases[week]['priority']):
            phases[week] = {'demand': float(demand), 'priority': priority}
    
    # Return sorted list
    result = [(w, phases[w]['demand']) for w in sorted(phases.keys())]
    return result

def extract_initial_condition(filepath):
    """
    Extract initial condition from task description file if present.
    Looks for patterns like: "Start of Phase Past Due + Scheduled Demand = 1453.06"
    
    Returns: (initial_backlog, first_week_demand) or (None, None) if not found
    """
    try:
        with open(filepath) as f:
            content = f.read()
    except (FileNotFoundError, json.JSONDecodeError):
        return None, None
    
    # Simple pattern matching for common initial condition formats
    import re
    # Pattern: "X + Y = Z" or "X + Scheduled Demand = Y"
    match = re.search(r'Start of \w+ Past Due.*?(?:\+|plus).*?(\d+\.?\d*).*?=\s*(\d+\.?\d*)', content, re.IGNORECASE)
    if match:
        first_demand = float(match.group(1))
        total = float(match.group(2))
        return total - first_demand, first_demand
    
    return None, None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: extract_json_demand.py <json_file>", file=sys.stderr)
        print("\nOutputs JSON array of [week, demand] pairs, sorted by week.", file=sys.stderr)
        sys.exit(1)
    
    filepath = sys.argv[1]
    result = extract_json_demand(filepath)
    print(json.dumps(result))
