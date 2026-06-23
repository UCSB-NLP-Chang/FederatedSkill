#!/usr/bin/env python3
"""Deterministic queue capacity planner with step-down staffing rules.

Usage: python3 queue_simulator.py <input_excel> <output_excel> <output_summary>

IMPORTANT: Do NOT rewrite this script. Modify only the CONFIG dictionary below
for your scenario. The simulation logic is correct and reusable across domains.

See references/simulation_rules.md for parameter guidance and domain adaptation.
"""
import sys
import openpyxl

# ── CONFIGURATION: Edit this block for your scenario ──────────────────────
# See references/simulation_rules.md for how to calculate these values.
CONFIG = {
    # Initial backlog/past-due at start of simulation
    "initial_backlog": 407.0,

    # Capacity and overtime for each staffing level
    "capacity_6_days": 168,
    "overtime_6_days": 16,
    "capacity_5_days": 140,
    "overtime_5_days": 8,
    "capacity_4_days": 112,
    "overtime_4_days": 0,

    # Demand threshold: if demand > this, use 5 days instead of 4
    # Typically equals capacity_4_days
    "demand_threshold_5_days": 112,

    # Row indices (1-based) in input Excel for horizontal week layout
    "row_weeks": 2,
    "row_demand": 4,

    # Output column headers (exactly 7, in this order)
    "headers": [
        "Week",
        "On-Call Days",
        "Forecast Alert Load (Analyst Hrs)",
        "Weekly Triage Capacity (Analyst Hrs)",
        "Start-of-Week Alert Queue (Analyst Hrs)",
        "End-of-Week Alert Queue/Buffer (Analyst Hrs)",
        "Burnout Overtime Hours"
    ],

    # Summary template: {w5} = first 5-day week, {w4} = first 4-day week
    "summary_template": (
        "The backlog catches up at week {w5} (first 5-day week) after burning down overtime. "
        "Operations normalize at week {w4} (first 4-day week), ending the catch-up phase. "
        "Remaining weeks alternate between standard and reduced staffing based on demand fluctuations."
    )
}
# ── End of configuration ──────────────────────────────────────────────────


def simulate(input_path, out_excel, out_summary):
    wb_in = openpyxl.load_workbook(input_path)
    ws_in = wb_in.active

    # Extract weeks and demands from configured rows
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
            CONFIG["headers"][0]: week,
            CONFIG["headers"][1]: current_days,
            CONFIG["headers"][2]: demand,
            CONFIG["headers"][3]: cap,
            CONFIG["headers"][4]: max(0, start_queue),
            CONFIG["headers"][5]: end_queue,
            CONFIG["headers"][6]: ot
        })

        start_queue = end_queue

    # Write Excel
    wb_out = openpyxl.Workbook()
    ws_out = wb_out.active
    ws_out.title = "Plan"
    headers = CONFIG["headers"]
    ws_out.append(headers)
    for r in rows:
        ws_out.append([r[h] for h in headers])
    wb_out.save(out_excel)

    # Write Summary
    summary_text = CONFIG["summary_template"].format(w5=first_5, w4=first_4)
    with open(out_summary, "w") as f:
        f.write(f"First_Week_5_Days: {first_5}\n")
        f.write(f"First_Week_4_Days: {first_4}\n")
        f.write(f"Summary: {summary_text}\n")

    print(f"Plan saved to {out_excel}")
    print(f"Summary saved to {out_summary}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 queue_simulator.py <input_excel> <output_excel> <output_summary>")
        print("Note: Modify CONFIG in script for your scenario. See references/simulation_rules.md")
        sys.exit(1)
    simulate(sys.argv[1], sys.argv[2], sys.argv[3])
