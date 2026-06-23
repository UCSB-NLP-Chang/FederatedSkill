---
name: sec-13f-alert-processing
description: Process deduplicated alert packs containing multiple SEC 13F analysis requests. Use when given a batch of alerts with types like issuer_top_holders, fund_change, ignore_me, etc. Handles alert deduplication (keep first occurrence), type filtering, and aggregates results into a unified output structure.
---

# SEC 13F Alert Pack Processor

Process batches of alerts with deduplication and type filtering, delegating to appropriate analysis skills.

## Input Format

Alert packs contain multiple alert objects with structure:
```json
[
  {"type": "issuer_top_holders", "issuer_query": "palantir", "quarter": "2025-q3", "top_n": 3},
  {"type": "fund_change", "fund_query": "tiger global", "quarter_current": "2025-q3", "quarter_baseline": "2025-q2"},
  {"type": "ignore_me", ...}
]
```

## Workflow

### 1. Deduplicate Alerts

For each alert type, keep only the **first occurrence** by `(type, key_identifiers)`:
- `issuer_top_holders`: dedupe by `(type, issuer_query, quarter)`
- `fund_change`: dedupe by `(type, fund_query, quarter_current, quarter_baseline)`
- `ignore_me`: skip entirely (do not include in output)

### 2. Route to Analysis Skills

| Alert Type | Skill | Script/Method |
|------------|-------|---------------|
| `issuer_top_holders` | sec-13f-issuer-rollup | `scripts/issuer_rollup.py <issuer> <infotable> <coverpage> <top_n>` |
| `fund_change` | sec-13f-fund-analysis | B3 cross-quarter comparison workflow |
| `ignore_me` | - | Skip, no output |

### 3. Handle Missing Baseline (B3-Single Schema)

When fund matching fails semantic check for baseline quarter:

1. Verify match failure: distance > 4 OR key word from query absent in matched name
2. Output B3-Partial schema:
   ```json
   {
     "fund_query_current": "...",
     "quarter_current": "...",
     "fund_query_baseline": "...",
     "quarter_baseline": "...",
     "largest_buy_cusip": "<largest_current_position>",
     "largest_sell_cusip": "",
     "baseline_missing": true
   }
   ```
3. Get largest current position: run `classify_holdings.py` on current quarter, take `top3_cusips[0]`

### 4. Aggregate Output

Group results by alert type in final JSON:
```json
{
  "issuer_top_holders": [...],
  "fund_change": [...]
}
```

## Critical Validation Rules

### Semantic Match Check (MANDATORY)
After finding best Levenshtein match, verify:
1. Extract key identifying words from query (e.g., "tiger" from "tiger global")
2. Check if at least one key word appears in matched manager name
3. If NO key word match -> **reject match** even if distance <= 4

**Example rejections:**
- Query "tiger global" -> Match "Voyager Global Management LP" (distance=4, but no "tiger") -> **REJECT**
- Query "renaissance technologies" -> Match "Headlands Technologies" (distance=7, no "renaissance") -> **REJECT**

### Missing Baseline Decision Tree
```
Fund found in current quarter?
|-- NO -> Output matched_manager: null
|-- YES -> Fund found in baseline quarter?
    |-- NO (or rejected match) -> B3-Partial schema
    |-- YES -> Standard B3 comparison
```

## Anti-patterns

- **Do NOT accept matches solely on Levenshtein distance** -- always run semantic check
- **Do NOT output null for largest_sell_cusip in B3-Partial** -- use empty string ""
- **Do NOT skip deduplication** -- downstream verifiers expect unique alert results
- **Do NOT include ignored alert types in output** -- filter before processing
- **Do NOT use awk with fixed column indices** for TSV parsing. SEC filing column positions vary. Use Python scripts with DictReader or provided helpers.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: pass raw floats directly to output
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Scripts

- `scripts/dedupe_alerts.py <alerts.json>`: Deduplicate alert pack by type+identifiers
- `scripts/validate_match.py <query> <matched_name>`: Semantic validation beyond Levenshtein

## References

- `references/alert-schemas.md`: Full output schemas for each alert type
- `references/dedup-rules.md`: Deduplication key extraction by alert type