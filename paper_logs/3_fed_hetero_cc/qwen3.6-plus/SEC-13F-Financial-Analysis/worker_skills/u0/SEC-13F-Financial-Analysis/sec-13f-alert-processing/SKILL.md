---
name: sec-13f-alert-processing
description: Process, deduplicate, and route batches of SEC 13F filing alerts to the correct analysis sub-skills. Use when given a list of alerts containing `issuer_top_holders`, `fund_change`, or other 13F query types that require deduplication, distractor filtering, and schema assembly. Also use when filling structured JSON report templates with 13F-derived data.
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

## Template-Filling Workflow

When the task requires filling a pre-existing JSON template (e.g., `brief_template.json`):

1. **Load the template first** — read it before computing any values to understand the required schema, section order, and item order.
2. **Compute values using scripts only** — do NOT write inline Python for aggregation, comparison, or matching. Use the scripts provided in sub-skills.
3. **Preserve template structure exactly** — maintain section order, item order, key names, and any `notes` arrays unchanged.
4. **Verify structural match** — after writing output, run a quick structural comparison against the template to confirm keys, order, and array lengths match.
5. **Verify value precision** — ensure numeric values are raw floats, not rounded or formatted strings.

## Anti-Patterns
- **Do NOT use `awk` with fixed column indices** for TSV parsing. SEC filing column positions vary (e.g., empty FIGI fields shift VALUE). Always use `csv.DictReader` or provided Python scripts.
- **Do NOT skip deduplication**. Identical alerts must be merged; only process unique queries.
- **Do NOT process distractors**. Skip alerts explicitly marked as test/ignore or containing invalid identifiers.
- **Do NOT manually compute aggregates**. Use `rollup_issuer.py` and `compare_quarters.py` to ensure correct VALUE scaling and header-aware parsing.
- **Do NOT write inline Python for issuer rollup, fund matching, or cross-quarter comparison**. The scripts are validated; inline code is not and causes verification failure.
- **Do NOT modify template structure**. Preserve section order, item order, key names, and notes arrays exactly as in the template.

## Validation
- Verify CUSIPs are exactly 9 characters.
- Confirm deduplicated count matches expected unique queries.
- Ensure output JSON keys match the alert types present in the input.
- For template-filling: verify structural match (keys, order, array lengths) against the original template.
- For template-filling: verify numeric values are raw floats, not strings or rounded values.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Test fails despite correct-looking output | Used awk or inline Python instead of scripts | Re-run using `rollup_issuer.py`, `compare_quarters.py`, or `match_manager.py` |
| VALUE sums are off by 1000x | Forgot to multiply by 1000 (SEC reports in thousands) | Apply `* 1000` scaling to all VALUE aggregations |
| Wrong manager matched | Distance > 4 or semantic mismatch | Enforce distance ≤ 4 threshold; run semantic sanity-check |
| Template structure mismatch | Modified section/item order or key names | Load template first; write values into existing structure without reordering |
| CUSIP lookup returns wrong results | Used awk with fixed column indices | Use `csv.DictReader` or Python with header-aware parsing |