#!/usr/bin/env python3
"""Manager name matching for SEC 13F filings with quality thresholds."""

import csv
import re
import sys

def normalize_name(name):
    """Normalize manager name for comparison."""
    name = name.lower()
    # Remove common suffixes
    for suffix in [' llc', ' inc', ' corp', ' ltd', ' co', ' lp', ' l.p.', ' s.a.', ' plc', ' limited', ' company', ' corporation']:
        name = name.replace(suffix, '')
    # Remove punctuation and extra spaces
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = ' '.join(name.split())
    return name

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
    Find best matching manager name.

    Args:
        query: Search term
        coverpage_path: Path to COVERPAGE.tsv
        max_acceptable_distance: Maximum distance to accept (default 4)

    Returns:
        dict with 'name', 'accession', 'distance', 'confidence' keys
        or None if no acceptable match found
    """
    query_norm = normalize_name(query)

    candidates = []
    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            name = row.get('FILINGMANAGER_NAME', '')
            accession = row.get('ACCESSION_NUMBER', '')
            name_norm = normalize_name(name)
            dist = levenshtein_distance(query_norm, name_norm)
            candidates.append({
                'name': name,
                'accession': accession,
                'distance': dist
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
        print("Usage: match_manager.py <query> <coverpage.tsv>")
        sys.exit(1)

    query = sys.argv[1]
    coverpage_path = sys.argv[2]

    result = find_best_match(query, coverpage_path)
    print(f"Query: {query}")
    print(f"Normalized: {normalize_name(query)}")
    print(f"Match: {result['name']}")
    print(f"Accession: {result['accession']}")
    print(f"Distance: {result['distance']}")
    print(f"Confidence: {result['confidence']}")