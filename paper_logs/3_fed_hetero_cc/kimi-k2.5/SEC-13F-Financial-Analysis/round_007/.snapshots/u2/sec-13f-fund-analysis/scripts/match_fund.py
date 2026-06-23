#!/usr/bin/env python3
"""
Match a fund query to the closest FILINGMANAGER_NAME in 13F COVERPAGE data
with threshold validation to prevent false matches.

Usage:
    python match_fund.py "renaissance technologies" COVERPAGE.tsv
"""

import csv
import re
import sys
import json
from typing import List, Tuple, Optional, Dict


SUFFIXES = [
    'llc', 'lp', 'ltd', 'inc', 'corp', 'corporation', 'company', 'co',
    'partners', 'management', 'advisors', 'capital', 'group', 'holdings',
    'limited', 'plc', 'sa', 'nv', 'bv', 'gmbh', 'ag', 'kk', 'pte', 'sarl'
]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings."""
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


def normalize_name(name: str) -> str:
    """Normalize company name for comparison."""
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    words = name.split()
    while words and words[-1] in SUFFIXES:
        words.pop()
    return ' '.join(words)


def find_best_match(query: str, coverpage_path: str, max_distance: int = 4) -> Dict:
    """
    Find best matching manager for query with threshold validation.

    Returns dict with match info or None if no acceptable match found.
    """
    normalized_query = normalize_name(query)

    candidates: List[Tuple[int, str, str, str]] = []
    with open(coverpage_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            manager_name = row['FILINGMANAGER_NAME']
            normalized = normalize_name(manager_name)
            distance = levenshtein_distance(normalized_query, normalized)
            accession = row['ACCESSION_NUMBER']
            candidates.append((distance, manager_name, normalized, accession))

    candidates.sort(key=lambda x: (x[0], x[1]))

    if not candidates:
        return {
            'matched_manager': None,
            'accession_number': None,
            'distance': None,
            'confidence': 'none',
            'reason': 'no candidates found'
        }

    best = candidates[0]
    distance = best[0]

    if distance <= 2:
        confidence = 'high'
    elif distance <= 4:
        confidence = 'marginal'
    else:
        confidence = 'low'

    if distance > max_distance:
        return {
            'matched_manager': None,
            'accession_number': None,
            'distance': distance,
            'confidence': confidence,
            'reason': f'distance {distance} exceeds threshold {max_distance}',
            'top_candidates': [{'name': c[1], 'distance': c[0]} for c in candidates[:5]]
        }

    return {
        'matched_manager': best[1],
        'normalized_manager': best[2],
        'accession_number': best[3],
        'distance': distance,
        'confidence': confidence
    }


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <query> <coverpage.tsv> [max_distance]", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    coverpage_path = sys.argv[2]
    max_distance = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    result = find_best_match(query, coverpage_path, max_distance)
    print(json.dumps(result, indent=2))