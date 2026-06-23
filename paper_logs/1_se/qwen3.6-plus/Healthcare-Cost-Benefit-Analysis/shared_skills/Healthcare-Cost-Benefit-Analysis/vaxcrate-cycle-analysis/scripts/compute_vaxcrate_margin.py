#!/usr/bin/env python3
import argparse
import csv
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Compute vaxcrate dispatch cycle margin analysis.")
    parser.add_argument("--manifest", required=True, help="Path to campaign_manifest.json")
    parser.add_argument("--crate", required=True, help="Path to crate_cost.csv")
    parser.add_argument("--billing", required=True, help="Path to billing.csv")
    parser.add_argument("--overrides", required=True, help="Path to location_overrides.csv")
    parser.add_argument("--suspensions", required=True, help="Path to suspensions.csv")
    parser.add_argument("--threshold", type=float, default=11000.0, help="Decision threshold USD")
    parser.add_argument("--out-json", default="vaxcrate_analysis.json")
    parser.add_argument("--out-md", default="vaxcrate_summary.md")
    args = parser.parse_args()

    def load_csv(path):
        with open(path, newline='') as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters='\t,')
            return list(csv.DictReader(f, dialect=dialect))

    with open(args.manifest) as f:
        manifest = json.load(f)

    campaigns = {}
    alias_to_id = {}
    for region in manifest.get("regions", []):
        for c in region.get("campaigns", []):
            if c.get("analysis_flag") == "review":
                cid = c["campaign_id"]
                campaigns[cid] = {
                    "name": c["campaign_name"],
                    "drug_cost_per_1000": c["drug_cost_per_1000_doses_usd"],
                    "doses_per_day": c["doses_per_day"],
                    "crate_tier": c["crate_tier"],
                    "default_clinics": c["default_active_clinics"]
                }
                for alias in c.get("alias_labels", []):
                    alias_to_id[alias] = cid

    # Load suspensions
    hold_ids = set()
    for row in load_csv(args.suspensions):
        if row.get("suspension_status", "").strip().lower() == "hold":
            hold_ids.add(row["campaign_id"])

    # Filter out held campaigns
    for cid in list(campaigns.keys()):
        if cid in hold_ids:
            del campaigns[cid]

    # Load crate costs
    crate_costs = {}
    for row in load_csv(args.crate):
        crate_costs[row["crate_tier"]] = float(row["crate_cost_usd"])

    # Load billing
    billing = {}
    for row in load_csv(args.billing):
        if row.get("status", "").strip().lower() == "active":
            label = row["campaign_label"]
            if label in alias_to_id:
                cid = alias_to_id[label]
                cycle = row["cycle_tag"]
                pay = float(row["payment_per_dispatch_per_clinic_usd"])
                if cid not in billing or cycle > billing[cid]["cycle"]:
                    billing[cid] = {"cycle": cycle, "payment": pay}

    # Load overrides
    overrides = {}
    for row in load_csv(args.overrides):
        if row.get("state", "").strip().lower() == "approved":
            cid = row["campaign_id"]
            rev_str = row.get("revision", "").strip()
            rev = int(rev_str) if rev_str else 0
            clinics_str = row.get("active_clinics", "").strip()
            clinics = int(clinics_str) if clinics_str else 0
            if cid not in overrides or rev > overrides[cid]["rev"]:
                overrides[cid] = {"rev": rev, "clinics": clinics}

    DISP_6 = 60
    DISP_12 = 30
    DAYS_YEAR = 360

    results = []
    total_m6 = 0.0
    total_m12 = 0.0

    for cid, c in campaigns.items():
        clinics = overrides.get(cid, {}).get("clinics", c["default_clinics"])
        crate_cost = crate_costs.get(c["crate_tier"], 0.0)
        payment = billing.get(cid, {}).get("payment", 0.0)

        drug_annual = (c["drug_cost_per_1000"] / 1000.0) * c["doses_per_day"] * DAYS_YEAR * clinics
        crate_6 = crate_cost * DISP_6 * clinics
        crate_12 = crate_cost * DISP_12 * clinics
        rev_6 = payment * DISP_6 * clinics
        rev_12 = payment * DISP_12 * clinics

        m6 = rev_6 - drug_annual - crate_6
        m12 = rev_12 - drug_annual - crate_12
        diff = m12 - m6

        total_m6 += m6
        total_m12 += m12

        results.append({
            "campaign_id": cid,
            "campaign_name": c["name"],
            "active_clinics": clinics,
            "drug_cost_per_1000_doses_usd": c["drug_cost_per_1000"],
            "doses_per_day": c["doses_per_day"],
            "crate_tier": c["crate_tier"],
            "crate_cost_usd": crate_cost,
            "payment_per_dispatch_per_clinic_usd": payment,
            "annual_drug_cost_6_day_usd": round(drug_annual, 2),
            "annual_drug_cost_12_day_usd": round(drug_annual, 2),
            "annual_crate_cost_6_day_usd": round(crate_6, 2),
            "annual_crate_cost_12_day_usd": round(crate_12, 2),
            "annual_revenue_6_day_usd": round(rev_6, 2),
            "annual_revenue_12_day_usd": round(rev_12, 2),
            "annual_margin_6_day_usd": round(m6, 2),
            "annual_margin_12_day_usd": round(m12, 2),
            "annual_margin_difference_12_minus_6_usd": round(diff, 2)
        })

    abs_diff = abs(total_m12 - total_m6)
    if abs_diff > args.threshold:
        decision = "switch_to_12_day" if total_m12 > total_m6 else "keep_6_day"
    else:
        decision = "keep_6_day"

    out = {
        "assumptions": {
            "dispatches_per_year_6_day": DISP_6,
            "dispatches_per_year_12_day": DISP_12,
            "days_per_dispatch_6_day": 6,
            "days_per_dispatch_12_day": 12,
            "switch_threshold_usd": args.threshold,
            "override_rule": "highest numeric approved revision per campaign_id",
            "suspension_rule": "exclude campaigns with suspension_status == 'hold'"
        },
        "campaigns": sorted(results, key=lambda x: x["campaign_id"]),
        "totals": {
            "total_annual_margin_6_day_usd": round(total_m6, 2),
            "total_annual_margin_12_day_usd": round(total_m12, 2),
            "absolute_difference_usd": round(abs_diff, 2),
            "decision": decision
        }
    }

    with open(args.out_json, 'w') as f:
        json.dump(out, f, indent=2)

    md = [
        "# Vaccination Crate Dispatch Cycle Analysis",
        "",
        f"**Total 6-day annual margin:** ${total_m6:,.2f} USD",
        f"**Total 12-day annual margin:** ${total_m12:,.2f} USD",
        f"**Absolute margin difference (12-day minus 6-day):** ${abs_diff:,.2f} USD",
        "",
        f"**Decision:** `{decision}`"
    ]
    with open(args.out_md, 'w') as f:
        f.write("\n".join(md) + "\n")

    print(f"Done. abs_diff={abs_diff}, decision={decision}")

if __name__ == "__main__":
    main()
