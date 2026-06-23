#!/usr/bin/env python3
import argparse
import csv
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Compute onco cooler dispatch cycle margin analysis.")
    parser.add_argument("--catalog", required=True, help="Path to program_catalog.json")
    parser.add_argument("--cooler", required=True, help="Path to cooler_cost.csv")
    parser.add_argument("--payment", required=True, help="Path to contract_payment.csv")
    parser.add_argument("--overrides", required=True, help="Path to site_overrides.csv")
    parser.add_argument("--threshold", type=float, default=10000.0, help="Decision threshold USD")
    parser.add_argument("--out-json", default="onco_cooler_analysis.json")
    parser.add_argument("--out-md", default="onco_cooler_summary.md")
    args = parser.parse_args()

    def load_csv(path):
        with open(path, newline='') as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters='\t,')
            return list(csv.DictReader(f, dialect=dialect))

    # Load catalog
    with open(args.catalog) as f:
        catalog = json.load(f)

    programs = {}
    label_to_code = {}
    for sg in catalog.get("service_groups", []):
        for p in sg.get("programs", []):
            if p.get("review_flag") == "review":
                code = p["program_code"]
                programs[code] = {
                    "name": p["program_name"],
                    "cost_per_1000": p["acquisition_cost_per_1000_units_usd"],
                    "units_per_day": p["units_per_day"],
                    "cooler_type": p["cooler_type"],
                    "default_sites": p["default_active_sites"]
                }
                for label in p.get("known_labels", []):
                    label_to_code[label] = code

    # Load cooler costs
    cooler_costs = {}
    for row in load_csv(args.cooler):
        cooler_costs[row["cooler_type"]] = float(row["cooler_cost_usd"])

    # Load payments
    payments = {}
    for row in load_csv(args.payment):
        label = row["program_label"]
        if label in label_to_code:
            payments[label_to_code[label]] = float(row["payment_per_dispatch_per_site_usd"])

    # Load overrides
    overrides = {}
    for row in load_csv(args.overrides):
        code = row["program_code"]
        if row["approval_state"] == "approved":
            ver = int(row["version_no"])
            if code not in overrides or ver > overrides[code]["ver"]:
                overrides[code] = {"ver": ver, "sites": int(row["active_sites"])}

    DISP_10 = 36
    DISP_20 = 18
    DAYS_YEAR = 360

    results = []
    total_m10 = 0.0
    total_m20 = 0.0

    for code, p in programs.items():
        sites = overrides.get(code, {}).get("sites", p["default_sites"])
        cooler_cost = cooler_costs.get(p["cooler_type"], 0.0)
        payment = payments.get(code, 0.0)

        drug_annual = (p["cost_per_1000"] / 1000.0) * p["units_per_day"] * DAYS_YEAR * sites
        cooler_10 = cooler_cost * DISP_10 * sites
        cooler_20 = cooler_cost * DISP_20 * sites
        rev_10 = payment * DISP_10 * sites
        rev_20 = payment * DISP_20 * sites

        m10 = rev_10 - drug_annual - cooler_10
        m20 = rev_20 - drug_annual - cooler_20
        diff = m20 - m10

        total_m10 += m10
        total_m20 += m20

        results.append({
            "program_code": code,
            "program_name": p["name"],
            "active_sites": sites,
            "acquisition_cost_per_1000_units_usd": p["cost_per_1000"],
            "units_per_day": p["units_per_day"],
            "cooler_type": p["cooler_type"],
            "cooler_cost_usd": cooler_cost,
            "payment_per_dispatch_per_site_usd": payment,
            "annual_drug_cost_10_day_usd": round(drug_annual, 2),
            "annual_drug_cost_20_day_usd": round(drug_annual, 2),
            "annual_cooler_cost_10_day_usd": round(cooler_10, 2),
            "annual_cooler_cost_20_day_usd": round(cooler_20, 2),
            "annual_revenue_10_day_usd": round(rev_10, 2),
            "annual_revenue_20_day_usd": round(rev_20, 2),
            "annual_margin_10_day_usd": round(m10, 2),
            "annual_margin_20_day_usd": round(m20, 2),
            "annual_margin_difference_20_minus_10_usd": round(diff, 2)
        })

    abs_diff = abs(total_m20 - total_m10)
    if abs_diff > args.threshold:
        decision = "switch_to_20_day" if total_m20 > total_m10 else "keep_10_day"
    else:
        decision = "keep_10_day"

    out = {
        "assumptions": {
            "dispatches_per_year_10_day": DISP_10,
            "dispatches_per_year_20_day": DISP_20,
            "days_covered_per_year": DAYS_YEAR,
            "switch_threshold_usd": args.threshold,
            "site_override_rule": "highest approved version_no per program_code"
        },
        "programs": sorted(results, key=lambda x: x["program_code"]),
        "totals": {
            "total_annual_margin_10_day_usd": round(total_m10, 2),
            "total_annual_margin_20_day_usd": round(total_m20, 2),
            "absolute_difference_usd": round(abs_diff, 2),
            "decision": decision
        }
    }

    with open(args.out_json, 'w') as f:
        json.dump(out, f, indent=2)

    md = [
        "# Oncology Cooler Dispatch Analysis",
        "",
        f"**10-day total annual margin:** ${total_m10:,.2f}",
        f"**20-day total annual margin:** ${total_m20:,.2f}",
        f"**Absolute margin difference:** ${abs_diff:,.2f}",
        "",
        f"**Decision:** `{decision}`"
    ]
    with open(args.out_md, 'w') as f:
        f.write("\n".join(md) + "\n")

    print(f"Done. abs_diff={abs_diff}, decision={decision}")

if __name__ == "__main__":
    main()
