#!/usr/bin/env python3
"""Deterministic queue capacity planner with step-down staffing rules.

Usage: python3 queue_simulator.py <input_excel> <output_excel> <output_summary>

Adjust CONFIG constants if task parameters differ from the default SOC scenario.
"""
import sys
import openpyxl

CONFIG = {
    "initial_backlog": 407.0,
    "capacity_6_days": 168,
    "overtime_6_days": 16,
    "capacity_5_days": 140,
    "overtime_5_days": 8,
    "capacity_4_days": 112,
    "overtime_4_days": 0,
    "demand_threshold_5_days": 112,
    # Row indices (1-based) for standard input layout
    "row_weeks": 2,
    "row_demand": 4
}

def simulate(input_path, out_excel, out_summary):
    wb_in = openpyxl.load_workbook(input_path)
    ws_in = wb_in.active

    weeks = [c.value for c in ws_in[CONFIG["row_weeks"]] if c.value is not None and isinstance(c.value, (int, float))]
    demands = [c.value for c in ws_in[CONFIG["row_demand"]] if c.value is not None]

    rows = []
    current_days = 6
    start_queue = CONFIG["initial_backlog"]
    first_5 = None
    first_4 = None

    for i, week in enumerate(weeks):
        demand = demands[i]

        if current_days == 6:
            cap, ot = CONFIG["capacity_6_days"], CONFIG["overtime_6_days"]
        elif current_days == 5:
            cap, ot = CONFIG["capacity_5_days"], CONFIG["overtime_5_days"]
        else:
            cap, ot = CONFIG["capacity_4_days"], CONFIG["overtime_4_days"]

        end_queue = start_queue + demand - cap

        # Transition logic
        if current_days == 6 and end_queue <= 0:
            current_days = 5 if demand > CONFIG["demand_threshold_5_days"] else 4
        elif current_days == 4 and demand > CONFIG["demand_threshold_5_days"]:
            current_days = 5

        if current_days == 5 and first_5 is None:
            first_5 = week
        if current_days == 4 and first_4 is None:
            first_4 = week

        rows.append({
            "Week": week,
            "On-Call Days": current_days,
            "Forecast Alert Load (Analyst Hr)": demand,
            "Weekly Triage Capacity (Analyst Hr)": cap,
            "Start-of-Week Alert Queue (Analyst Hr)": max(0, start_queue),
            "End-of-Week Alert Queue/Buffer (Analyst Hr)": end_queue,
            "Burnout Overtime Hours": ot
        })

        start_queue = end_queue

    # Write Excel
    wb_out = openpyxl.Workbook()
    ws_out = wb_out.active
    ws_out.title = "Plan"
    headers = list(rows[0].keys())
    ws_out.append(headers)
    for r in rows:
        ws_out.append([r[h] for h in headers])
    wb_out.save(out_excel)

    # Write Summary
    summary_text = (
        f"The backlog catches up at week {first_5} (first 5-day week) after burning down overtime. "
        f"Operations normalize at week {first_4} (first 4-day week), ending the catch-up phase. "
        f"Remaining weeks alternate between standard and reduced staffing based on demand fluctuations."
    )
    with open(out_summary, "w") as f:
        f.write(f"First_Week_5_Days: {first_5}\n")
        f.write(f"First_Week_4_Days: {first_4}\n")
        f.write(f"Summary: {summary_text}\n")

    print(f"Plan saved to {out_excel}")
    print(f"Summary saved to {out_summary}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 queue_simulator.py <input_excel> <output_excel> <output_summary>")
        sys.exit(1)
    simulate(sys.argv[1], sys.argv[2], sys.argv[3])