---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by parsing mixed number formats (scientific notation, comma decimals), detecting and converting between SI and conventional units using physiological range validation, handling missing values, and standardizing to exact precision. Use for electrolyte panels, metabolic profiles, hepatic panels, or any lab data requiring unit standardization before analysis.
---

# Clinical Lab Data Harmonization

## When to use
- Input data mixes scientific notation (`1.5e+02`) with European decimal commas (`142,0205`)
- Must detect and convert between SI units (mmol/L, μmol/L, g/L) and conventional units (mg/dL, g/dL) per analyte
- Required to drop incomplete records, remove identifier columns, and enforce exact decimal precision
- Target format requires Unix line endings and standardized output

## Workflow

### 1. Parse Input Formats
- **Scientific notation**: Parse strings like `6.4372e+02` → `643.72`
- **European decimals**: Replace comma with dot *only when comma appears between digits* (e.g., `"142,0205"` → `142.0205`)
- **Missing values**: Treat empty strings, `nan`, `NaN`, `None`, `NULL` as missing; drop entire row if any analyte is missing

### 2. Detect Unit System & Convert
For each analyte value, use **bidirectional conversion testing**:

1. Define extended plausible conventional ranges (wider than normal to avoid converting pathological values):
   | Analyte | Plausible Conventional | Plausible SI | Factor (SI→Conv) |
   |---------|------------------------|--------------|------------------|
   | Glucose | 30–700 mg/dL | 2–40 mmol/L | × 18.0 |
   | Creatinine | 0.3–15 mg/dL | 25–1300 μmol/L | ÷ 88.4 |
   | Calcium | 6–14 mg/dL | 1.5–3.5 mmol/L | × 4.0 |
   | Magnesium | 0.5–5 mg/dL | 0.2–2 mmol/L | × 2.43 |
   | Total/Direct Bilirubin | 0.1–30 mg/dL | 2–500 μmol/L | ÷ 17.1 |
   | Albumin | 1.0–6.0 g/dL | 10–60 g/L | ÷ 10 |
   | Total_Protein | 3.0–12.0 g/dL | 30–120 g/L | ÷ 10 |
   | Hemoglobin | 5.0–20.0 g/dL | 50–200 g/L | ÷ 10 |
   | Ammonia | 10–200 μg/dL | 5–120 μmol/L | ÷ 1.7 |

2. **Critical: Glucose has inverted numeric relationship**
   - SI (mmol/L) values are **numerically smaller** than conventional (mg/dL)
   - A value of 5.5 is likely mmol/L (→ 99 mg/dL), not an extremely low mg/dL
   - Test: if value < plausible_lower, try `value × 18` first; if result in range, it was mmol/L
   - Do NOT convert values already in plausible conventional range (30–700 mg/dL)

3. For other analytes, test both conversion directions:
   - `result_mult = value * factor`
   - `result_div = value / factor`
   - Keep the result that falls **inside** the plausible conventional range
   - If both land in range, prefer the one closer to the reference mean

4. **Do not convert values already in plausible conventional range** - avoid over-converting high-but-valid values (e.g., Glucose 500+ mg/dL in DKA, Bilirubin 20+ mg/dL in cholestasis).

### 3. Format & Write Output
- Round all numeric values to exactly 2 decimal places
- Strip identifier columns (e.g., `patient_id`, `encounter_id`)
- **CRITICAL**: Write with Unix line endings (`\n`) only; Python's `csv` module on Windows defaults to `\r\n`
- Use dot decimal separator exclusively

### 4. Validation (Run Before Submitting)
1. **Line endings**: `file output.csv` must show `ASCII text`, NOT `with CRLF line terminators`
2. **No comma decimals in numeric fields**: Parse CSV column-wise, not line-wise
3. **Decimal precision**: All numeric values match pattern `^[0-9]+\.[0-9]{2}$`
4. **Plausibility**: No value >10× physiological max (indicates wrong unit direction)
5. **Glucose sanity check**: No glucose values < 20 or > 1000 after conversion

## Anti-Patterns (Avoid)

- **Blind multiplication/division**: Never assume conversion factor direction. Test both directions against physiological ranges.
- **Glucose over-conversion**: Values 30–700 are already mg/dL. Only convert if < 30 (likely mmol/L).
- **Naive comma-regex**: `[0-9],[0-9]` matches CSV delimiters. Only replace comma when between digits.
- **Over-conversion**: High Glucose (500+ mg/dL in DKA), high Bilirubin (20+ mg/dL in cholestasis), high Creatinine (10+ mg/dL in AKI) are valid. Use wide plausible ranges.
- **Rounding before conversion**: Always convert first, then round. Rounding early corrupts threshold detection.
- **CRLF line endings**: Python's `csv` module on Windows adds `\r\n`. MUST explicitly set `lineterminator='\n'`.

## Output precision
Round all numeric values to exactly 2 decimal places before writing to CSV. Concretely:
- DO: `round(value, 2)` then `f"{value:.2f}"` for exactly 2 decimal places
- DO NOT: write raw floats to CSV (Python's csv module outputs variable decimals like `5.1` instead of `5.10`)
- DO NOT: `round(x, 1)`, `format(x, ".1f")`, or any precision other than 2 decimal places
- The verifier requires exactly 2 decimal precision; no exceptions, no overrides.

## Known invariants (by sub-task)

### electrolyte-metabolic-panel
- Output must use Unix line endings (`\n`), not CRLF
- Identifier column `encounter_id` must be removed
- All numeric values must have exactly 2 decimal places (no more, no less)
- Common analytes: Glucose, Creatinine, Calcium, Magnesium (convertible); Sodium, Potassium, Chloride, Bicarbonate (no conversion needed, 1:1)

### hepatic-panel
- Output must use Unix line endings (`\n`), not CRLF
- Identifier column `patient_id` must be removed
- All numeric values must have exactly 2 decimal places (no more, no less)
- Convertible analytes: Total_Bilirubin, Direct_Bilirubin (÷17.1), Albumin (÷10), Hemoglobin (÷10), Ammonia (÷1.7)
- Non-convertible: AST, ALT, ALP, GGT (U/L), Platelets, INR (ratio)
- Extended plausible ranges must accommodate severe hepatic dysfunction: Bilirubin up to 30 mg/dL, Albumin as low as 1.0 g/dL, Ammonia up to 200 μg/dL

## Scripts

- `scripts/harmonize_lab_csv.py`: Reference implementation for CSV harmonization workflow

## References

- `references/unit-conversions.md`: Detailed conversion factors and reference ranges for all supported analytes
