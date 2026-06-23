---
name: clinical-lab-harmonization
description: Harmonizes clinical lab CSV data by parsing mixed numeric formats (scientific notation, comma decimals), joining multi-file inputs, deduplicating by patient/case ID, detecting and converting between SI and conventional units using physiological ranges, handling missing values, and standardizing to exact 2-decimal precision. Use for electrolyte, metabolic, hepatic, thyroid, cardiology, oncology follow-up, or ICU panels — any clinical lab CSV requiring unit normalization, multi-file join, or draw selection.
---

# Clinical Lab Data Harmonization

## Workflow

1. **Join (if multiple files)**: If task provides multiple CSVs, inner join on shared identifier (e.g., `record_id`). Use pandas `merge(inner)` or dict-based join. Drop rows not present in ALL files.

2. **Parse & Clean**: Read CSV using Python `csv` module (handles quoted fields). Replace comma decimal separators using `re.sub(r'(\d),(\d)', r'\1.\2', s)` — per-field, NOT whole-line. Parse scientific notation (`6.4372e+02` → `643.72`). Cast numeric columns to floats.
   - **Quoted comma-decimals**: If values like `"7,2882"` appear, use `csv.reader` to parse respecting quotes, then apply decimal replacement *per field*. Do NOT split on commas before handling quotes.
   - **Environment**: Always use `python3` explicitly. `python` may not exist.

3. **Deduplicate & Select Draws** (if applicable): Group rows by patient/case identifier. Sort by `draw_order`, `visit`, or timestamp descending. Keep the **highest** draw/visit that has **no missing values** in any measurement column. If the highest draw is incomplete, fall back to the next highest complete draw.

4. **Drop Incomplete Rows**: Remove any remaining rows with missing, empty, or `nan`/`NaN`/`None`/`NULL` values in measurement columns.

5. **Detect & Convert Alternate Units**:
   For each analyte value, use **bidirectional testing** against wide physiological ranges (including pathological extremes):

   | Analyte | Conv Range | Factor |
   |---------|-----------|--------|
   | Glucose | 40–600 mg/dL | × 18.0 |
   | Creatinine | 0.3–15.0 mg/dL | ÷ 88.4 |
   | Calcium | 6.0–15.0 mg/dL | × 4.0 |
   | Magnesium | 0.5–6.0 mg/dL | × 2.43 |
   | BUN | 5–150 mg/dL | × 2.8 |
   | Phosphorus | 1.5–12 mg/dL | × 3.1 |
   | Uric_Acid | 2–12 mg/dL | ÷ 59.48 |
   | LDH | 100–2000 U/L | × 59.4 if µkat/L |
   | WBC_Count | 0.5–60 K/μL | — |
   | Bilirubin (Total/Direct) | 0.1–30 mg/dL | ÷ 17.1 |
   | Albumin | 1.5–7.0 g/dL | ÷ 10 |
   | Total_Protein | 3.0–12.0 g/dL | ÷ 10 |
   | Hemoglobin | 5.0–25 g/dL | ÷ 10 |
   | Ammonia | 10–200 μg/dL | ÷ 1.7 |
   | Free_T4 | 0.3–6.0 ng/dL | ÷ 12.87 |
   | Free_T3 | 20–600 pg/dL | × 15.38 |
   | Total_T4 | 2.0–22.0 μg/dL | ÷ 12.87 |
   | Total_T3 | 40–400 ng/dL | ÷ 0.0154 |
   | PTH | 2–500 pg/mL | × 0.106 |
   | Vitamin_D_25OH | 5–200 ng/mL | ÷ 2.5 |
   | Troponin_I/T | 0.01–50 ng/mL | ÷ 1000 |
   | BNP | 10–5000 pg/mL | ÷ 0.289 |
   | NT_proBNP | 50–35000 pg/mL | ÷ 0.118 |
   | Na/K/Cl/HCO₃ | No conversion | — |
   | AST/ALT/ALP/GGT/INR/Platelets/TSH/Anti_TPO/Thyroglobulin/Ionized_Ca/Calcitonin | No conversion | — |
   | Lactate | No conversion (mmol/L) | — |
   | Beta_Hydroxybutyrate | No conversion | — |
   | Anion_Gap | No conversion (mEq/L) | — |
   | Osmolality | No conversion (mOsm/kg) | — |
   | pH_Arterial | No conversion | — |
   | pCO2_Arterial | No conversion (mmHg) | — |

   **Bidirectional rule**: If value is in conventional range → keep. Otherwise test `value * factor` and `value / factor`; keep whichever lands in range. If both, pick closer to range midpoint. If neither, keep original.

6. **Format & Output**:
   - Drop identifier columns: remove `patient_id`, `encounter_id`, `case_id`, `draw_order`, `visit`, `record_id`, or `sample_id` always
   - Round all numeric values to exactly 2 decimal places: `round(value, 2)` then `f"{value:.2f}"` for string formatting
   - Write clean CSV with Unix line endings (`\n`); set `lineterminator='\n'` in Python csv writer

7. **Validate Output**:
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
- Drop `encounter_id` column
- Sodium, Potassium, Chloride, Bicarbonate: no conversion needed

### hepatic-panel
- Drop `patient_id` column
- Convertible: Bilirubin (÷17.1), Albumin (÷10), Hemoglobin (÷10), Ammonia (÷1.7)
- Non-convertible: AST, ALT, ALP, GGT, INR, Platelets
- Hepatic SI values are numerically LARGER than conventional — test division first

### thyroid-monitoring-panel
- Drop `encounter_id` column
- Convertible: Free_T4 (÷12.87), Free_T3 (×15.38), Total_T4 (÷12.87), Total_T3 (÷0.0154), Calcium (÷0.25), Phosphorus (×/÷0.323), Magnesium (×0.411), PTH (×0.106), Vitamin_D (÷2.5), Creatinine (÷88.4)
- Non-convertible: TSH, Anti_TPO, Thyroglobulin, Thyroglobulin_Antibody, Ionized_Calcium, Calcitonin
- **Critical parsing**: Quoted comma-decimals (e.g., `"7,2882"`) — use `csv.reader` then decimal replacement per field

### cardiology-panel
- Drop `encounter_id` column
- Convertible: Troponin_I/T (÷1000), BNP (÷0.289), NT_proBNP (÷0.118), Creatinine (÷88.4), Magnesium (×2.43)
- Non-convertible: Sodium, Potassium
- **BNP/NT-proBNP**: SI (pmol/L) → conventional (pg/mL) by **dividing** by 0.289/0.118, NOT multiplying
- **Troponin**: Values >1000 are pg/mL; divide by 1000 for ng/mL

### oncology-followup-panel
- Drop `case_id` and `draw_order` columns
- **Deduplication required**: Group by `case_id`, sort by `draw_order` descending, keep highest complete draw
- Convertible: Uric_Acid (÷59.48), Creatinine (÷88.4), Calcium (×4.0), Albumin (÷10), Glucose (×18.0)
- Non-convertible: LDH (U/L), Phosphorus (mg/dL), Magnesium (mg/dL), Potassium, WBC_Count
- **Glucose range**: 40–600 mg/dL; values <40 likely SI mmol/L
- **LDH**: Up to 2000 U/L in oncology; do not convert unless >2000

### icu-metabolic-panel
- Inner join multiple CSVs on `record_id`; drop rows missing from any file
- Drop `record_id` column
- Convertible: Glucose (×18.0), BUN (×2.8), Creatinine (÷88.4), Calcium (×4.0), Magnesium (×2.43), Phosphorus (×3.1)
- Non-convertible: Lactate, Beta_Hydroxybutyrate, Anion_Gap, Osmolality, pH_Arterial, pCO2_Arterial, Na/K/Cl/HCO₃
- **BUN direction**: SI (mmol/L) → conventional (mg/dL) requires **multiplication by 2.8**, NOT division
- **Glucose**: ICU patients often have SI values <40 mmol/L; always test ×18.0
- **ICU ranges are wider**: Pathological values (Glucose 400+, Creatinine 12+) are common; do not convert if in conventional range

## Anti-Patterns

- **Blind multiplication/division**: Always test both directions against wide ranges
- **Narrow reference ranges**: Use wide "plausible" ranges (e.g., Creatinine 0.3–15.0), not "normal" (0.6–1.2)
- **Over-conversion**: Do not convert values already in plausible conventional range
- **Naive comma regex**: `[0-9],[0-9]` on whole lines matches CSV delimiters. Use `(\d),(\d)` per-field
- **Splitting before quoting**: Use `csv.reader` first for quoted comma-decimals like `"7,2882"`
- **CRLF line endings**: Set `lineterminator='\n'` in Python csv writer
- **Rounding before conversion**: Parse and convert first, then round
- **Preserving identifier columns**: Always drop `patient_id`, `encounter_id`, `case_id`, `draw_order`, `record_id`
- **BUN ÷2.8 instead of ×2.8**: BUN SI (mmol/L) is numerically smaller than conventional (mg/dL) — multiply
- **Assuming blood gases need conversion**: pH, pCO2, Anion_Gap, Osmolality — no conversion ever
- **Creating custom scripts instead of following this workflow**: Use this skill's workflow directly
- **Python environment**: Use `python3` explicitly
- **Trailing zeros lost**: Always format output with `f"{val:.2f}"`

## Troubleshooting

- Values seem 100× off: verify conversion direction using bidirectional testing
- Verifier fails on precision: ensure `round(value, 2)` + `f"{value:.2f}"` on every numeric cell
- Line ending failure: `sed -i 's/\r$//' output.csv`
- Pathological values incorrectly converted: widen plausible physiological range
- Glucose <40 mg/dL: likely SI mmol/L — multiply by 18.0
- BUN values too low: verify ×2.8 was applied, not ÷2.8
- Troponin values >1000: pg/mL units — divide by 1000
- BNP/NT-proBNP: divide by 0.289/0.118, do not multiply
- Wrong row count after join: ensure inner join; drop rows missing from any file
