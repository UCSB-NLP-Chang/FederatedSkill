#!/usr/bin/env python3
"""
SEC 13F Issuer Ownership Rollup

Finds all managers holding a specific issuer/security and aggregates VALUE by manager.
Inverse of manager-centric workflows: instead of holdings for a manager, find managers for a holding.

Usage:
  python3 issuer_rollup.py <data_dir> <issuer_name_or_cusip> <quarter_date>

Arguments:
  data_dir: Path to quarter directory containing COVERPAGE.tsv and INFOTABLE.tsv
  issuer_name_or_cusip: Either issuer name (case-insensitive grep) or exact CUSIP
  quarter_date: Quarter date in DD-MON-YYYY format (e.g., 30-SEP-2025)

Output JSON to stdout.
"""
import csv
import json
import sys
import os
import re
from collections import defaultdict


def find_cusip_by_issuer(info_path, issuer_name):
    """Find CUSIP(s) for an issuer name using case-insensitive match on NAMEOFISSUER."""
    cusip_counts = defaultdict(int)
    issuer_lower = issuer_name.lower()

    with open(info_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            name_of_issuer = row.get('NAMEOFISSUER', '')
            if issuer_lower in name_of_issuer.lower():
                cusip = row.get('CUSIP', '')
                if cusip:
                    cusip_counts[cusip] += 1

    if not cusip_counts:
        return None

    # Return CUSIP with most matches
    return max(cusip_counts, key=cusip_counts.get)


def is_valid_cusip(s):
    """Check if string looks like a CUSIP (9 alphanumeric characters)."""
    return bool(re.match(r'^[A-Z0-9]{9}$', s.upper()))


def aggregate_by_accession(info_path, cusip):
    """Aggregate VALUE by ACCESSION_NUMBER for a given CUSIP."""
    accession_values = defaultdict(float)

    with open(info_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('CUSIP', '') == cusip:
                accession = row.get('ACCESSION_NUMBER', '')
                value_str = row.get('VALUE', '0')
                try:
                    value = float(value_str) if value_str else 0.0
                except ValueError:
                    value = 0.0
                accession_values[accession] += value

    return accession_values


def get_manager_names(cover_path, accessions):
    """Look up manager names for a set of accession numbers."""
    accession_to_manager = {}

    with open(cover_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            accession = row.get('ACCESSION_NUMBER', '')
            if accession in accessions:
                accession_to_manager[accession] = row.get('FILINGMANAGER_NAME', '')

    return accession_to_manager


def issuer_rollup(data_dir, issuer_or_cusip, quarter_date):
    """Perform issuer ownership rollup analysis."""
    cover_path = os.path.join(data_dir, 'COVERPAGE.tsv')
    info_path = os.path.join(data_dir, 'INFOTABLE.tsv')

    if not os.path.exists(cover_path):
        return {"error": f"COVERPAGE.tsv not found in {data_dir}", "issuer_query": issuer_or_cusip}
    if not os.path.exists(info_path):
        return {"error": f"INFOTABLE.tsv not found in {data_dir}", "issuer_query": issuer_or_cusip}

    # Determine if input is CUSIP or issuer name
    if is_valid_cusip(issuer_or_cusip):
        cusip = issuer_or_cusip.upper()
        issuer_query = issuer_or_cusip
    else:
        cusip = find_cusip_by_issuer(info_path, issuer_or_cusip)
        if not cusip:
            return {
                "error": f"No CUSIP found for issuer '{issuer_or_cusip}'",
                "issuer_query": issuer_or_cusip,
                "cusip": None
            }
        issuer_query = issuer_or_cusip

    # Aggregate VALUE by accession
    accession_values = aggregate_by_accession(info_path, cusip)

    if not accession_values:
        return {
            "error": f"No holdings found for CUSIP {cusip}",
            "issuer_query": issuer_query,
            "cusip": cusip
        }

    # Get manager names
    accession_to_manager = get_manager_names(cover_path, set(accession_values.keys()))

    # Sort by VALUE descending
    sorted_accessions = sorted(accession_values.items(), key=lambda x: x[1], reverse=True)

    # Build output
    top_managers = []
    top_accessions = []
    seen_managers = set()

    for accession, value in sorted_accessions:
        manager = accession_to_manager.get(accession, 'UNKNOWN')
        top_accessions.append(accession)
        if manager not in seen_managers:
            top_managers.append(manager)
            seen_managers.add(manager)
        if len(top_accessions) >= 5 and len(top_managers) >= 5:
            break

    return {
        "issuer_query": issuer_query,
        "quarter": quarter_date,
        "cusip": cusip,
        "top_managers": top_managers[:5],
        "top_accessions": top_accessions[:5],
        "total_value": sum(accession_values.values()),
        "holdings_count": len(accession_values)
    }


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: issuer_rollup.py <data_dir> <issuer_name_or_cusip> <quarter_date>", file=sys.stderr)
        print("Example: issuer_rollup.py 2025-q3 palantir 30-SEP-2025", file=sys.stderr)
        print("Example: issuer_rollup.py 2025-q3 69608A108 30-SEP-2025", file=sys.stderr)
        sys.exit(1)

    data_dir = sys.argv[1]
    issuer_or_cusip = sys.argv[2]
    quarter_date = sys.argv[3]

    result = issuer_rollup(data_dir, issuer_or_cusip, quarter_date)
    print(json.dumps(result, indent=2))
