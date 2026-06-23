#!/usr/bin/env python3
import argparse
import csv
import json
import sys

def main():
    parser = argparse.ArgumentParser(description="Compute pharmacy mailer refill cycle margin analysis.")
    parser.add_argument("--compound", required=True, help="Path to compound_cost.csv")
    parser.add_argument("--mailer", required=True, help="Path to mailer_cost.csv")
    parser.add_argument("--base", required=True, help="Path to base_payment.csv")
    parser.add_argument("--fee", required=True, help="Path to service_fee.csv")
    parser.add_argument("--threshold", type=float, default=8500.0, help="Decision threshold USD")
    parser.add_argument("--patients", type=int, default=150, help="Patient cohort size")
    parser.add_argument("--cycle-a", type=int, default=45, help="Shorter cycle days")
    parser.add_argument("--cycle-b", type=int, default=90, help="Longer cycle days")
    parser.add_argument("--fills-a", type=int, default=8, help="Fills per year for cycle A")
    parser.add_argument("--fills-b", type=int, default=4, help="Fills per year for cycle B")
    parser.add_argument("--out-json", default="mailer_policy_analysis.json")
    parser.add_argument("--out-md", default="mailer_policy_summary.md")
    args = parser.parse_args()

    def load_csv(path):
        with open(path, newline='') as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters='\t,')
            return list(csv.DictReader(f, dialect=dialect))

    comp_rows = load_csv(args.compound)
    mailer_rows = load_csv(args.mailer)
    base_rows = load_csv(args.base)
    fee_rows = load_csv(args.fee)

    comp_data = {}
    for row in comp_rows:
        comp_data[row['medication']] = {
            'price_per_1000': float(row['price_per_1000_doses_usd']),
            'mailer_format': row['mailer_format']
        }

    mailer_data = {}
    for row in mailer_rows:
        mailer_data[row['mailer_format']] = float(row['mailer_cost_usd'])

    base_data = {}
    for row in base_rows:
        base_data[row['medication']] = float(row['base_payment_per_fill_150_patients_usd'])

    fee_data = {}
    for row in fee_rows:
        fee_data[row['medication']] = float(row['service_fee_per_fill_150_patients_usd'])

    meds = []
    total_margin_a = 0.0
    total_margin_b = 0.0

    for med, c in comp_data.items():
        price = c['price_per_1000']
        m_format = c['mailer_format']
        m_cost = mailer_data.get(m_format, 0.0)
        base_pay = base_data.get(med, 0.0)
        svc_fee = fee_data.get(med, 0.0)

        doses_a = args.cycle_a
        doses_b = args.cycle_b

        # Drug cost (identical annually)
        drug_a = (price / 1000.0) * doses_a * args.fills_a * args.patients
        drug_b = (price / 1000.0) * doses_b * args.fills_b * args.patients

        # Mailer cost
        mail_a = m_cost * args.fills_a * args.patients
        mail_b = m_cost * args.fills_b * args.patients

        # Payment (base + fee)
        pay_per_fill = base_pay + svc_fee
        pay_a = pay_per_fill * args.fills_a
        pay_b = pay_per_fill * args.fills_b

        margin_a = pay_a - drug_a - mail_a
        margin_b = pay_b - drug_b - mail_b
        diff = margin_b - margin_a

        total_margin_a += margin_a
        total_margin_b += margin_b

        meds.append({
            "medication": med,
            "price_per_1000_doses_usd": price,
            "mailer_format": m_format,
            "mailer_cost_usd": round(m_cost, 2),
            "base_payment_per_fill_usd": round(base_pay, 2),
            "service_fee_per_fill_usd": round(svc_fee, 2),
            "annual_drug_cost_45_day_usd": round(drug_a, 2),
            "annual_drug_cost_90_day_usd": round(drug_b, 2),
            "annual_mailer_cost_45_day_usd": round(mail_a, 2),
            "annual_mailer_cost_90_day_usd": round(mail_b, 2),
            "annual_payment_45_day_usd": round(pay_a, 2),
            "annual_payment_90_day_usd": round(pay_b, 2),
            "annual_margin_45_day_usd": round(margin_a, 2),
            "annual_margin_90_day_usd": round(margin_b, 2),
            "annual_margin_difference_90_minus_45_usd": round(diff, 2)
        })

    abs_diff = abs(total_margin_b - total_margin_a)
    if abs_diff > args.threshold:
        decision = "switch_to_90_day" if total_margin_b > total_margin_a else "keep_45_day"
    else:
        decision = "keep_45_day"

    result = {
        "assumptions": {
            "patients_per_medication": args.patients,
            "fills_per_year_45_day": args.fills_a,
            "fills_per_year_90_day": args.fills_b,
            "cycle_45_days": args.cycle_a,
            "cycle_90_days": args.cycle_b,
            "switch_threshold_usd": args.threshold
        },
        "medications": sorted(meds, key=lambda x: x['medication']),
        "totals": {
            "total_annual_margin_45_day_usd": round(total_margin_a, 2),
            "total_annual_margin_90_day_usd": round(total_margin_b, 2),
            "absolute_difference_usd": round(abs_diff, 2),
            "decision": decision
        }
    }

    with open(args.out_json, 'w') as f:
        json.dump(result, f, indent=2)

    md_lines = [
        "# Mailer Policy Analysis Summary",
        "",
        f"Total annual margin (45-day): **${total_margin_a:,.2f}**",
        f"Total annual margin (90-day): **${total_margin_b:,.2f}**",
        f"Absolute margin difference: **${abs_diff:,.2f}**",
        "",
        f"**Decision: {decision}**"
    ]
    with open(args.out_md, 'w') as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Done. abs_diff = {abs_diff}\ndecision = {decision}")

if __name__ == "__main__":
    main()
