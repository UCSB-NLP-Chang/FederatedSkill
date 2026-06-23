#!/usr/bin/env python3
"""Generates a constraint-aware production schedule in Excel from a JSON config."""
import argparse
import json
import sys
from datetime import date, timedelta
from openpyxl import Workbook

def get_workdays(start, end, holidays):
    """Returns list of workdays (Mon-Fri) excluding holidays."""
    days = []
    curr = start
    while curr <= end:
        if curr.weekday() < 5 and curr not in holidays:
            days.append(curr)
        curr += timedelta(days=1)
    return days

def distribute_demand(total, days_count, capacity_limit, start_offset=0):
    """Distributes demand evenly across days respecting capacity limit."""
    if days_count <= 0 or total <= 0:
        return [0] * days_count
    available_days = max(0, days_count - start_offset)
    if available_days == 0:
        return [0] * days_count
    base = min(total // available_days, capacity_limit)
    rem = total - (base * available_days)
    schedule = [0] * start_offset + [base] * available_days
    for i in range(start_offset, len(schedule)):
        if rem <= 0: break
        add = min(rem, capacity_limit - schedule[i])
        schedule[i] += add
        rem -= add
    return schedule

def main():
    parser = argparse.ArgumentParser(description="Generate production schedule")
    parser.add_argument("config", help="Path to JSON config file")
    parser.add_argument("output", help="Output Excel path")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    start = date.fromisoformat(cfg["start_date"])
    end = date.fromisoformat(cfg["end_date"])
    holidays = [date.fromisoformat(d) for d in cfg.get("holidays", [])]
    workdays = get_workdays(start, end, holidays)

    wb = Workbook()
    for sheet_name, scenario in cfg["scenarios"].items():
        ws = wb.create_sheet(title=sheet_name)
        ws.append(["Date", "Web Prod", "DB Prod", "Net Prod", "Web Open", "DB Open", "Net Open", "Total Prod"])

        web_open = scenario.get("initial_web_open", 0)
        db_open = scenario.get("initial_db_open", 0)
        net_open = scenario.get("initial_net_open", 0)

        # Example: distribute demand evenly. Replace with scenario-specific logic.
        web_sched = distribute_demand(scenario.get("web_demand", 0), len(workdays), scenario.get("web_cap", 100))
        db_sched = distribute_demand(scenario.get("db_demand", 0), len(workdays), scenario.get("db_cap", 100))
        net_sched = distribute_demand(scenario.get("net_demand", 0), len(workdays), scenario.get("net_cap", 100))

        for i, d in enumerate(workdays):
            w, db, n = web_sched[i], db_sched[i], net_sched[i]
            ws.append([d, w, db, n, web_open, db_open, net_open, w + db + n])
            web_open = max(0, web_open - w)
            db_open = max(0, db_open - db)
            net_open = max(0, net_open - n)

    wb.save(args.output)
    print(f"Saved {args.output}")

if __name__ == "__main__":
    main()
