---
name: sec-13f-alert-processing
description: Process, deduplicate, and route batches of SEC 13F filing alerts to the correct analysis sub-skills. Use when given a list of alerts containing `issuer_top_holders`, `fund_change`, or other 13F query types that require deduplication, distractor filtering, and schema assembly.
---

# SEC 13F Alert Processing & Routing

Handle batches of 13F filing alerts by deduplicating, filtering distractors, routing to the correct analysis skill, and assembling the final output.

## Workflow

1. **Parse & Deduplicate Alerts**
   - Read the alert list.
   - Remove exact duplicates based on alert type and query parameters.
   - Preserve first-seen order for output assembly.
   - Filter out distractors (e.g., alerts with `ignore_me`, invalid CUSIPs, or malformed queries).

2. **Route to Sub-Skills**
   - `issuer_top_holders` → Delegate to `sec-13f-issuer-rollup`.
     - Resolve company name/ticker to 9-digit CUSIP.
     - Run `python3 scripts/rollup_issuer.py` to get top managers by aggregated VALUE.
   - `fund_change` → Delegate to `sec-13f-fund-analysis` (B3 workflow).
     - Match fund in current and baseline quarters using `match_manager.py`.
     - If baseline missing, treat all current positions as new buys; largest buy = largest current position.
     - Run `compare_quarters.py` or compute largest buy/sell CUSIP.
   - Other types → Route to appropriate 13F analysis sub-skill.

3. **Assemble Output**
   - Group results by alert type.
   - Maintain original deduplicated order.
   - Output as a single JSON object with keys matching alert types (e.g., `issuer_top_holders`, `fund_change`).

## Anti-Patterns
- **Do NOT use `awk` with fixed column indices** for TSV parsing. SEC filing column positions vary (e.g., empty FIGI fields shift VALUE). Always use `csv.DictReader` or provided Python scripts.
- **Do NOT skip deduplication**. Identical alerts must be merged; only process unique queries.
- **Do NOT process distractors**. Skip alerts explicitly marked as test/ignore or containing invalid identifiers.
- **Do NOT manually compute aggregates**. Use `rollup_issuer.py` and `compare_quarters.py` to ensure correct VALUE scaling and header-aware parsing.

## Validation
- Verify CUSIPs are exactly 9 characters.
- Confirm deduplicated count matches expected unique queries.
- Ensure output JSON keys match the alert types present in the input.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.