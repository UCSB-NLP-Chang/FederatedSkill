# Manager Matching Strategies

## Matching Order (apply sequentially, stop at first match)

1. **Exact Match**: Normalized query equals normalized manager name.
2. **Substring Match**: Query is substring of manager or vice versa.
3. **Word-Level Match**: Significant word intersection using Jaccard with stop-word filtering.
4. **Fuzzy Match**: SequenceMatcher ratio > 0.9 (high threshold to avoid false positives).

## Stop Words (Critical)

Words treated as generic noise for overlap calculation:

```python
stop_words = {
    # Articles/prepositions
    'the', 'and', 'of', 'in',
    # Legal entities
    'llc', 'inc', 'ltd', 'corp', 'lp', 'company', 'co',
    # Generic financial terms
    'global', 'asset', 'assets', 'wealth', 'financial', 'services', 'solutions',
    'management', 'advisory', 'investment', 'capital', 'group', 'partners',
    'associates', 'holdings', 'trust', 'fund', 'funds', 'advisors'
}
```

**Critical**: Two funds sharing only stop words (e.g., both contain "Global Management") are **not** necessarily matches. Require at least one distinctive term overlap or high fuzzy similarity.

## Word-Level Matching Details

### Algorithm
```python
def word_overlap_score(query_norm, candidate_norm):
    stop_words = {'the', 'and', 'of', 'global', 'asset', 'assets', 'wealth', 
                  'financial', 'management', 'advisory', 'investment', 'llc', 'inc'}
    query_words = set(query_norm.split()) - stop_words
    candidate_words = set(candidate_norm.split()) - stop_words
    if not query_words or not candidate_words:
        return 0.0
    intersection = query_words & candidate_words
    union = query_words | candidate_words
    return len(intersection) / len(union)
```

### Examples

| Query | Candidate | Shared Words | Valid Match? | Reason |
|-------|-----------|--------------|--------------|--------|
| `elliott associates` | `jvl associates llc` | `associates` | Yes | Valid stop word overlap + substring |
| `third point` | `third point llc` | N/A | Yes | Exact normalized match |
| `scion asset management` | `sycomore asset management` | `asset`, `management` | **NO** | Only generic stop words shared; distinct firms |
| `tiger global` | `voyager global management` | `global` | **NO** | Only generic word shared; distinct firms |
| `peak xv` | `peak xv partners` | `peak`, `xv` | Yes | Distinctive terms match |

## High-Risk Match Patterns (Explicitly Reject)

These patterns indicate likely false positives:

1. **Generic-only overlap**: Intersection contains only words from stop_words list
   - `Kinetic Partners` vs `Tiger Global` (shares "Partners/Group-like" meaning but distinct)
   - `Sycomore Asset` vs `Scion Asset` (shares "Asset" but distinct firms)

2. **Phonetic similarity without lexical overlap**: 
   - `Scion` vs `Sycomore` sound similar but share no letters; fuzzy matching without word overlap is dangerous
   - Require either high fuzzy (>0.9) AND at least 3+ character substring shared, OR word overlap with distinctive terms

3. **Case-insensitive substring traps**:
   - `grep -i "tiger"` matches "Tigertail Avenue" (address field, not manager name)
   - Always normalize before substring matching

## Fuzzy Matching Thresholds

- **Accept**: ratio > 0.90 and substantial character overlap (>= 4 consecutive characters shared)
- **Reject**: ratio <= 0.90 or < 50% character overlap
- **High risk**: manager names with <= 10 characters total (short names have inflated ratios)

## Handler for Ambiguous Cases

When word overlap yields multiple candidates with similar scores:
1. Prefer candidate where query is substring of normalized name
2. Prefer candidate with highest fuzzy ratio among word-matched candidates
3. If fuzzy spread < 0.05 between top two, report ambiguity error rather than guessing

## Implementation Checklist

- [ ] Stop words filtered from word-overlap calculation
- [ ] Generic-only overlaps rejected
- [ ] Fuzzy threshold >= 0.9
- [ ] Short name (< 10 chars) handling with stricter thresholds
- [ ] Verification step ensuring matched manager passes sanity check against known fund list if available