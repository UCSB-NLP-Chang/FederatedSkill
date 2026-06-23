#!/usr/bin/env python3
import argparse
import csv
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Compute syncpack cycle margin analysis.")
    parser.add_argument("--ingredient", required=True, help="Path to ingredient_cost.csv")
    parser.add_argument("--card", required=True, help="Path to card_cost.csv")
    parser.add_argument("--reim", required=True, help="Path to reimbursement.csv")
    parser.add_argument("--threshold", type=float, default=9000.0, help="Decision threshold USD")
    parser.add_argument("--patients", type=int, default=180, help="Patient cohort size")
    parser.add_argument("--cycle-a", type=int, default=28, help="Shorter cycle days")
    parser.add_argument("--cycle-b", type=int, default=56, help="Longer cycle days")
    parser.add_argument("--out-json", default="syncpack_analysis.json")
    parser.add_argument("--out-md", default="syncpack_summary.md")
    args = parser.parse_args()

    def load_csv(path):
        with open(path, newline='') as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters='\t,')
            return list(csv.DictReader(f, dialect=dialect))

    ing_rows = load_csv(args.ingredient)
    card_rows = load_csv(args.card)
    reim_rows = load_csv(args.reim)

    ing_data = {}
    for row in ing_rows:
        ing_data[row['medication']] = {
            'price_per_1000': float(row['price_per_1000_capsules_usd']),
            'blister_card_count': int(row['blister_card_count'])
        }

    card_data = {}
    for row in card_rows:
        card_data[int(row['blister_card_count'])] = float(row['card_cost_usd'])

    reim_data = {}
    for row in reim_rows:
        reim_data[row['medication']] = float(row['reimbursement_per_cycle_180_patients_usd'])

    fills_a = 365.0 / args.cycle_a
    fills_b = 365.0 / args.cycle_b

    meds = []
    total_margin_a = 0.0
    total_margin_b = 0.0

    for med, ing in ing_data.items():
        price = ing['price_per_1000']
        card_count = ing['blister_card_count']
        card_cost = card_data.get(card_count, 0.0)
        reim = reim_data.get(med, 0.0)

        # Assume 1 capsule per day
        caps_per_fill_a = args.cycle_a
        caps_per_fill_b = args.cycle_b
        cards_per_fill_a = args.cycle_a / card_count
        cards_per_fill_b = args.cycle_b / card_count

        # Drug cost (identical annually)
        drug_a = (price / 1000.0) * caps_per_fill_a * fills_a * args.patients
        drug_b = (price / 1000.0) * caps_per_fill_b * fills_b * args.patients

        # Card cost
        pkg_a = card_cost * cards_per_fill_a * fills_a * args.patients
        pkg_b = card_cost * cards_per_fill_b * fills_b * args.patients

        # Reimbursement (already scaled for cohort)
        reim_a = reim * fills_a
        reim_b = reim * fills_b

        margin_a = reim_a - drug_a - pkg_a
        margin_b = reim_b - drug_b - pkg_b
        diff = margin_b - margin_a

        total_margin_a += margin_a
        total_margin_b += margin_b

        meds.append({
            "medication": med,
            "price_per_1000_capsules_usd": price,
            "blister_card_count": card_count,
            "card_cost_usd": round(card_cost, 2),
            "reimbursement_per_cycle_180_patients_usd": reim,
            "annual_drug_cost_28_day_usd": round(drug_a, 2),
            "annual_drug_cost_56_day_usd": round(drug_b, 2),
            "annual_card_cost_28_day_usd": round(pkg_a, 2),
            "annual_card_cost_56_day_usd": round(pkg_b, 2),
            "annual_reimbursement_28_day_usd": round(reim_a, 2),
            "annual_reimbursement_56_day_usd": round(reim_b, 2),
            "annual_margin_28_day_usd": round(margin_a, 2),
            "annual_margin_56_day_usd": round(margin_b, 2),
            "annual_margin_difference_56_minus_28_usd": round(diff, 2)
        })

    abs_diff = abs(total_margin_b - total_margin_a)
    # Correct threshold logic: switch only if difference EXCEEDS threshold
    if abs_diff > args.threshold:
        decision = "convert_to_56_day" if total_margin_b > total_margin_a else "keep_28_day"
    else:
        decision = "keep_28_day"

    result = {
        "assumptions": {
            "patients_per_medication": args.patients,
            "fills_per_year_28_day": round(fills_a, 4),
            "fills_per_year_56_day": round(fills_b, 4),
            "cycle_28_days": args.cycle_a,
            "cycle_56_days": args.cycle_b,
            "switch_threshold_usd": args.threshold
        },
        "medications": sorted(meds, key=lambda x: x['medication']),
        "totals": {
            "total_annual_margin_28_day_usd": round(total_margin_a, 2),
            "total_annual_margin_56_day_usd": round(total_margin_b, 2),
            "absolute_difference_usd": round(abs_diff, 2),
            "decision": decision
        }
    }

    with open(args.out_json, 'w') as f:
        json.dump(result, f, indent=2)

    md_lines = [
        "# SyncPack Cycle Analysis Summary",
        "",
        f"Total annual margin (28-day): **${total_margin_a:,.2f}**",
        f"Total annual margin (56-day): **${total_margin_b:,.2f}**",
        f"Absolute margin difference: **${abs_diff:,.2f}**",
        "",
        f"**Decision: {decision}**"
    ]
    with open(args.out_md, 'w') as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Done. abs_diff = {abs_diff}\ndecision = {decision}")

if __name__ == "__main__":
    main()
