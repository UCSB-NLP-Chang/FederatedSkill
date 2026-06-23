# Manager Matching Strategies

## Matching Order (apply sequentially, stop at first match)

1. **Exact Match**: Normalized query equals normalized manager name.
2. **Substring Match**: Query is substring of manager or vice versa.
3. **Word-Level Match**: Any word from the query appears as a complete word in the manager name (or vice versa).
4. **Fuzzy Match**: SequenceMatcher ratio > 0.85.

## Word-Level Matching Details

Word-level matching bridges the gap between substring and fuzzy matching. It catches cases where the query and manager share a meaningful word but neither is a substring of the other.

### Algorithm
```python
def word_level_match(query_words, manager_words):
    query_set = set(query_words)
    manager_set = set(manager_words)
    return bool(query_set & manager_set)
```

### Examples

| Query | Manager Name | Shared Word | Match? |
|-------|-------------|-------------|--------|
| `elliott associates` | `jvl associates llc` | `associates` | Yes |
| `capital management` | `boyar asset management inc` | `management` | Yes |
| `wealth advisors` | `lantern wealth advisors llc` | `wealth`, `advisors` | Yes |
| `peak xv` | `peak xv partners v ltd` | `peak`, `xv` | Yes |

### When to Use
- Use word-level matching when the task expects a resolved manager but exact/substring matching fails.
- Do NOT use word-level matching for single-word queries where the word is too common (e.g., "capital", "management", "advisors") unless combined with other signals.
- If multiple managers share the same word, prefer the one with the highest fuzzy ratio among word-matched candidates.

## Fuzzy Matching Thresholds

- **High confidence**: ratio > 0.90 — accept immediately
- **Medium confidence**: 0.85 < ratio <= 0.90 — accept if no better match exists
- **Low confidence**: ratio <= 0.85 — reject unless task explicitly requires best-effort resolution

## Anti-Patterns

- Do NOT force the closest Levenshtein match when ratio < 0.85 — it yields false positives (e.g., "Headlands" → "Renaissance").
- Do NOT skip word-level matching — many real-world queries resolve via shared words.
- Do NOT use substring matching on untokenized strings — `ISHARES` contains `share` but is not a stock.
