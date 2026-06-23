---
name: clinical-lab-harmonization
description: Harmonizes clinical lab CSV data by parsing mixed numeric formats (scientific notation, comma decimals), detecting and converting between SI and conventional units using physiological ranges, handling missing values, and standardizing decimal precision. Use when processing electrolyte/metabolic panel CSVs requiring unit normalization and validation.
---

# Clinical Lab Data Harmonization

## Workflow

1. **Parse & Clean**: Read CSV. Replace comma decimal separators (`"1,23"`) with dots using regex `\d,\d` → `\1.\2`. Parse scientific notation (`6.4372e+02` → `643.72`). Cast numeric columns to floats.

2. **Drop Incomplete Rows**: Remove rows with missing, empty, or `nan`/`NaN`/`None` values in any measurement column.

3. **Detect & Convert Alternate Units**:
   - For each analyte, test if value is outside plausible US conventional range:
   
   | Analyte | US Conventional Range | SI Range | Conversion (SI→Conv) |
   |---------|----------------------|----------|----------------------|
   | Glucose | 70–140 mg/dL (extend to 30–700 for DKA) | 3.9–7.8 mmol/L | × 18.0 |
   | Creatinine | 0.7–1.3 mg/dL (extend to 0.3–15) | 62–115 μmol/L | ÷ 88.4 |
   | Calcium | 8.5–10.5 mg/dL (extend to 6–12) | 2.1–2.6 mmol/L | × 4.0 |
   | Magnesium | 1.7–2.2 mg/dL (extend to 0.5–5) | 0.7–0.9 mmol/L | × 2.43 |
   
   - **Conversion direction**: Test both `value * factor` and `value / factor`. Keep the operation that places result inside plausible range.
   - Apply conversion only to out-of-range values. Leave pathological-but-plausible values unchanged (e.g., Glucose 500+ in DKA).

4. **Format & Output**: Round all numeric values to 2 decimal places. Drop identifier columns (`encounter_id`, `patient_id`). Write clean CSV with Unix line endings (`\n`).

5. **Validate Output**:
   - `file output.csv` must show `ASCII text` (not `with CRLF line terminators`)
   - `grep -E '[0-9]+e[+-]' output.csv` returns nothing (no scientific notation)
   - All numeric values match `^[0-9]+\.[0-9]{2}$` (exactly 2 decimal places)

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### electrolyte-metabolic-panel
- Output must have exactly 2 decimal places per numeric field
- Unix line endings (`\n`) only; strip `\r` if present
- Row count = original count minus dropped incomplete rows
- Sodium, Potassium, Chloride, Bicarbonate: no unit conversion needed (mmol/L = mEq/L)

## Anti-Patterns

- **Blind multiplication**: Never assume the provided factor is a direct multiplier. Always test both directions against physiological ranges.
- **Over-conversion**: Do not convert values that are high/low but clinically possible. Use extended ranges (Glucose 30–700, Creatinine 0.3–15).
- **Naive comma regex**: `[0-9],[0-9]` matches CSV delimiters. Use `\d,\d` or column-aware parsing.
- **CRLF line endings**: Verify with `file output.csv` before submitting.
- **Rounding before conversion**: Parse and convert first, then round. Rounding before conversion corrupts threshold detection.
- **Python environment**: Use `python3` explicitly.

## Troubleshooting

- If values seem 100× off: verify conversion factor direction (multiply vs divide)
- If verifier fails on precision: ensure rounding happens after all conversions
- If line ending failure: run `sed -i 's/\r$//' output.csv`
