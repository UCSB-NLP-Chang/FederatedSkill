#!/usr/bin/env python3
"""Manager name matching for SEC 13F filings with quality thresholds."""

import csv
import re
import sys


SUFFIXES = [
    'llc', 'lp', 'ltd', 'inc', 'corp', 'corporation', 'company', 'co',
    'partners', 'management', 'advisors', 'capital', 'group', 'holdings',
    'limited', 'plc', 'sa', 'nv', 'bv', 'gmbh', 'ag', 'kk', 'pte', 'sarl'
]


def normalize_name(name):
    """Normalize manager name for comparison."""
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    words = name.split()
    while words and words[-1] in SUFFIXES:
        words.pop()
    return ' '.join(words)


def levenshtein_distance(s1, s2):
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_best_match(query, coverpage_path, max_acceptable_distance=4):
    """
    Find best matching manager name with threshold validation.

    Args:
        query: Search term
        coverpage_path: Path to COVERPAGE.tsv
        max_acceptable_distance: Maximum distance to accept (default 4)

    Returns:
        dict with 'name', 'accession', 'distance', 'confidence' keys
        or None dict if no acceptable match found
    """
    query_norm = normalize_name(query)

    candidates = []
    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            manager_name = row.get('FILINGMANAGER_NAME', '')
            accession = row.get('ACCESSION_NUMBER', '')
            name_norm = normalize_name(manager_name)
            dist = levenshtein_distance(query_norm, name_norm)
            candidates.append({
                'name': manager_name,
                'accession': accession,
                'distance': dist,
                'normalized': name_norm
            })

    candidates.sort(key=lambda x: (x['distance'], x['name']))
    best = candidates[0] if candidates else None

    if best and best['distance'] <= max_acceptable_distance:
        best['confidence'] = 'high' if best['distance'] <= 2 else 'marginal'
        return best

    # No acceptable match
    return {
        'name': None,
        'accession': None,
        'distance': best['distance'] if best else None,
        'confidence': 'none',
        'top_candidates': candidates[:5] if candidates else []
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: match_manager.py <query> <coverpage.tsv>", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    coverpage_path = sys.argv[2]

    result = find_best_match(query, coverpage_path)

    print(f"Query: {query}")
    print(f"Normalized query: {normalize_name(query)}")
    if result['name']:
        print(f"Matched manager: {result['name']}")
        print(f"Accession number: {result['accession']}")
        print(f"Distance: {result['distance']}")
        print(f"Confidence: {result['confidence']}")
    else:
        print("No acceptable match found.")
        print(f"Best distance: {result['distance']}")
        if result['top_candidates']:
            print("Top candidates:")
            for c in result['top_candidates']:
                print(f"  - {c['name']} (distance={c['distance']})")