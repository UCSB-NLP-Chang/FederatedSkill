#!/usr/bin/env python3
"""Issuer ownership rollup: find all managers holding a specific issuer."""

import csv
import sys
import json
from collections import defaultdict


def find_cusip_for_issuer(infotable_path: str, issuer_query: str) -> tuple[str | None, list[str]]:
    """
    Find the canonical CUSIP for an issuer by searching NAMEOFISSUER.

    Returns (cusip, list_of_matching_names) or (None, []) if not found.
    """
    issuer_lower = issuer_query.lower()
    cusip_counts = defaultdict(int)
    matching_names = set()

    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            name = row.get('NAMEOFISSUER', '').strip()
            if issuer_lower in name.lower():
                cusip = row.get('CUSIP', '').strip()
                if cusip:
                    cusip_counts[cusip] += 1
                    matching_names.add(name)

    if not cusip_counts:
        return None, []

    # Return the most common CUSIP (should be consistent for a single issuer)
    best_cusip = max(cusip_counts.keys(), key=lambda c: cusip_counts[c])
    return best_cusip, list(matching_names)[:5]  # Return sample of matching names


def aggregate_by_accession(infotable_path: str, cusip: str) -> dict[str, float]:
    """
    Aggregate VALUE by ACCESSION_NUMBER for a specific CUSIP.

    Returns dict mapping accession -> total value (raw, no scaling).
    """
    accession_values = defaultdict(float)

    with open(infotable_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('CUSIP', '').strip() != cusip:
                continue

            accession = row.get('ACCESSION_NUMBER', '').strip()
            val_str = row.get('VALUE', '0').strip()
            try:
                val = float(val_str)
            except ValueError:
                val = 0.0

            accession_values[accession] += val

    return dict(accession_values)


def get_manager_names(coverpage_path: str, accessions: list[str]) -> dict[str, str]:
    """
    Map accession numbers to manager names.

    Returns dict mapping accession -> manager name.
    """
    accession_to_name = {}
    accessions_set = set(accessions)

    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            accession = row.get('ACCESSION_NUMBER', '').strip()
            if accession in accessions_set:
                name = row.get('FILINGMANAGER_NAME', '').strip()
                accession_to_name[accession] = name

    return accession_to_name


def issuer_rollup(issuer_query: str, infotable_path: str, coverpage_path: str, top_n: int = 5) -> dict:
    """
    Find all managers holding a specific issuer, ranked by value.

    Returns dict with issuer_query, cusip, top_n_managers, top_n_accessions.
    """
    # Step 1: Find CUSIP
    cusip, sample_names = find_cusip_for_issuer(infotable_path, issuer_query)

    if not cusip:
        return {
            "issuer_query": issuer_query,
            "cusip": None,
            "top5_managers": [],
            "top5_accessions": [],
            "error": "Issuer not found"
        }

    # Step 2: Aggregate by accession
    accession_values = aggregate_by_accession(infotable_path, cusip)

    # Step 3: Sort by value descending
    sorted_accessions = sorted(accession_values.items(), key=lambda x: x[1], reverse=True)
    top_accessions = [acc for acc, val in sorted_accessions[:top_n]]

    # Step 4: Map to manager names
    accession_to_manager = get_manager_names(coverpage_path, top_accessions)

    # Build ordered lists
    top_managers = [accession_to_manager.get(acc, "UNKNOWN") for acc in top_accessions]

    return {
        "issuer_query": issuer_query,
        "cusip": cusip,
        f"top{top_n}_managers": top_managers,
        f"top{top_n}_accessions": top_accessions
    }


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: issuer_rollup.py <issuer_query> <infotable.tsv> <coverpage.tsv> [top_n]", file=sys.stderr)
        sys.exit(1)

    issuer_query = sys.argv[1]
    infotable_path = sys.argv[2]
    coverpage_path = sys.argv[3]
    top_n = int(sys.argv[4]) if len(sys.argv) > 4 else 5

    result = issuer_rollup(issuer_query, infotable_path, coverpage_path, top_n)
    print(json.dumps(result, indent=2))