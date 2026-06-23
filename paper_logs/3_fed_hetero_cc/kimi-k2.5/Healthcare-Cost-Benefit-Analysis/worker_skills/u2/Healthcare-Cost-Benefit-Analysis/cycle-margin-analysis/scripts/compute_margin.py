#!/usr/bin/env python3
import argparse
import csv
import json
import os

def main():
    parser = argparse.ArgumentParser(description="Compute refill cycle margin analysis between two cycle lengths.")
    parser.add_argument("--acquisition", required=True, help="Path to acquisition/wholesale price CSV")
    parser.add_argument("--packaging", required=True, help="Path to packaging/vial price CSV")
    parser.add_argument("--reimbursement", required=True, help="Path to reimbursement CSV")
    parser.add_argument("--threshold", type=float, default=12000.0, help="Decision threshold in USD")
    parser.add_argument("--output-dir", default=".", help="Directory for output files")
    parser.add_argument("--patients", type=int, default=240, help="Number of patients per medication")
    parser.add_argument("--fills-a", type=int, default=12, help="Fills per year for cycle A")
    parser.add_argument("--fills-b", type=int, default=4, help="Fills per year for cycle B")
    parser.add_argument("--doses-a", type=int, default=60, help="Doses/tablets per fill for cycle A")
    parser.add_argument("--doses-b", type=int, default=180, help="Doses/tablets per fill for cycle B")
    parser.add_argument("--label-a", default="30_day", help="Label for cycle A (e.g., 30_day, 90_day)")
    parser.add_argument("--label-b", default="90_day", help="Label for cycle B (e.g., 90_day, 100_day)")
    parser.add_argument("--entity-col", default="therapy", help="Column name for entity (therapy/medication)")
    parser.add_argument("--price-col", default="price_per_1000_doses_usd", help="Column name for price per 1000 doses/tablets")
    parser.add_argument("--container-col", default="canister_size_units", help="Column name for container size in acquisition CSV")
    parser.add_argument("--supply-col", default="packaging_cost_usd", help="Column name for supply cost in packaging CSV")
    parser.add_argument("--reimb-col", default="reimbursement_per_fill_240_patients_usd", help="Column name for reimbursement per fill")
    parser.add_argument("--container-join-col", default=None, help="Column name for container size in packaging CSV (defaults to same as --container-col)")
    args = parser.parse_args()

    container_join_col = args.container_join_col or args.container_col

    # Read acquisition (keyed by entity)
    acq_data = {}
    with open(args.acquisition, newline='') as f:
        for row in csv.DictReader(f):
            acq_data[row[args.entity_col]] = row

    # Read packaging/supply (keyed by container size)
    pkg_data = {}
    with open(args.packaging, newline='') as f:
        for row in csv.DictReader(f):
            pkg_data[row[container_join_col]] = row

    # Read reimbursement (keyed by entity)
    reimb_data = {}
    with open(args.reimbursement, newline='') as f:
        for row in csv.DictReader(f):
            reimb_data[row[args.entity_col]] = row

    entities = sorted(acq_data.keys())
    results = []
    total_margin_a = 0.0
    total_margin_b = 0.0

    for e in entities:
        acq = acq_data[e]
        reimb = reimb_data.get(e, {})

        price_per_1000 = float(acq[args.price_col])
        container_size = acq[args.container_col]
        # Try int conversion for matching, fall back to string
        try:
            container_key = str(int(float(container_size)))
        except (ValueError, TypeError):
            container_key = str(container_size)
        pkg_cost = float(pkg_data[container_key][args.supply_col])
        reimb_per_fill = float(reimb.get(args.reimb_col, 0))

        # Annual drug cost (may differ between models)
        annual_drug_cost_a = (price_per_1000 / 1000.0) * args.doses_a * args.fills_a * args.patients
        annual_drug_cost_b = (price_per_1000 / 1000.0) * args.doses_b * args.fills_b * args.patients

        # Supply/packaging costs
        supply_a = pkg_cost * args.fills_a * args.patients
        supply_b = pkg_cost * args.fills_b * args.patients

        # Reimbursement
        reimb_a = reimb_per_fill * args.fills_a
        reimb_b = reimb_per_fill * args.fills_b

        # Margins
        margin_a = reimb_a - (annual_drug_cost_a + supply_a)
        margin_b = reimb_b - (annual_drug_cost_b + supply_b)
        diff = margin_b - margin_a

        total_margin_a += margin_a
        total_margin_b += margin_b

        result = {
            args.entity_col: e,
            args.price_col: price_per_1000,
            args.container_col: container_size,
            args.supply_col: pkg_cost,
            args.reimb_col: reimb_per_fill,
            f"annual_drug_cost_{args.label_a}_usd": annual_drug_cost_a,
            f"annual_drug_cost_{args.label_b}_usd": annual_drug_cost_b,
            f"annual_supply_cost_{args.label_a}_usd": supply_a,
            f"annual_supply_cost_{args.label_b}_usd": supply_b,
            f"annual_reimbursement_{args.label_a}_usd": reimb_a,
            f"annual_reimbursement_{args.label_b}_usd": reimb_b,
            f"annual_margin_{args.label_a}_usd": margin_a,
            f"annual_margin_{args.label_b}_usd": margin_b,
            f"annual_margin_difference_{args.label_b}_minus_{args.label_a}_usd": diff
        }
        results.append(result)

    abs_diff = abs(total_margin_b - total_margin_a)
    if total_margin_b > total_margin_a and abs_diff > args.threshold:
        decision = f"switch_to_{args.label_b}"
    else:
        decision = f"keep_{args.label_a}"

    # Write JSON
    output_json = {
        "assumptions": {
            "patients_per_medication": args.patients,
            f"fills_per_year_{args.label_a}": args.fills_a,
            f"fills_per_year_{args.label_b}": args.fills_b,
            f"doses_per_fill_{args.label_a}": args.doses_a,
            f"doses_per_fill_{args.label_b}": args.doses_b,
            "switch_threshold_usd": args.threshold
        },
        "medications" if args.entity_col == "medication" else "therapies": results,
        "totals": {
            f"total_annual_margin_{args.label_a}_usd": total_margin_a,
            f"total_annual_margin_{args.label_b}_usd": total_margin_b,
            "absolute_difference_usd": abs_diff,
            "decision": decision
        }
    }
    json_path = os.path.join(args.output_dir, "cycle_margin_analysis.json")
    with open(json_path, 'w') as f:
        json.dump(output_json, f, indent=2)

    # Write Markdown
    md_path = os.path.join(args.output_dir, "cycle_margin_summary.md")
    with open(md_path, 'w') as f:
        f.write("# Pharmacy Refill Cycle Analysis\n\n")
        f.write(f"Total annual margin under {args.label_a} fills: ${total_margin_a:,.2f}\n")
        f.write(f"Total annual margin under {args.label_b} fills: ${total_margin_b:,.2f}\n")
        f.write(f"Absolute margin difference ({args.label_b} vs {args.label_a}): ${abs_diff:,.2f}\n")
        f.write(f"Decision: {decision}\n")

    print(f"JSON written to {json_path}")
    print(f"Summary written to {md_path}")
    print(f"Decision: {decision}")

if __name__ == "__main__":
    main()
