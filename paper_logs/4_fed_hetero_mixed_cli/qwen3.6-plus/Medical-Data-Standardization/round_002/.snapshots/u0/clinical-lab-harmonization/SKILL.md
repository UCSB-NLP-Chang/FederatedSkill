---
name: clinical-lab-harmonization
description: Harmonizes clinical lab CSV data by parsing mixed numeric formats (scientific notation, comma decimals), detecting and converting between SI and conventional units using physiological ranges, handling missing values, and standardizing to exact 2-decimal precision. Use for electrolyte panels, metabolic profiles, hepatic panels, or any clinical lab CSV requiring unit normalization.
---

# Clinical Lab Data Harmonization

## Workflow

1. **Parse & Clean**: Read CSV. Replace comma decimal separators using `re.sub(r'(\d),(\d)', r'\1.\2', s)` — column-aware, NOT whole-line. Parse scientific notation (`6.4372e+02` → `643.72`). Cast numeric columns to floats.

2. **Drop Incomplete Rows**: Remove rows with missing, empty, or `nan`/`NaN`/`None`/`NULL` values in any measurement column.

3. **Detect & Convert Alternate Units**:
   For each analyte value, use bidirectional testing against physiological ranges:

   | Analyte | Conventional Range (extended) | SI Range | Factor (SI→Conv) |
   |---------|------------------------------|----------|------------------|
   | Glucose | 30–700 mg/dL | 2–40 mmol/L | × 18.0 |
   | Creatinine | 0.3–15 mg/dL | 25–1300 μmol/L | ÷ 88.4 |
   | Calcium | 6–14 mg/dL | 1.5–3.5 mmol/L | × 4.0 |
   | Magnesium | 0.5–5 mg/dL | 0.2–2 mmol/L | × 2.43 |
   | Total/Direct Bilirubin | 0.1–30 mg/dL | 2–500 μmol/L | ÷ 17.1 |
   | Albumin | 1.0–6.0 g/dL | 10–60 g/L | ÷ 10 |
   | Total_Protein | 3.0–12.0 g/dL | 30–120 g/L | ÷ 10 |
   | Hemoglobin | 5.0–25 g/dL | 50–250 g/L | ÷ 10 |
   | Ammonia | 10–200 μg/dL | 5–120 μmol/L | ÷ 1.7 |
   | Na/K/Cl/HCO₃ | mmol/L = mEq/L | No conversion | — |
   | AST/ALT/ALP/GGT/INR/Platelets | U/L or ratio | No conversion | — |

   **Conversion decision rule:**
   - Test both `value * factor` and `value / factor`; keep result inside plausible conventional range
   - **Glucose is special**: SI (mmol/L) is numerically SMALLER than conventional (mg/dL). If value < 30, try `value × 18` first
   - If both directions land in range, prefer result closer to reference mean
   - Do NOT convert values already in plausible conventional range

4. **Format & Output**:
   - Drop identifier columns: remove `patient_id` and `encounter_id` always
   - Round all numeric values to exactly 2 decimal places: `round(value, 2)` then `f"{value:.2f}"`
   - Write clean CSV with Unix line endings (`\n`); set `lineterminator='\n'` in Python csv writer

5. **Validate Output**:
   - `file output.csv` must show `ASCII text` (NOT `with CRLF line terminators`)
   - All numeric values match `^[0-9]+\.[0-9]{2}$` (exactly 2 decimal places)
   - `grep -E '[0-9]+e[+-]' output.csv` returns nothing
   - Row count = original minus dropped incomplete rows

## Output precision

The verifier requires exactly 2 decimal places. Round at final output step only:
- DO: `round(value, 2)` then `f"{value:.2f}"` for exactly 2 decimal places
- DO NOT: leave raw floats, use `round(x, 1)`, or skip formatting
- Convert first, then round — rounding before conversion corrupts threshold detection

## Known invariants (by sub-task)

### electrolyte-metabolic-panel
- Exactly 2 decimal places per numeric field
- Unix line endings only; strip `\r` if present
- Row count = original minus dropped incomplete rows
- Drop `encounter_id` column
- Sodium, Potassium, Chloride, Bicarbonate: no conversion needed

### hepatic-panel
- Exactly 2 decimal places per numeric field
- Unix line endings only; strip `\r` if present
- Drop `patient_id` column
- Convertible: Bilirubin (÷17.1), Albumin (÷10), Hemoglobin (÷10), Ammonia (÷1.7)
- Non-convertible: AST, ALT, ALP, GGT (U/L), INR (ratio), Platelets
- Hepatic SI values are numerically LARGER than conventional (g/L vs g/dL, μmol/L vs mg/dL) — test division first for these

## Anti-Patterns

- **Blind multiplication**: Never assume factor direction. Always test both directions against ranges.
- **Over-conversion**: Do not convert pathological-but-plausible values (Glucose 500+ in DKA, Bilirubin 20+ in cholestasis).
- **Naive comma regex**: `[0-9],[0-9]` on whole lines matches CSV delimiters. Use `(\d),(\d)` per-cell.
- **CRLF line endings**: Python csv on Windows defaults to `\r\n`. Set `lineterminator='\n'`.
- **Rounding before conversion**: Parse and convert first, then round.
- **Preserving identifier columns**: Always drop `patient_id` and `encounter_id`.
- **Python environment**: Use `python3` explicitly.

## Troubleshooting

- Values seem 100× off: verify conversion direction (multiply vs divide)
- Verifier fails on precision: ensure `round(value, 2)` + `f"{value:.2f}"` is applied to every numeric cell
- Line ending failure: `sed -i 's/\r$//' output.csv`
