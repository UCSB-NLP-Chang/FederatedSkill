#!/usr/bin/env python3
"""Compute Mailer Policy analysis and generate JSON/MD outputs."""
import csv
import json
import sys
import os

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "/root"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 8500.0

    compounds = {}
    with open(os.path.join(base_dir, "compound_cost.csv")) as f:
        for row in csv.DictReader(f):
            compounds[row["medication"]] = {
                "price_per_1000": float(row["price_per_1000_doses_usd"]),
                "mailer_format": row["mailer_format"]
            }

    mailers = {}
    with open(os.path.join(base_dir, "mailer_cost.csv")) as f:
        for row in csv.DictReader(f):
            mailers[row["mailer_format"]] = float(row["mailer_cost_usd"])

    base_payments = {}
    with open(os.path.join(base_dir, "base_payment.csv")) as f:
        for row in csv.DictReader(f):
            base_payments[row["medication"]] = float(row["base_payment_per_fill_150_patients_usd"])

    service_fees = {}
    with open(os.path.join(base_dir, "service_fee.csv")) as f:
        for row in csv.DictReader(f):
            service_fees[row["medication"]] = float(row["service_fee_per_fill_150_patients_usd"])

    PATIENTS = 150
    FILLS_45 = 8
    FILLS_90 = 4
    DOSES_45 = 45
    DOSES_90 = 90

    medications = []
    for med_name in sorted(compounds.keys()):
        comp = compounds[med_name]
        price = comp["price_per_1000"]
        fmt = comp["mailer_format"]
        mailer_cost = mailers[fmt]
        base_pay = base_payments[med_name]
        svc_fee = service_fees[med_name]
        total_pay_per_fill = base_pay + svc_fee

        annual_drug = (price / 1000) * PATIENTS * FILLS_45 * DOSES_45
        annual_mailer_45 = mailer_cost * PATIENTS * FILLS_45
        annual_mailer_90 = mailer_cost * PATIENTS * FILLS_90
        annual_pay_45 = total_pay_per_fill * FILLS_45
        annual_pay_90 = total_pay_per_fill * FILLS_90

        margin_45 = annual_pay_45 - annual_drug - annual_mailer_45
        margin_90 = annual_pay_90 - annual_drug - annual_mailer_90
        diff = margin_90 - margin_45

        medications.append({
            "medication": med_name,
            "price_per_1000_doses_usd": round(price, 2),
            "mailer_format": fmt,
            "mailer_cost_usd": round(mailer_cost, 2),
            "base_payment_per_fill_150_patients_usd": round(base_pay, 2),
            "service_fee_per_fill_150_patients_usd": round(svc_fee, 2),
            "total_payment_per_fill_150_patients_usd": round(total_pay_per_fill, 2),
            "annual_drug_cost_45_day_usd": round(annual_drug, 2),
            "annual_drug_cost_90_day_usd": round(annual_drug, 2),
            "annual_mailer_cost_45_day_usd": round(annual_mailer_45, 2),
            "annual_mailer_cost_90_day_usd": round(annual_mailer_90, 2),
            "annual_payment_45_day_usd": round(annual_pay_45, 2),
            "annual_payment_90_day_usd": round(annual_pay_90, 2),
            "annual_margin_45_day_usd": round(margin_45, 2),
            "annual_margin_90_day_usd": round(margin_90, 2),
            "annual_margin_difference_90_minus_45_usd": round(diff, 2)
        })

    total_margin_45 = round(sum(m["annual_margin_45_day_usd"] for m in medications), 2)
    total_margin_90 = round(sum(m["annual_margin_90_day_usd"] for m in medications), 2)
    total_diff = round(total_margin_90 - total_margin_45, 2)
    abs_total_diff = round(abs(total_diff), 2)

    decision = "switch_to_90_day" if abs_total_diff < threshold else "keep_45_day"

    result = {
        "assumptions": {
            "patients_per_medication": PATIENTS,
            "fills_per_year_45_day": FILLS_45,
            "fills_per_year_90_day": FILLS_90,
            "doses_per_fill_45_day": DOSES_45,
            "doses_per_fill_90_day": DOSES_90,
            "switch_threshold_usd": threshold
        },
        "medications": medications,
        "totals": {
            "annual_margin_45_day_usd": total_margin_45,
            "annual_margin_90_day_usd": total_margin_90,
            "absolute_difference_usd": abs_total_diff,
            "decision": decision
        }
    }

    json_path = os.path.join(base_dir, "mailer_policy_analysis.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)

    summary_path = os.path.join(base_dir, "mailer_policy_summary.md")
    with open(summary_path, "w") as f:
        f.write("# Mailer Policy Analysis Summary\n\n")
        f.write(f"- Total annual margin (45-day cycle): **${total_margin_45:,.2f}**\n")
        f.write(f"- Total annual margin (90-day cycle): **${total_margin_90:,.2f}**\n")
        f.write(f"- Absolute margin difference (90 − 45): **${abs_total_diff:,.2f}**\n")
        f.write(f"- Switch threshold: **${threshold:,.2f}**\n")
        f.write(f"- Decision: `{decision}`\n\n")
        f.write(f"The 90-day model {'reduces' if total_diff < 0 else 'increases'} total annual margin by ${abs_total_diff:,.2f}, {'exceeding' if abs_total_diff >= threshold else 'falling below'} the ${threshold:,.2f} threshold. {'Switch to 90-day fill cycle.' if decision == 'switch_to_90_day' else 'Keep the 45-day fill cycle.'}\n")

    print(f"Generated {json_path} and {summary_path}")

if __name__ == "__main__":
    main()