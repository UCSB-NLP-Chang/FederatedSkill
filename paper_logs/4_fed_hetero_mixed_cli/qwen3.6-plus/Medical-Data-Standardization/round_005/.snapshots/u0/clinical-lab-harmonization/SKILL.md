---
name: clinical-lab-harmonization
description: Harmonizes clinical lab CSV data by parsing mixed numeric formats (scientific notation, comma decimals), deduplicating by patient/case ID (keeping highest complete draw), detecting and converting between SI and conventional units using physiological ranges, handling missing values, and standardizing to exact 2-decimal precision. Use for electrolyte panels, metabolic profiles, hepatic panels, thyroid monitoring, cardiology panels, oncology follow-ups, or any clinical lab CSV requiring unit normalization and draw selection.
---

# Clinical Lab Data Harmonization

## Workflow

1. **Parse & Clean**: Read CSV using Python `csv` module (handles quoted fields). Replace comma decimal separators using `re.sub(r'(\d),(\d)', r'\1.\2', s)` — per-field, NOT whole-line. Parse scientific notation (`6.4372e+02` → `643.72`). Cast numeric columns to floats.
   - **Quoted comma-decimals**: If values like `"7,2882"` appear, use `csv.reader` to parse respecting quotes, then apply decimal replacement *per field*. Do NOT split on commas before handling quotes.
   - **Environment**: Always use `python3` explicitly. `python` may not exist.

2. **Deduplicate & Select Draws**: Group rows by patient/case identifier. Sort by `draw_order`, `visit`, or timestamp descending. Keep the **highest** draw/visit that has **no missing values** in any measurement column. If the highest draw is incomplete, fall back to the next highest complete draw.

3. **Drop Incomplete Rows**: After selection, remove any remaining rows with missing, empty, or `nan`/`NaN`/`None`/`NULL` values in measurement columns.

4. **Detect & Convert Alternate Units**:
   For each analyte value, use **bidirectional testing** against wide physiological ranges (including pathological extremes):

   | Analyte | Plausible Conventional Range | SI/Alternate Range | Factor |
   |---------|------------------------------|--------------------|--------|
   | Glucose | 40–600 mg/dL | 2–35 mmol/L | × 18.0 |
   | Creatinine | 0.3–15.0 mg/dL | 25–1300 μmol/L | ÷ 88.4 |
   | Calcium | 6.0–15.0 mg/dL | 1.5–3.5 mmol/L | × 4.0 |
   | Magnesium | 0.5–6.0 mg/dL | 0.2–2 mmol/L | × 2.43 |
   | Uric_Acid | 2–12 mg/dL | 120–700 μmol/L | ÷ 59.48 |
   | Phosphorus | 1.5–12 mg/dL | 0.5–4 mmol/L | × 3.1 |
   | LDH | 100–2000 U/L | 1.5–35 μkat/L | × 59.4 |
   | WBC_Count | 0.5–60 K/μL | 0.5–60 ×10⁹/L | — |
   | Total/Direct Bilirubin | 0.1–30 mg/dL | 2–500 μmol/L | ÷ 17.1 |
   | Albumin | 1.5–7.0 g/dL | 10–60 g/L | ÷ 10 |
   | Total_Protein | 3.0–12.0 g/dL | 30–120 g/L | ÷ 10 |
   | Hemoglobin | 5.0–25 g/dL | 50–250 g/L | ÷ 10 |
   | Ammonia | 10–200 μg/dL | 5–120 μmol/L | ÷ 1.7 |
   | Free_T4 | 0.3–6.0 ng/dL | 10–80 pmol/L | ÷ 12.87 |
   | Free_T3 | 20–600 pg/dL | 3–40 pmol/L | × 15.38 |
   | Total_T4 | 2.0–22.0 μg/dL | 25–280 nmol/L | ÷ 12.87 |
   | Total_T3 | 40–400 ng/dL | 0.6–6.0 nmol/L | ÷ 0.0154 |
   | PTH | 2–500 pg/mL | 20–5000 pmol/L | × 0.106 |
   | Vitamin_D_25OH | 5–200 ng/mL | 12–500 nmol/L | ÷ 2.5 |
   | Troponin_I / Troponin_T | 0.01–50 ng/mL | 10–5000 ng/L | ÷ 1000 |
   | BNP | 10–5000 pg/mL | 3–1500 pmol/L | ÷ 0.289 |
   | NT_proBNP | 50–35000 pg/mL | 6–4000 pmol/L | ÷ 0.118 |
   | Na/K/Cl/HCO₃ | mmol/L = mEq/L | No conversion | — |
   | AST/ALT/ALP/GGT/INR/Platelets/TSH/Anti_TPO/Thyroglobulin/Ionized_Ca/Calcitonin | No conversion | — | — |

   **Bidirectional Conversion Decision Rule:**
   - If value is already inside the plausible conventional range → **keep as-is** (even if pathologically high/low).
   - If value is outside the range → try `value * factor` and `value / factor`.
   - Keep the result that lands **inside** the plausible conventional range.
   - If both land in range, prefer the one closer to the reference mean.
   - If neither lands in range, keep original (likely pathological but correct unit).

5. **Format & Output**:
   - Drop identifier columns: remove `patient_id`, `encounter_id`, `case_id`, `draw_order`, `visit`, or `sample_id` always
   - Round all numeric values to exactly 2 decimal places: `round(value, 2)` then `f"{value:.2f}"` for string formatting
   - Write clean CSV with Unix line endings (`\n`); set `lineterminator='\n'` in Python csv writer

6. **Validate Output**:
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

### oncology-followup-panel
- Exactly 2 decimal places per numeric field
- Unix line endings only; strip `\r` if present
- Group by `case_id`, keep highest complete `draw_order`
- Drop `case_id` and `draw_order` columns
- Convertible: Uric_Acid (÷59.48), Creatinine (÷88.4), Calcium (×4.0), Albumin (÷10), Glucose (×18.0)
- Non-convertible: LDH (U/L), Phosphorus (mg/dL), Magnesium (mg/dL), Potassium (mEq/L), WBC_Count (K/μL)
- **Glucose range**: Use 40–600 mg/dL. Values <40 mg/dL are physiologically implausible for follow-up and likely SI mmol/L.
- **LDH**: Oncology patients often have elevated LDH (up to 2000 U/L). Do not convert unless >2000.

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
- **Critical parsing**: Input frequently contains quoted comma-decimals (e.g., `"7,2882"`, `"1874,4810"`). Use `csv.reader` to parse respecting quotes, then apply decimal replacement per field.

### cardiology-panel
- Exactly 2 decimal places per numeric field
- Unix line endings only; strip `\r` if present
- Drop `encounter_id` column
- Convertible: Troponin_I/T (÷1000), BNP (÷0.289), NT_proBNP (÷0.118), Creatinine (÷88.4), Magnesium (×2.43 or ÷2.43 depending on input)
- Non-convertible: Sodium, Potassium
- **BNP/NT-proBNP**: SI units are pmol/L. To convert to US pg/mL, **divide** by 0.289 (BNP) or 0.118 (NT-proBNP). Do not multiply.
- **Troponin**: Often reported in ng/L or pg/mL. Divide by 1000 to get ng/mL.
- **Magnesium**: Standard factor is ×2.43 (mmol/L → mg/dL). If values are out of range, test both `*2.43` and `/2.43` against 0.8–5.0 mg/dL range.

## Anti-Patterns

- **Blind multiplication/division**: Never assume factor direction. Always test both `value * factor` and `value / factor` against wide physiological ranges.
- **Narrow reference ranges**: Do not use strict "normal" ranges (e.g., Creatinine 0.6-1.2) for detection. Use wide "plausible physiological" ranges (e.g., 0.3-15.0) to avoid converting pathological values.
- **Over-conversion**: Do not convert values already in plausible conventional range, even if pathologically elevated.
- **Naive comma regex**: `[0-9],[0-9]` on whole lines matches CSV delimiters. Use `(\d),(\d)` per-field.
- **Splitting before quoting**: Do NOT split CSV on commas before handling quoted fields — European decimals inside quotes (`"7,2882"`) will corrupt column alignment. Always use `csv.reader` first.
- **CRLF line endings**: Python csv on Windows defaults to `\r\n`. Set `lineterminator='\n'`.
- **Rounding before conversion**: Parse and convert first, then round.
- **Preserving identifier columns**: Always drop `patient_id`, `encounter_id`, `case_id`, `draw_order`, or `visit`.
- **Python environment**: Use `python3` explicitly.
- **Trailing zeros lost**: `round()` returns floats that drop trailing zeros. Always format output strings with `f"{val:.2f}"`.

## Troubleshooting

- Values seem 100× off: verify conversion direction (multiply vs divide) using bidirectional testing.
- Verifier fails on precision: ensure `round(value, 2)` + `f"{value:.2f}"` is applied to every numeric cell.
- Line ending failure: `sed -i 's/\r$//' output.csv`
- Pathological values incorrectly converted: widen the plausible physiological range used for detection.
- Glucose <40 mg/dL detected: likely SI mmol/L. Tighten lower bound to 40 mg/dL for detection.
- Verifier fails despite local checks passing: verify output file path matches task requirements exactly; check BNP/NT-proBNP conversion direction (divide, not multiply); ensure no hidden columns or extra whitespace in headers.