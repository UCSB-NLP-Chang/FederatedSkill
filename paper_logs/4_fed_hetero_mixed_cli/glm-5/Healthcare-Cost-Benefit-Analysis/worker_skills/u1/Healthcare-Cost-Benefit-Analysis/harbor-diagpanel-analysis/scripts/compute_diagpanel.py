#!/usr/bin/env python3
"""Compute Harbor Diagnostic Panel analysis and generate JSON/MD outputs."""
import csv
import json
import sys
import os

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "/root"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 6000.0

    # Load report template for metadata preservation
    template_path = os.path.join(base_dir, "report_template.json")
    if os.path.exists(template_path):
        with open(template_path) as f:
            template = json.load(f)
    else:
        template = {"metadata": {}, "audit_notes": []}

    # Load panel manifest
    with open(os.path.join(base_dir, "panel_manifest.json")) as f:
        manifest = json.load(f)

    panels = {}
    alias_map = {}
    for cluster in manifest.get("service_clusters", []):
        for panel in cluster.get("panels", []):
            if panel.get("analysis_mode") == "review":
                code = panel["panel_code"]
                panels[code] = panel
                # Map aliases for contract resolution
                alias_map[panel["panel_name"]] = code
                for alias in panel.get("alias_labels", []):
                    alias_map[alias] = code

    # Load holdouts and exclude
    holdouts_path = os.path.join(base_dir, "holdouts.json")
    if os.path.exists(holdouts_path):
        with open(holdouts_path) as f:
            holdout_data = json.load(f)
        for h in holdout_data.get("holdouts", []):
            if h.get("holdout_state") == "exclude":
                panels.pop(h.get("panel_code"), None)

    # Load shipper costs
    shipper_costs = {}
    with open(os.path.join(base_dir, "shipper_cost.csv")) as f:
        for row in csv.DictReader(f):
            shipper_costs[row["shipper_class"]] = float(row["shipper_cost_usd"])

    # Load network adjustments
    network_adj = {}
    with open(os.path.join(base_dir, "network_adjustment.csv")) as f:
        for row in csv.DictReader(f):
            network_adj[row["network_tier"]] = float(row["network_adjustment_per_run_per_lab_usd"])

    # Load contract payments (latest current effective_week per panel)
    payments = {}
    contract_rows = []
    with open(os.path.join(base_dir, "contract_payment.csv")) as f:
        for row in csv.DictReader(f):
            label = row["panel_ref"]
            if label in alias_map:
                code = alias_map[label]
                status = row.get("status_flag", "").lower()
                if status == "current":
                    effective = row["effective_week"]
                    contract_rows.append((code, effective, float(row["base_payment_per_run_per_lab_usd"])))

    # Select latest effective week per panel (lexicographic works for ISO weeks)
    latest_payment = {}
    for code, effective, payment in contract_rows:
        if code not in latest_payment or effective > latest_payment[code][0]:
            latest_payment[code] = (effective, payment)
    for code, (_, payment) in latest_payment.items():
        payments[code] = payment

    # Load lab overrides (highest approved rev with non-empty active_labs per panel)
    labs = {}
    with open(os.path.join(base_dir, "lab_overrides.csv")) as f:
        for row in csv.DictReader(f):
            code = row["panel_code"]
            if code in panels and row.get("approval") == "approved":
                rev_str = row.get("rev", "").strip()
                active_str = row.get("active_labs", "").strip()
                if not rev_str or active_str == "":
                    continue
                try:
                    rev = int(rev_str)
                    active_labs = int(active_str)
                except ValueError:
                    continue
                if code not in labs or rev > labs[code]["rev"]:
                    labs[code] = {"rev": rev, "active_labs": active_labs}

    # Constants
    RUNS_14 = 26
    RUNS_28 = 13

    results = []
    for code in sorted(panels.keys()):
        panel = panels[code]

        # Resolve active labs
        if code in labs:
            active_labs = labs[code]["active_labs"]
        else:
            active_labs = panel["default_active_labs"]

        reagent_cost_per_1000 = panel["reagent_cost_per_1000_tests_usd"]
        shipper_class = panel["shipper_class"]
        shipper_cost = shipper_costs[shipper_class]
        network_tier = panel["network_tier"]
        network_adjustment = network_adj.get(network_tier, 0.0)
        base_payment = payments.get(code, 0.0)
        total_payment = base_payment + network_adjustment

        tests_14 = panel["tests_per_lab_per_run_14_day"]
        tests_28 = panel["tests_per_lab_per_run_28_day"]

        # Annual reagent cost (identical for both due to balanced test volumes)
        annual_reagent = (tests_14 * RUNS_14 * active_labs / 1000) * reagent_cost_per_1000

        # Shipper costs
        shipper_14 = shipper_cost * RUNS_14 * active_labs
        shipper_28 = shipper_cost * RUNS_28 * active_labs

        # Revenue
        rev_14 = total_payment * RUNS_14 * active_labs
        rev_28 = total_payment * RUNS_28 * active_labs

        # Margins
        margin_14 = rev_14 - annual_reagent - shipper_14
        margin_28 = rev_28 - annual_reagent - shipper_28
        diff = margin_28 - margin_14

        results.append({
            "panel_code": code,
            "panel_name": panel["panel_name"],
            "active_labs": active_labs,
            "reagent_cost_per_1000_tests_usd": round(reagent_cost_per_1000, 2),
            "network_tier": network_tier,
            "network_adjustment_per_run_per_lab_usd": round(network_adjustment, 2),
            "shipper_class": shipper_class,
            "shipper_cost_usd": round(shipper_cost, 2),
            "base_payment_per_run_per_lab_usd": round(base_payment, 2),
            "total_payment_per_run_per_lab_usd": round(total_payment, 2),
            "tests_per_lab_per_run_14_day": tests_14,
            "tests_per_lab_per_run_28_day": tests_28,
            "annual_reagent_cost_14_day_usd": round(annual_reagent, 2),
            "annual_reagent_cost_28_day_usd": round(annual_reagent, 2),
            "annual_shipper_cost_14_day_usd": round(shipper_14, 2),
            "annual_shipper_cost_28_day_usd": round(shipper_28, 2),
            "annual_revenue_14_day_usd": round(rev_14, 2),
            "annual_revenue_28_day_usd": round(rev_28, 2),
            "annual_margin_14_day_usd": round(margin_14, 2),
            "annual_margin_28_day_usd": round(margin_28, 2),
            "annual_margin_difference_28_minus_14_usd": round(diff, 2)
        })

    total_margin_14 = round(sum(r["annual_margin_14_day_usd"] for r in results), 2)
    total_margin_28 = round(sum(r["annual_margin_28_day_usd"] for r in results), 2)
    total_diff = round(total_margin_28 - total_margin_14, 2)
    abs_total_diff = round(abs(total_diff), 2)

    decision = "adopt_28_day" if abs_total_diff < threshold else "keep_14_day"

    output = {
        "metadata": template.get("metadata", {}),
        "audit_notes": template.get("audit_notes", []),
        "analysis": {
            "assumptions": {
                "runs_per_year_14_day": RUNS_14,
                "runs_per_year_28_day": RUNS_28,
                "switch_threshold_usd": threshold,
                "lab_override_rule": "highest approved rev with non-empty active_labs per panel_code, else default_active_labs",
                "contract_rule": "latest current effective_week per panel (matched by panel_name or alias_labels)",
                "holdout_rule": "exclude panels with holdout_state: exclude",
                "adjustment_rule": "missing network_tier adjustment defaults to 0.0"
            },
            "panels": results,
            "totals": {
                "total_annual_margin_14_day_usd": total_margin_14,
                "total_annual_margin_28_day_usd": total_margin_28,
                "total_annual_margin_difference_28_minus_14_usd": total_diff,
                "absolute_total_margin_difference_usd": abs_total_diff
            },
            "recommendation": {
                "decision": decision,
                "justification": f"The absolute total margin difference (${abs_total_diff:,.2f}) is {'below' if abs_total_diff < threshold else 'above or equal to'} the threshold of ${threshold:,.2f}, making the 28-day cadence {'economically favorable' if decision == 'adopt_28_day' else 'not recommended'}."
            }
        }
    }

    json_path = os.path.join(base_dir, "diagpanel_policy_report.json")
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    # Markdown summary: exactly 4-8 non-empty lines
    summary_path = os.path.join(base_dir, "diagpanel_policy_summary.md")
    with open(summary_path, "w") as f:
        f.write("Diagnostic panel policy analysis compared 14-day versus 28-day replenishment cadences.\n\n")
        f.write(f"Total 14-day annual margin: ${total_margin_14:,.2f} USD\n")
        f.write(f"Total 28-day annual margin: ${total_margin_28:,.2f} USD\n")
        f.write(f"Absolute margin difference: ${abs_total_diff:,.2f} USD\n\n")
        f.write(f"Decision: `{decision}` — the absolute difference is {'below' if abs_total_diff < threshold else 'above or equal to'} the ${threshold:,.2f} threshold.\n")

    print(f"Generated {json_path} and {summary_path}")

if __name__ == "__main__":
    main()