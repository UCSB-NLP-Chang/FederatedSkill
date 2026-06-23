#!/usr/bin/env python3
"""Compute VaxCrate dispatch analysis and generate JSON/MD outputs."""
import csv
import json
import sys
import os

def parse_cycle_tag(tag):
    """Parse cycle_tag like '2026-Q4' into comparable tuple (year, quarter)."""
    parts = tag.split('-Q')
    return (int(parts[0]), int(parts[1]))

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "/root"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 11000.0

    # Load campaign manifest
    with open(os.path.join(base_dir, "campaign_manifest.json")) as f:
        manifest = json.load(f)

    campaigns = {}
    alias_map = {}
    for region in manifest.get("regions", []):
        for c in region.get("campaigns", []):
            if c.get("analysis_flag") == "review":
                code = c["campaign_id"]
                campaigns[code] = c
                alias_map[c["campaign_name"]] = code
                for alias in c.get("alias_labels", []):
                    alias_map[alias] = code

    # Load crate costs
    crate_costs = {}
    with open(os.path.join(base_dir, "crate_cost.csv")) as f:
        for row in csv.DictReader(f):
            crate_costs[row["crate_tier"]] = float(row["crate_cost_usd"])

    # Load billing data (latest active cycle_tag per campaign)
    payments = {}
    billing_rows = []
    with open(os.path.join(base_dir, "billing.csv")) as f:
        for row in csv.DictReader(f):
            label = row["campaign_label"]
            if label in alias_map:
                code = alias_map[label]
                if row.get("status", "").lower() == "active":
                    cycle_tag = row["cycle_tag"]
                    payment = float(row["payment_per_dispatch_per_clinic_usd"])
                    billing_rows.append((code, parse_cycle_tag(cycle_tag), payment))

    # Select latest cycle_tag per campaign
    latest_payment = {}
    for code, cycle, payment in billing_rows:
        if code not in latest_payment or cycle > latest_payment[code][0]:
            latest_payment[code] = (cycle, payment)
    for code, (_, payment) in latest_payment.items():
        payments[code] = payment

    # Load suspensions (exclude hold campaigns)
    hold_campaigns = set()
    with open(os.path.join(base_dir, "suspensions.csv")) as f:
        for row in csv.DictReader(f):
            if row.get("suspension_status", "").lower() == "hold":
                hold_campaigns.add(row["campaign_id"])

    # Remove hold campaigns from in-scope set
    for code in list(campaigns.keys()):
        if code in hold_campaigns:
            del campaigns[code]

    # Load location overrides (highest approved revision with non-empty fields)
    clinics = {}
    with open(os.path.join(base_dir, "location_overrides.csv")) as f:
        for row in csv.DictReader(f):
            code = row["campaign_id"]
            if code in campaigns and row.get("state", "").lower() == "approved":
                rev_str = row.get("revision", "").strip()
                active_str = row.get("active_clinics", "").strip()
                if rev_str and active_str:
                    try:
                        rev = int(rev_str)
                        active = int(active_str)
                        if code not in clinics or rev > clinics[code]["revision"]:
                            clinics[code] = {"revision": rev, "active_clinics": active}
                    except ValueError:
                        continue

    # Constants
    DISPATCHES_6 = 60
    DISPATCHES_12 = 30
    DAYS_PER_YEAR = 360

    results = []
    for code in sorted(campaigns.keys()):
        c = campaigns[code]
        # Resolve active clinics
        if code in clinics:
            clinic_count = clinics[code]["active_clinics"]
        else:
            clinic_count = c["default_active_clinics"]

        drug_cost_per_1000 = c["drug_cost_per_1000_doses_usd"]
        doses_per_day = c["doses_per_day"]
        crate_tier = c["crate_tier"]
        crate_cost = crate_costs[crate_tier]
        payment = payments[code]

        # Annual drug cost (identical for both)
        annual_drug = (drug_cost_per_1000 / 1000) * doses_per_day * DAYS_PER_YEAR * clinic_count

        # Crate costs
        crate_6 = crate_cost * DISPATCHES_6 * clinic_count
        crate_12 = crate_cost * DISPATCHES_12 * clinic_count

        # Revenue
        rev_6 = payment * DISPATCHES_6 * clinic_count
        rev_12 = payment * DISPATCHES_12 * clinic_count

        # Margins
        margin_6 = rev_6 - annual_drug - crate_6
        margin_12 = rev_12 - annual_drug - crate_12
        diff = margin_12 - margin_6

        results.append({
            "campaign_id": code,
            "campaign_name": c["campaign_name"],
            "active_clinics": clinic_count,
            "drug_cost_per_1000_doses_usd": round(drug_cost_per_1000, 2),
            "doses_per_day": doses_per_day,
            "crate_tier": crate_tier,
            "crate_cost_usd": round(crate_cost, 2),
            "payment_per_dispatch_per_clinic_usd": round(payment, 2),
            "annual_drug_cost_6_day_usd": round(annual_drug, 2),
            "annual_drug_cost_12_day_usd": round(annual_drug, 2),
            "annual_crate_cost_6_day_usd": round(crate_6, 2),
            "annual_crate_cost_12_day_usd": round(crate_12, 2),
            "annual_revenue_6_day_usd": round(rev_6, 2),
            "annual_revenue_12_day_usd": round(rev_12, 2),
            "annual_margin_6_day_usd": round(margin_6, 2),
            "annual_margin_12_day_usd": round(margin_12, 2),
            "annual_margin_difference_12_minus_6_usd": round(diff, 2)
        })

    total_margin_6 = round(sum(r["annual_margin_6_day_usd"] for r in results), 2)
    total_margin_12 = round(sum(r["annual_margin_12_day_usd"] for r in results), 2)
    total_diff = round(total_margin_12 - total_margin_6, 2)
    abs_total_diff = round(abs(total_diff), 2)

    decision = "move_to_12_day" if abs_total_diff < threshold else "keep_6_day"

    output = {
        "assumptions": {
            "dispatches_per_year_6_day": DISPATCHES_6,
            "dispatches_per_year_12_day": DISPATCHES_12,
            "days_per_dispatch_6_day": 6,
            "days_per_dispatch_12_day": 12,
            "switch_threshold_usd": threshold,
            "override_rule": "highest numeric approved revision with non-empty active_clinics, else default_active_clinics",
            "suspension_rule": "exclude campaigns with suspension_status=hold"
        },
        "campaigns": results,
        "totals": {
            "annual_margin_6_day_usd": total_margin_6,
            "annual_margin_12_day_usd": total_margin_12,
            "absolute_difference_usd": abs_total_diff,
            "decision": decision
        }
    }

    json_path = os.path.join(base_dir, "vaxcrate_analysis.json")
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)

    summary_path = os.path.join(base_dir, "vaxcrate_summary.md")
    with open(summary_path, "w") as f:
        f.write("# Vaccination Crate Dispatch Analysis Summary\n\n")
        f.write(f"Total 6-day annual margin: ${total_margin_6:,.2f} USD\n")
        f.write(f"Total 12-day annual margin: ${total_margin_12:,.2f} USD\n")
        f.write(f"Absolute margin difference (12-day minus 6-day): ${abs_total_diff:,.2f} USD\n")
        f.write(f"Decision: `{decision}`\n")

    print(f"Generated {json_path} and {summary_path}")

if __name__ == "__main__":
    main()