---
name: clinical-lab-harmonization
description: Harmonizes clinical lab CSV data by parsing mixed numeric formats (scientific notation, comma decimals, quoted fields), detecting and converting between SI and conventional units using physiological ranges, handling missing values, and standardizing to exact 2-decimal precision. Use for electrolyte panels, metabolic profiles, hepatic panels, thyroid monitoring, cardiology panels, oncology followup panels, or any clinical lab CSV requiring unit normalization. Also handles deduplication when multiple draws exist per case.
---

# Clinical Lab Data Harmonization

## Workflow

1. **Parse & Clean**: Read CSV. Replace comma decimal separators using `re.sub(r'(\d),(\d)', r'\1.\2', s)` — column-aware, NOT whole-line. Parse scientific notation (`6.4372e+02` → `643.72`). Cast numeric columns to floats.

   **CRITICAL - Quoted comma-decimals**: If values like `"7,2882"` appear, use a CSV parser that respects quoted fields (Python `csv` module), then apply decimal replacement *per field*. Do NOT split on commas before handling quotes — this corrupts column alignment.

2. **Drop Incomplete Rows**: Remove rows with missing, empty, or `nan`/`NaN`/`None`/`NULL` values in any measurement column.

3. **Deduplicate if Needed**: If multiple rows exist per case (e.g., multiple blood draws):
   - Identify the case identifier column (e.g., `case_id`, `patient_id`)
   - Identify the draw/timestamp column (e.g., `draw_order`, `draw_date`)
   - For each case, prefer the latest/most complete draw
   - Fallback to earlier draw if later draw has missing values
   - Output exactly one row per case

4. **Detect & Convert Alternate Units**:
   For each analyte value, use **bidirectional testing** against wide physiological ranges (including pathological extremes):

   | Analyte | Plausible Conventional Range | SI Range | Factor |
   |---------|------------------------------|----------|--------|
   | Glucose | 30–700 mg/dL | 2–40 mmol/L | × 18.0 |
   | Creatinine | 0.2–20.0 mg/dL | 25–1300 μmol/L | ÷ 88.4 |
   | Calcium | 5.0–15.0 mg/dL | 1.5–3.5 mmol/L | × 4.0 |
   | Magnesium | 0.8–5.0 mg/dL | 0.2–2 mmol/L | × 2.43 |
   | Total/Direct Bilirubin | 0.1–30 mg/dL | 2–500 μmol/L | ÷ 17.1 |
   | Albumin | 1.0–6.0 g/dL | 10–60 g/L | ÷ 10 |
   | Total_Protein | 3.0–12.0 g/dL | 30–120 g/L | ÷ 10 |
   | Hemoglobin | 5.0–25 g/dL | 50–250 g/L | ÷ 10 |
   | Ammonia | 10–200 μg/dL | 5–120 μmol/L | ÷ 1.7 |
   | LDH | 140–1000 U/L | 2–17 µkat/L | ÷ 0.0167 |
   | Uric_Acid | 2.0–12.0 mg/dL | 120–700 μmol/L | ÷ 59.48 |
   | Free_T4 | 0.3–6.0 ng/dL | 10–80 pmol/L | ÷ 12.87 |
   | Free_T3 | 20–600 pg/dL | 3–40 pmol/L | × 15.38 |
   | Total_T4 | 2.0–22.0 μg/dL | 25–280 nmol/L | ÷ 12.87 |
   | Total_T3 | 40–400 ng/dL | 0.6–6.0 nmol/L | ÷ 0.0154 |
   | Phosphorus | 1.0–8.0 mg/dL | 0.3–2.5 mmol/L | ×/÷ 0.323 |
   | PTH | 2–500 pg/mL | 20–5000 pmol/L | × 0.106 |
   | Vitamin_D_25OH | 5–200 ng/mL | 12–500 nmol/L | ÷ 2.5 |
   | Troponin_I / Troponin_T | 0.01–50 ng/mL | 10–50000 ng/L (pg/mL) | ÷ 1000 |
   | BNP | 10–5000 pg/mL | 3–1500 pmol/L | ÷ 0.289 |
   | NT_proBNP | 50–35000 pg/mL | 6–4000 pmol/L | ÷ 0.118 |
   | Na/K/Cl/HCO₃ | mmol/L = mEq/L | No conversion | — |
   | WBC_Count | 1.0–50.0 K/µL | 1.0–50.0 ×10⁹/L | No conversion |
   | AST/ALT/ALP/GGT/INR/Platelets/TSH/Anti_TPO/Thyroglobulin/Ionized_Ca/Calcitonin | No conversion | — | — |

   **Bidirectional Conversion Decision Rule:**
   - If value is already inside the plausible conventional range → **keep as-is** (even if pathologically high/low).
   - If value is outside the range → try `value * factor` and `value / factor`.
   - Keep the result that lands **inside** the plausible conventional range.
   - If both land in range, prefer the one closer to the reference mean.
   - If neither lands in range, keep original (likely pathological but correct unit).

5. **Format & Output**:
   - Drop identifier columns: remove `patient_id` and `encounter_id` always
   - Round all numeric values to exactly 2 decimal places: `round(value, 2)` then `f"{value:.2f}"`
   - Write clean CSV with Unix line endings (`\n`); set `lineterminator='\n'` in Python csv writer

6. **Validate Output**:
   - `file output.csv` must show `ASCII text` (NOT `with CRLF line terminators`)
   - All numeric values match `^[0-9]+\.[0-9]{2}$` (exactly 2 decimal places)
   - `grep -E '[0-9]+e[+-]' output.csv` returns nothing
   - Row count = original minus dropped incomplete rows (or one per case after deduplication)

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

### thyroid-monitoring-panel
- Exactly 2 decimal places per numeric field
- Unix line endings only; strip `\r` if present
- Drop `encounter_id` column
- Convertible: Free_T4 (÷12.87), Free_T3 (×15.38), Total_T4 (÷12.87), Total_T3 (÷0.0154), Calcium (÷0.25), Phosphorus (×/÷0.323), Magnesium (×0.411), PTH (×0.106), Vitamin_D (÷2.5), Creatinine (÷88.4)
- Non-convertible: TSH, Anti_TPO, Thyroglobulin, Thyroglobulin_Antibody, Ionized_Calcium, Calcitonin
- Use wide physiological ranges to avoid converting genuinely pathological values (e.g., Free_T4 up to 6.0 ng/dL, Creatinine up to 20.0 mg/dL)
- **Critical parsing note**: Input frequently contains quoted comma-decimals (e.g., `"7,2882"`, `"1874,4810"`). Use proper CSV parsing that respects quotes, then apply decimal replacement per field.

### cardiology-panel
- Exactly 2 decimal places per numeric field
- Unix line endings only; strip `\r` if present
- Drop `encounter_id` column
- Convertible: Troponin_I/T (÷1000), BNP (÷0.289), NT_proBNP (÷0.118), Creatinine (÷88.4), Magnesium (×2.43 or ÷2.43 depending on input)
- Non-convertible: Sodium, Potassium
- **BNP/NT-proBNP**: SI units are pmol/L. To convert to US pg/mL, **divide** by 0.289 (BNP) or 0.118 (NT-proBNP). Do not multiply.
- **Troponin**: Often reported in ng/L or pg/mL. Divide by 1000 to get ng/mL.
- **Magnesium**: Standard factor is ×2.43 (mmol/L → mg/dL). If values are out of range, test both `*2.43` and `/2.43` against 0.8–5.0 mg/dL range.
- **Critical**: Troponin values >1000 strongly suggest pg/mL units requiring ÷1000 conversion.

### oncology-followup-panel
- Exactly 2 decimal places per numeric field
- Unix line endings only; strip `\r` if present
- Drop `case_id` and `draw_order` columns
- **Deduplication required**: One row per case, selecting most complete/latest draw with fallback
- Convertible: Uric_Acid (÷59.48), Creatinine (÷88.4), Phosphorus (×3.097), Calcium (×4.008), Albumin (÷10), Glucose (×18.02), Magnesium (×2.431), LDH (÷0.0167 if SI µkat/L)
- Non-convertible: Potassium, WBC_Count
- LDH SI (µkat/L) is rare; most labs report U/L directly

## Anti-Patterns

- **Blind multiplication/division**: Never assume factor direction. Always test both `value * factor` and `value / factor` against wide physiological ranges.
- **Narrow reference ranges**: Do not use strict "normal" ranges (e.g., Creatinine 0.6-1.2) for detection. Use wide "plausible physiological" ranges (e.g., 0.2-20.0) to avoid converting pathological values.
- **Over-conversion**: Do not convert values already in plausible conventional range, even if pathologically elevated.
- **Naive comma regex**: `[0-9],[0-9]` on whole lines matches CSV delimiters. Use `(\d),(\d)` per-cell.
- **Ignoring quoted fields**: Splitting CSV on commas before handling quotes corrupts European decimals like `"7,2882"`. Use `csv` module first.
- **CRLF line endings**: Python csv on Windows defaults to `\r\n`. Set `lineterminator='\n'`.
- **Rounding before conversion**: Parse and convert first, then round.
- **Preserving identifier columns**: Always drop `patient_id` and `encounter_id`.
- **Python environment**: Use `python3` explicitly.
- **Missing trailing zeros**: `round(x, 2)` returns a float that may display as `9.0` instead of `9.00`. Always format with `f"{value:.2f}"` for exact 2 decimal places.

## Troubleshooting

- Values seem 100× off: verify conversion direction (multiply vs divide) using bidirectional testing.
- Verifier fails on precision: ensure `round(value, 2)` + `f"{value:.2f}"` is applied to every numeric cell.
- Line ending failure: `sed -i 's/\r$//' output.csv`
- Pathological values incorrectly converted: widen the plausible physiological range used for detection.
- Quoted European decimals misparsed: use `csv.reader` then `re.sub(r'(\d),(\d)', r'\1.\2', field)` per field.
- Troponin values >1000: strongly suggest pg/mL units — divide by 1000 to get ng/mL.
- BNP/NT-proBNP conversion: SI (pmol/L) divides by 0.289/0.118 to get conventional pg/mL. Do not multiply.
- Multiple rows per case: implement deduplication with draw order fallback before unit conversion.

## Scripts

- `scripts/harmonize_lab_csv.py`: Reference implementation for CSV harmonization workflow

## References

- `references/unit-conversions.md`: Detailed conversion factors and reference ranges for all supported analytes
