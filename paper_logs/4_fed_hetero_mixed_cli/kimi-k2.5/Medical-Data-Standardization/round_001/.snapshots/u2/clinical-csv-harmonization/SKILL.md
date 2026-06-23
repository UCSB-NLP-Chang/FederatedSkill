---
name: clinical-csv-harmonization
description: Harmonizes clinical lab CSV data by parsing mixed number formats (scientific notation, comma decimals), detecting and converting between SI and US conventional units using physiological range testing, handling missing values, and standardizing to exact 2-decimal precision. Use for electrolyte panels, metabolic profiles, or any lab CSV requiring unit normalization.
---

# Clinical CSV Data Harmonization

## When to use
- Input data mixes scientific notation (`1.5e+02`) with European decimal commas (`142,0205`)
- Must detect and convert between SI units (mmol/L, μmol/L) and conventional units (mg/dL) per analyte
- Required to drop incomplete records, remove identifier columns, and enforce exact decimal precision
- Target format requires Unix line endings and specific column ordering

## Workflow

### 1. Parse Input Formats
- **Scientific notation**: Parse strings matching `[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)`
- **European decimals**: Replace comma with dot *only when comma appears between digits*: `re.sub(r'(\d),(\d)', r'\1.\2', s)`
  - Do NOT use naive regex `[0-9],[0-9]` on whole lines - this matches CSV delimiters
- **Missing values**: Treat empty strings, `nan`, `NaN`, `NULL`, `None` as missing; drop entire row if any analyte is missing

### 2. Detect Unit System & Convert
For each value, use bidirectional testing against physiological ranges:

| Analyte | Conventional Range (mg/dL) | SI Range (mmol/L or μmol/L) | Factor (SI→Conv) |
|---------|---------------------------|------------------------------|------------------|
| Glucose | 70–140 (extended: 30–700) | 3.9–7.8 (extended: 1.7–39) | ×18.0 |
| Creatinine | 0.7–1.3 (extended: 0.3–15) | 62–115 (extended: 27–1326) | ÷88.4 |
| Calcium | 8.5–10.5 (extended: 6–12) | 2.1–2.6 (extended: 1.5–3) | ×4.0 |
| Magnesium | 1.7–2.2 (extended: 0.5–5) | 0.7–0.9 (extended: 0.2–2) | ×2.43 |

**Conversion decision rule (bidirectional testing)**:
1. Test both `value * factor` and `value / factor`
2. Keep the operation that places the result inside the extended plausible range
3. If both fall in range (overlap zone), prefer conventional (mg/dL) unless column statistics suggest otherwise
4. Do NOT convert pathological-but-plausible values (e.g., Glucose 500+ mg/dL in DKA)

### 3. Format & Write Output
- Round all numeric values to exactly 2 decimal places: `round(value, 2)`
- Format output as string with exactly 2 decimals: `f"{value:.2f}"`
- Explicitly write Unix line endings (`\n`); strip `\r` if present: `sed -i 's/\r$//' output.csv`
- Remove identifier columns (e.g., `encounter_id`) while preserving measurement column order
- Use dot decimal separator exclusively

### 4. Validation (Critical)
Run these checks before submitting:
1. **Line endings**: `file output.csv` must show `ASCII text`, not `with CRLF line terminators`
2. **No comma decimals**: Parse CSV properly - `cut -d',' -f2 output.csv | grep ','` should return nothing (check numeric columns only)
3. **Decimal precision**: All numeric values must match pattern `^[0-9]+\.[0-9]{2}$` (exactly 2 decimal places)
4. **Plausibility**: No value should be >10× physiological max after conversion (indicates wrong unit direction)
5. **Row count**: Output rows = input rows - dropped rows (no extra/missing)

## Anti-patterns (Avoid)

- **Do not** use naive regex `[0-9],[0-9]` to detect comma decimals across entire lines - this matches `142.02` when followed by comma delimiter in CSV
- **Do not** assume conversion factor direction - test both multiply and divide, keep result in plausible range
- **Do not** round before unit conversion - parse first, convert, then round (affects threshold detection)
- **Do not** convert values that are high/low but clinically possible (e.g., Glucose 500+ mg/dL in DKA, Creatinine 10+ mg/dL in AKI)
- **Do not** assume all values in a column share the same unit system - evaluate per cell due to mixed source data
- **Do not** use `python` command; use `python3` explicitly
- **Do not** validate decimal precision with `awk` without stripping `\r` first - carriage returns attach to final field

## Output precision
Never round, truncate, or fixed-format numeric values beyond the required 2 decimal places. Pass raw float values through the workflow and round only at final output. Concretely:
- DO NOT: `round(x, 1)`, `format(x, ".1f")`, `f"{x:.1f}"`, `.toFixed(1)`
- DO: `round(value, 2)` then `f"{value:.2f}"` for exactly 2 decimal places
- The verifier requires exactly 2 decimal precision; give it exactly that.

## Known invariants (by sub-task)

### electrolyte-metabolic-panel
- Output must use Unix line endings (`\n`), not CRLF
- Identifier column `encounter_id` must be removed
- All numeric values must have exactly 2 decimal places (no more, no less)
- Common analytes: Glucose, Creatinine, Calcium, Magnesium (convertible); Sodium, Potassium, Chloride, Bicarbonate (no conversion needed, 1:1)
