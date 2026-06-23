# Fuzzy Matching Guide for Name Validation

## Algorithm Selection

**Use Levenshtein Distance (Edit Distance)**
- Install: `pip install python-Levenshtein` or `pip install rapidfuzz`
- Why: Handles insertions/deletions better than sequence-based ratios
- Example: "Briann Ortega" vs "Brian Ortega"
  - Simple ratio: ~50% (fails)
  - Levenshtein ratio: ~92% (passes)

## Threshold Guidelines

| Threshold | Behavior | Use Case |
|-----------|----------|----------|
| 95% | Very strict; allows only 1-2 char differences in short names | High-security financial transfers |
| 90% | **Recommended**; catches single typos, transpositions | Standard expense claims |
| 85% | Permits 2-3 char differences; more false positives | Noisy OCR sources |
| 80% | Lenient; use only for discovery/initial matching | Data cleanup phases |

## Implementation Pattern

```python
from Levenshtein import ratio

def find_best_match(query: str, candidates: list, threshold: float = 0.90):
    query_norm = query.strip().lower()
    best_score = 0.0
    best_match = None

    for candidate in candidates:
        score = ratio(query_norm, candidate.lower())
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= threshold:
        return best_match, best_score
    return None, best_score
```

## Edge Cases

**Transpositions** (swapped letters)
- "Dana Kapor" vs "Dana Kapoor": 91% similarity (insertion)
- Handle by preprocessing: remove double letters? No, keep original and rely on Levenshtein.

**Missing Spaces**
- "AliceChen" vs "Alice Chen": Calculate both with/space insertion? Levenshtein handles at ~85%.

**Middle Names**
- "John Michael Smith" vs "John Smith": 67% similarity.
- **Strategy**: Tokenize and check if all claimed tokens exist in reference (order-independent subset).

## Debugging Mismatches

When a name should match but doesn't:

1. Print the similarity scores for top 3 candidates
2. Check for invisible characters (\xa0 non-breaking spaces)
3. Verify case normalization (Turkish i, German ß)
4. Check encoding issues (mojibake from PDF extraction)

## Anti-Patterns

- **Don't use `difflib.SequenceMatcher`** for typo-heavy data; it's slower and less accurate for insertions
- **Don't tokenize and compare word-by-word** unless handling middle name variations specifically
- **Don't cache fuzzy matches permanently** without human review; typos may indicate data quality issues

## Validation Examples

| Claimed Name | Directory Name | Similarity | Result |
|--------------|----------------|------------|--------|
| Alice Chenn | Alice Chen | 90.9% | Match |
| Dana Kapor | Dana Kapoor | 90.9% | Match |
| Briann Ortega | Brian Ortega | 92.3% | Match |
| Lucas Grey | (not in directory) | Best: 33% | Unknown |
| Miguel Santoz | Miguel Santos | 87.0% | Review* |

\* Below 90% threshold; flag for manual review or lower threshold if data quality is poor.
