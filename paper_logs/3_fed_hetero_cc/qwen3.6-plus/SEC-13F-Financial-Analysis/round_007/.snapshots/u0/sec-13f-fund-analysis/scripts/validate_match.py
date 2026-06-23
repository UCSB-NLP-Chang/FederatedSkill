#!/usr/bin/env python3
"""Validate fund match beyond Levenshtein distance with semantic check."""

import sys
import json
import re


def normalize(text):
    """Normalize text for comparison."""
    return re.sub(r'[^\w]', '', text.lower())


def extract_key_words(query):
    """Extract key identifying words from query."""
    # Common suffixes to ignore when extracting key words
    suffixes = {'llc', 'lp', 'ltd', 'inc', 'corp', 'corporation', 'company', 'co',
                'partners', 'management', 'advisors', 'capital', 'group', 'holdings',
                'limited', 'global', 'international', 'investments', 'fund'}

    words = query.lower().split()
    key_words = [w for w in words if w not in suffixes and len(w) > 2]
    return key_words


def semantic_check(query, matched_name):
    """Check if key words from query appear in matched name."""
    key_words = extract_key_words(query)
    matched_lower = matched_name.lower()

    matches = []
    for word in key_words:
        if word in matched_lower:
            matches.append(word)

    return {
        "key_words": key_words,
        "matches_found": matches,
        "match_ratio": len(matches) / len(key_words) if key_words else 0,
        "passed": len(matches) > 0
    }


def validate_match(query, matched_name, distance=None):
    """Full validation including semantic check."""
    semantic = semantic_check(query, matched_name)

    result = {
        "query": query,
        "matched_name": matched_name,
        "distance": distance,
        "semantic_check": semantic,
        "acceptable": semantic["passed"] and (distance is None or distance <= 4)
    }

    if not semantic["passed"]:
        result["rejection_reason"] = f"No key words ({semantic['key_words']}) found in match"
    elif distance is not None and distance > 4:
        result["rejection_reason"] = f"Distance {distance} exceeds threshold"

    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: validate_match.py <query> <matched_name> [distance]", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    matched_name = sys.argv[2]
    distance = int(sys.argv[3]) if len(sys.argv) > 3 else None

    result = validate_match(query, matched_name, distance)
    print(json.dumps(result, indent=2))