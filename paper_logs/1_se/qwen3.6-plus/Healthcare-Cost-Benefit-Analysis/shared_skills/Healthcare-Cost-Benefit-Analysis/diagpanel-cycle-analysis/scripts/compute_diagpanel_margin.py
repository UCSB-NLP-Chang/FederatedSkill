#!/usr/bin/env python3
import argparse
import csv
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Compute diagnostic panel dispatch cycle margin analysis.")
    parser.add_argument("--manifest", required=True, help="Path to panel_manifest.json")
    parser.add_argument("--shipper", required=True, help="Path to shipper_cost.csv")
    parser.add_argument("--contract", required=True, help="Path to contract_terms.csv")
    parser.add_argument("--adjustments", required=True, help="Path to network_adjustments.csv")
    parser.add_argument("--overrides", required=True, help="Path to lab_capacity_overrides.csv")
    parser.add_argument("--holdouts", required=True, help="Path to holdouts.json")
    parser.add_argument("--template", required=True, help="Path to report_template.json")
    parser.add_argument("--threshold", type=float, default=6000.0, help="Decision threshold USD")
    parser.add_argument("--out-json", default="diagpanel_policy_report.json")
    parser.add_argument("--out-md", default="diagpanel_policy_summary.md")
    args = parser.parse_args()

    def load_csv(path):
        with open(path, newline='') as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters='\t,')
            return list(csv.DictReader(f, dialect=dialect))

    with open(args.manifest) as f:
        manifest = json.load(f)

    with open(args.holdouts) as f:
        holdouts = json.load(f)

    with open(args.template) as f:
        template = json.load(f)

    # Build holdout exclusion set
    exclude_ids = set()
    for h in holdouts.get("holdouts", []):
        if h.get("holdout_state") == "exclude":
            exclude_ids.add(h["panel_code"])

    panels = {}
    alias_to_code = {}
    for cluster in manifest.get("service_clusters", []):
        for p in cluster.get("panels", []):
            if p.get("analysis_mode") == "review" and p["panel_code"] not in exclude_ids:
                code = p["panel_code"]
                panels[code] = {
                    "name": p["panel_name"],
                    "reagent_cost": p["reagent_cost_per_1000_tests_usd"],
                    "network_tier": p["network_tier"],
                    "shipper_class": p["shipper_class"],
                    "tests_14": p["tests_per_lab_per_run_14_day"],
                    "tests_28": p["tests_per_lab_per_run_28_day"],
                    "default_labs": p["default_active_labs"]
                }
                for alias in p.get("alias_labels", []):
                    alias_to_code[alias] = code

    # Load shipper costs
    shipper_costs = {}
    for row in load_csv(args.shipper):
        shipper_costs[row["shipper_class"]] = float(row["shipper_cost_usd"])

    # Load contract terms
    contracts = {}
    for row in load_csv(args.contract):
        if row.get("status_flag", "").strip().lower() == "current":
            ref = row["panel_ref"]
            if ref in alias_to_code:
                code = alias_to_code[ref]
                week = row["effective_week"]
                pay = float(row["base_payment_per_run_per_lab_usd"])
                if code not in contracts or week > contracts[code]["week"]:
                    contracts[code] = {"week": week, "payment": pay}

    # Load network adjustments
    adjustments = {}
    for row in load_csv(args.adjustments):
        adjustments[row["network_tier"]] = float(row["network_adjustment_per_run_per_lab_usd"])

    # Load overrides
    overrides = {}
    for row in load_csv(args.overrides):
        if row.get("approval", "").strip().lower() == "approved":
            code = row["panel_code"]
            rev_str = row.get("rev", "").strip()
            rev = int(rev_str) if rev_str else 0
            labs_str = row.get("active_labs", "").strip()
            labs = int(labs_str) if labs_str else None
            if labs is not None:
                if code not in overrides or rev > overrides[code]["rev"]:
                    overrides[code] = {"rev": rev, "labs": labs}

    RUNS_14 = 26
    RUNS_28 = 13

    results = []
    total_m14 = 0.0
    total_m28 = 0.0

    for code, p in panels.items():
        labs = overrides.get(code, {}).get("labs", p["default_labs"])
        shipper_cost = shipper_costs.get(p["shipper_class"], 0.0)
        base_pay = contracts.get(code, {}).get("payment", 0.0)
        net_adj = adjustments.get(p["network_tier"], 0.0)
        total_pay = base_pay + net_adj

        reagent_annual = (p["reagent_cost"] / 1000.0) * p["tests_14"] * RUNS_14 * labs
        shipper_14 = shipper_cost * RUNS_14 * labs
        shipper_28 = shipper_cost * RUNS_28 * labs
        rev_14 = total_pay * RUNS_14 * labs
        rev_28 = total_pay * RUNS_28 * labs

        m14 = rev_14 - reagent_annual - shipper_14
        m28 = rev_28 - reagent_annual - shipper_28
        diff = m28 - m14

        total_m14 += m14
        total_m28 += m28

        results.append({
            "panel_code": code,
            "panel_name": p["name"],
            "active_labs": labs,
            "reagent_cost_per_1000_tests_usd": p["reagent_cost"],
            "network_tier": p["network_tier"],
            "network_adjustment_per_run_per_lab_usd": net_adj,
            "shipper_class": p["shipper_class"],
            "shipper_cost_usd": shipper_cost,
            "base_payment_per_run_per_lab_usd": base_pay,
            "total_payment_per_run_per_lab_usd": total_pay,
            "tests_per_lab_per_run_14_day": p["tests_14"],
            "tests_per_lab_per_run_28_day": p["tests_28"],
            "annual_reagent_cost_14_day_usd": round(reagent_annual, 2),
            "annual_reagent_cost_28_day_usd": round(reagent_annual, 2),
            "annual_shipper_cost_14_day_usd": round(shipper_14, 2),
            "annual_shipper_cost_28_day_usd": round(shipper_28, 2),
            "annual_revenue_14_day_usd": round(rev_14, 2),
            "annual_revenue_28_day_usd": round(rev_28, 2),
            "annual_margin_14_day_usd": round(m14, 2),
            "annual_margin_28_day_usd": round(m28, 2),
            "annual_margin_difference_28_minus_14_usd": round(diff, 2)
        })

    abs_diff = abs(total_m28 - total_m14)
    if abs_diff > args.threshold:
        decision = "switch_to_28_day" if total_m28 > total_m14 else "keep_14_day"
    else:
        decision = "keep_14_day"

    out = template
    out["analysis"]["assumptions"] = {
        "runs_per_year_14_day": RUNS_14,
        "runs_per_year_28_day": RUNS_28,
        "switch_threshold_usd": args.threshold,
        "override_rule": "highest numeric approved rev with non-empty active_labs, else default_active_labs",
        "holdout_rule": "exclude holdout_state=exclude",
        "adjustment_rule": "missing network_tier adjustment defaults to 0.0"
    }
    out["analysis"]["panels"] = sorted(results, key=lambda x: x["panel_code"])
    out["analysis"]["totals"] = {
        "total_annual_margin_14_day_usd": round(total_m14, 2),
        "total_annual_margin_28_day_usd": round(total_m28, 2),
        "total_annual_margin_difference_28_minus_14_usd": round(total_m28 - total_m14, 2),
        "absolute_total_margin_difference_usd": round(abs_diff, 2)
    }
    out["analysis"]["recommendation"] = {
        "decision": decision,
        "reasoning": f"Absolute margin difference of ${abs_diff:,.2f} {'exceeds' if abs_diff > args.threshold else 'does not exceed'} the ${args.threshold:,.2f} threshold."
    }

    with open(args.out_json, 'w') as f:
        json.dump(out, f, indent=2)

    md = [
        "# Diagnostic Panel Policy Analysis Summary",
        "",
        f"**Total 14-day annual margin:** ${total_m14:,.2f} USD",
        f"**Total 28-day annual margin:** ${total_m28:,.2f} USD",
        f"**Absolute margin difference:** ${abs_diff:,.2f} USD",
        "",
        f"**Decision:** `{decision}`"
    ]
    with open(args.out_md, 'w') as f:
        f.write("\n".join(md) + "\n")

    print(f"Done. abs_diff={abs_diff}, decision={decision}")

if __name__ == "__main__":
    main()
