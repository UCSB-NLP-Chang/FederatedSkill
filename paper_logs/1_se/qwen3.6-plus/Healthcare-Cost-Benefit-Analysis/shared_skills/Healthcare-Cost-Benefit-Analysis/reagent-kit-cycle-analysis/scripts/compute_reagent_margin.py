#!/usr/bin/env python3
import argparse
import csv
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Compute reagent kit cycle margin analysis.")
    parser.add_argument("--manifest", required=True, help="Path to assay_manifest.json")
    parser.add_argument("--carrier", required=True, help="Path to carrier_cost.csv")
    parser.add_argument("--billing", required=True, help="Path to billing.csv")
    parser.add_argument("--overrides", required=True, help="Path to lab_overrides.csv")
    parser.add_argument("--template", required=True, help="Path to report_template.json")
    parser.add_argument("--threshold", type=float, default=7000.0, help="Decision threshold USD")
    parser.add_argument("--out-json", default="reagent_policy_report.json")
    parser.add_argument("--out-md", default="reagent_policy_summary.md")
    args = parser.parse_args()

    def load_csv(path):
        with open(path, newline='') as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters='\t,')
            return list(csv.DictReader(f, dialect=dialect))

    with open(args.manifest) as f:
        manifest = json.load(f)

    with open(args.template) as f:
        template = json.load(f)

    assays = {}
    alias_to_id = {}
    for region in manifest.get("regions", []):
        for a in region.get("assays", []):
            if a.get("in_scope", False):
                aid = a["assay_id"]
                assays[aid] = {
                    "name": a["assay_name"],
                    "reagent_price": a["reagent_price_per_1000_tests_usd"],
                    "carrier_type": a["carrier_type"],
                    "tests_small": a["tests_per_lab_per_run_small"],
                    "tests_bulk": a["tests_per_lab_per_run_bulk"],
                    "default_labs": a["default_active_labs"]
                }
                for alias in a.get("aliases", []):
                    alias_to_id[alias] = aid

    carrier_costs = {}
    for row in load_csv(args.carrier):
        carrier_costs[row["carrier_type"]] = float(row["carrier_cost_usd"])

    billing = {}
    for row in load_csv(args.billing):
        if row["is_active"].strip().lower() == "true":
            label = row["assay_label"]
            if label in alias_to_id:
                aid = alias_to_id[label]
                month = row["effective_month"]
                pay = float(row["payment_per_run_per_lab_usd"])
                if aid not in billing or month > billing[aid]["month"]:
                    billing[aid] = {"month": month, "payment": pay}

    overrides = {}
    for row in load_csv(args.overrides):
        if row["status"].strip().lower() == "approved":
            aid = row["assay_id"]
            rev = int(row["revision"])
            labs = int(row["active_labs"])
            if aid not in overrides or rev > overrides[aid]["rev"]:
                overrides[aid] = {"rev": rev, "labs": labs}

    RUNS_SMALL = 24
    RUNS_BULK = 12

    results = []
    total_m_small = 0.0
    total_m_bulk = 0.0

    for aid, a in assays.items():
        labs = overrides.get(aid, {}).get("labs", a["default_labs"])
        carrier_cost = carrier_costs.get(a["carrier_type"], 0.0)
        payment = billing.get(aid, {}).get("payment", 0.0)

        reagent_annual = (a["reagent_price"] / 1000.0) * a["tests_small"] * RUNS_SMALL * labs
        carrier_small = carrier_cost * RUNS_SMALL * labs
        carrier_bulk = carrier_cost * RUNS_BULK * labs
        rev_small = payment * RUNS_SMALL * labs
        rev_bulk = payment * RUNS_BULK * labs

        m_small = rev_small - reagent_annual - carrier_small
        m_bulk = rev_bulk - reagent_annual - carrier_bulk
        diff = m_bulk - m_small

        total_m_small += m_small
        total_m_bulk += m_bulk

        results.append({
            "assay_id": aid,
            "assay_name": a["name"],
            "active_labs": labs,
            "reagent_price_per_1000_tests_usd": a["reagent_price"],
            "carrier_type": a["carrier_type"],
            "carrier_cost_usd": carrier_cost,
            "payment_per_run_per_lab_usd": payment,
            "annual_reagent_cost_usd": round(reagent_annual, 2),
            "annual_carrier_cost_small_kit_usd": round(carrier_small, 2),
            "annual_carrier_cost_bulk_kit_usd": round(carrier_bulk, 2),
            "annual_revenue_small_kit_usd": round(rev_small, 2),
            "annual_revenue_bulk_kit_usd": round(rev_bulk, 2),
            "annual_margin_small_kit_usd": round(m_small, 2),
            "annual_margin_bulk_kit_usd": round(m_bulk, 2),
            "annual_margin_difference_bulk_minus_small_usd": round(diff, 2)
        })

    abs_diff = abs(total_m_bulk - total_m_small)
    if abs_diff > args.threshold:
        decision = "switch_to_bulk_kit" if total_m_bulk > total_m_small else "keep_small_kit"
    else:
        decision = "keep_small_kit"

    out = template
    out["analysis"]["assumptions"] = {
        "runs_per_year_small_kit": RUNS_SMALL,
        "runs_per_year_bulk_kit": RUNS_BULK,
        "switch_threshold_usd": args.threshold,
        "lab_override_rule": "highest approved revision per assay_id",
        "billing_rule": "latest active effective_month per assay"
    }
    out["analysis"]["assays"] = sorted(results, key=lambda x: x["assay_id"])
    out["analysis"]["totals"] = {
        "total_annual_margin_small_kit_usd": round(total_m_small, 2),
        "total_annual_margin_bulk_kit_usd": round(total_m_bulk, 2),
        "total_annual_margin_difference_bulk_minus_small_usd": round(total_m_bulk - total_m_small, 2),
        "absolute_total_margin_difference_usd": round(abs_diff, 2)
    }
    out["analysis"]["recommendation"] = {
        "decision": decision,
        "reasoning": f"Absolute margin difference of ${abs_diff:,.2f} {'exceeds' if abs_diff > args.threshold else 'does not exceed'} the ${args.threshold:,.2f} threshold."
    }

    with open(args.out_json, 'w') as f:
        json.dump(out, f, indent=2)

    md = [
        "# Reagent Policy Analysis Summary",
        "",
        f"**Total small-kit annual margin:** ${total_m_small:,.2f} USD",
        f"**Total bulk-kit annual margin:** ${total_m_bulk:,.2f} USD",
        f"**Absolute margin difference:** ${abs_diff:,.2f} USD",
        "",
        f"**Decision:** `{decision}`"
    ]
    with open(args.out_md, 'w') as f:
        f.write("\n".join(md) + "\n")

    print(f"Done. abs_diff={abs_diff}, decision={decision}")

if __name__ == "__main__":
    main()