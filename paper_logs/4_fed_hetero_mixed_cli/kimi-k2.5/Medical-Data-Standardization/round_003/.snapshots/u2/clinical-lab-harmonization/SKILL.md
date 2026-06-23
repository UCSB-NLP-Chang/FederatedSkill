---
name: clinical-lab-harmonization
description: Harmonizes clinical lab CSV data by parsing mixed number formats (scientific notation, comma decimals), detecting and converting between SI and US conventional units using physiological range testing, handling missing values, and standardizing to exact 2-decimal precision. Use for electrolyte panels, metabolic profiles, hepatic panels, thyroid monitoring, or any clinical lab CSV requiring unit normalization.
---

# Clinical Lab Data Harmonization

## When to use
- Input data mixes scientific notation (`1.5e+02`) with European decimal commas (`142,0205`)
- Must detect and convert between SI units (mmol/L, μmol/L, g/L, pmol/L) and conventional units (mg/dL, g/dL, ng/dL)
- Required to drop incomplete records, remove identifier columns, and enforce exact decimal precision
- Target format requires Unix line endings and specific column ordering
- **Thyroid panels**: Free_T4, Free_T3, Total_T4, Total_T3 frequently appear in pmol/L requiring conversion to ng/dL (Free_T4), pg/dL (Free_T3), μg/dL (Total_T4), or ng/dL (Total_T3)
- **Hepatic panels**: Bilirubin, Albumin, Hemoglobin frequently appear in SI units requiring conversion

## Workflow

### 1. Parse Input Formats
- **Scientific notation**: Parse strings matching `[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)`
- **European decimals**: Replace comma with dot *only when comma appears between digits*: `re.sub(r'(\d),(\d)', r'\1.\2', s)`
  - Do NOT use naive regex `[0-9],[0-9]` on whole lines - this matches CSV delimiters
- **CSV with quoted comma-decimals**: If values like `"7,2882"` appear, use a CSV parser that respects quoted fields (Python `csv` module), then apply decimal replacement *per field*. Do NOT split on commas before handling quotes.
- **Missing values**: Treat empty strings, `nan`, `NaN`, `NULL`, `None` as missing; drop entire row if any analyte is missing

### 2. Detect Unit System & Convert
For each value, use bidirectional testing against physiological ranges:

| Analyte | Conventional Range | SI Range | Factor (SI→Conv) |
|---------|-------------------|----------|------------------|
| Glucose | 70–140 mg/dL (ext: 30–700) | 3.9–7.8 mmol/L (ext: 1.7–39) | ×18.0 |
| Creatinine | 0.7–1.3 mg/dL (ext: 0.3–15) | 62–115 μmol/L (ext: 27–1326) | ÷88.4 |
| Calcium | 8.5–10.5 mg/dL (ext: 6–12) | 2.1–2.6 mmol/L (ext: 1.5–3) | ×4.0 |
| Magnesium | 1.7–2.2 mg/dL (ext: 0.5–5) | 0.7–0.9 mmol/L (ext: 0.2–2) | ×2.43 |
| **Total_Bilirubin** | 0.1–1.2 mg/dL (ext: 0.1–30) | 1.7–20.5 μmol/L (ext: 1.7–513) | **÷17.1** |
| **Direct_Bilirubin** | 0–0.3 mg/dL (ext: 0–10) | 0–5.1 μmol/L (ext: 0–171) | **÷17.1** |
| **Albumin** | 3.5–5.5 g/dL (ext: 1.5–6) | 35–55 g/L (ext: 15–60) | **÷10** |
| **Hemoglobin** | 12–18 g/dL (ext: 5–25) | 120–180 g/L (ext: 50–250) | **÷10** |
| **Free_T4** | 0.8–2.8 ng/dL (ext: 0.2–10) | 10–36 pmol/L (ext: 5–150) | **÷12.87** |
| **Free_T3** | 20–600 pg/dL (ext: 5–800) | 3–40 pmol/L (ext: 1.5–50) | **×15.38** |
| **Phosphorus** | 2.5–4.5 mg/dL (ext: 1–8) | 0.8–1.5 mmol/L (ext: 0.3–2.5) | **×3.10** |
| **PTH** | 10–65 pg/mL (ext: 2–500) | 1–7 pmol/L (ext: 0.2–50) | **×9.43** |
| **Vitamin_D_25OH** | 30–100 ng/mL (ext: 5–200) | 75–250 nmol/L (ext: 12–500) | **÷2.5** |
| **Total_T4** | 5–12 μg/dL (ext: 2–25) | 65–155 nmol/L (ext: 25–320) | **÷12.87** |
| **Total_T3** | 70–200 ng/dL (ext: 30–600) | 1.0–3.0 nmol/L (ext: 0.5–9) | **÷0.0154** |

**CRITICAL - Glucose special case**: SI values (mmol/L) are **numerically smaller** than conventional (mg/dL). A value of 5.5 is likely mmol/L (→ 99 mg/dL), not an extremely low mg/dL. If value < 30, test `value × 18` first.

**CRITICAL - Thyroid hormones**:
- Free_T4 and Total_T4 share the same factor (12.87) but different units (ng/dL vs μg/dL)
- Free_T3 converts to **pg/dL** (not ng/dL) — factor is ×15.38 from pmol/L; verify result falls in 20–600 pg/dL range
- Total_T3 conversion is aggressive (factor 0.0154); verify by checking if result falls in 70–200 ng/dL range
- TSH (mIU/L), Anti_TPO, Thyroglobulin, and Thyroglobulin_Antibody use identical units in SI and conventional (no conversion)
- Ionized_Calcium and Calcitonin require no conversion

**Conversion decision rule (bidirectional testing)**:
1. Test both `value * factor` and `value / factor`
2. Keep the operation that places the result inside the extended plausible range
3. If both fall in range (overlap zone), prefer conventional unless column statistics suggest otherwise
4. Do NOT convert pathological-but-plausible values (e.g., Glucose 500+ mg/dL in DKA, Bilirubin 25+ mg/dL in cholestasis, TSH >50 in hypothyroidism)

**Hepatic panel notes**:
- **No conversion needed**: AST, ALT, ALP, GGT reported in U/L (identical in SI and conventional)
- **Non-convertible**: INR (ratio), Platelets (×10⁹/L), AFP, Ferritin, Bile_Acids
- Extended ranges accommodate cholestatic disease (bilirubin up to 30 mg/dL), synthetic failure (albumin down to 1.5 g/dL)

**Thyroid panel notes**:
- **No conversion needed**: TSH (mIU/L), Anti_TPO (IU/mL), Thyroglobulin (ng/mL), Thyroglobulin_Antibody (IU/mL)
- **Convertible**: Free_T4, Free_T3, Total_T4, Total_T3
- Extended TSH range accommodates severe hypothyroidism (up to 100 mIU/L)

### 3. Format & Write Output
- Round all numeric values to exactly 2 decimal places: `round(value, 2)`
- Format output as string with exactly 2 decimals: `f"{value:.2f}"`
- Explicitly write Unix line endings (`\n`); strip `\r` if present: `sed -i 's/\r$//' output.csv`
- Remove identifier columns (`encounter_id`, `patient_id`) while preserving measurement column order
- Use dot decimal separator exclusively

### 4. Validation (Critical)
Run these checks before submitting:
1. **Line endings**: `file output.csv` must show `ASCII text`, not `with CRLF line terminators`
2. **No comma decimals**: Parse CSV properly - `cut -d',' -f2 output.csv | grep ','` should return nothing (check numeric columns only)
3. **Decimal precision**: All numeric values must match pattern `^[0-9]+\.[0-9]{2}$` (exactly 2 decimal places)
4. **Plausibility**: No value should be >10× physiological max after conversion (indicates wrong unit direction)
5. **Row count**: Output rows = input rows - dropped rows (no extra/missing)

## Anti-patterns (Avoid)

- **Do not** use naive regex `[0-9],[0-9]` to detect comma decimals across entire lines - this matches CSV delimiters
- **Do not** split CSV on commas before handling quoted fields - European decimals inside quotes (`"7,2882"`) will corrupt column alignment
- **Do not** assume conversion factor direction - test both multiply and divide, keep result in plausible range
- **Do not** round before unit conversion - parse first, convert, then round (affects threshold detection)
- **Do not** convert pathological-but-possible values (Glucose 500+ in DKA, Creatinine 10+ in AKI, Bilirubin 20+ in cholestasis, TSH 50+ in hypothyroidism)
- **Do not** assume all values in a column share the same unit system - evaluate per cell due to mixed source data
- **Do not** use `python` command; use `python3` explicitly
- **Do not** validate decimal precision with `awk` without stripping `\r` first - carriage returns attach to final field
- **Do not** convert AST/ALT/ALP/GGT between SI and conventional - reported in U/L (no conversion needed)
- **Do not** convert TSH or thyroid antibodies - units are consistent (mIU/L, IU/mL, ng/mL)
- **Do not** over-convert glucose - values 30–700 mg/dL are already conventional; only convert if < 30 (likely mmol/L)

## Output precision

The verifier requires exactly 2 decimal places for all numeric output values. Apply this at final output:
- `round(value, 2)` to get 2-decimal precision
- `f"{value:.2f}"` to format as string with exactly 2 decimal places
- Do NOT use `round(x, 1)` or `f"{x:.1f}"` - wrong precision
- Do NOT pass raw floats without formatting - Python may write fewer than 2 decimals

## Known invariants (by sub-task)

### electrolyte-metabolic-panel
- Output must use Unix line endings (`\n`), not CRLF
- Identifier column `encounter_id` must be removed
- All numeric values must have exactly 2 decimal places (no more, no less)
- Convertible: Glucose, Creatinine, Calcium, Magnesium
- No conversion needed: Sodium, Potassium, Chloride, Bicarbonate (mmol/L = mEq/L)

### hepatic-panel
- Output must use Unix line endings (`\n`), not CRLF
- Identifier column `patient_id` must be removed
- All numeric values must have exactly 2 decimal places (no more, no less)
- Convertible: Total_Bilirubin, Direct_Bilirubin (÷17.1), Albumin (÷10), Hemoglobin (÷10)
- No conversion needed: AST, ALT, ALP, GGT (U/L), INR, Platelets, AFP, Ferritin
- Extended plausible ranges accommodate severe hepatic dysfunction: Bilirubin up to 30 mg/dL, Albumin as low as 1.5 g/dL

### thyroid-monitoring-panel
- Output must use Unix line endings (`\n`), not CRLF
- Identifier column `encounter_id` must be removed
- All numeric values must have exactly 2 decimal places (no more, no less)
- Convertible: Free_T4 (÷12.87), Free_T3 (×15.38 pg/dL), Total_T4 (÷12.87), Total_T3 (÷0.0154)
- No conversion needed: TSH (mIU/L), Anti_TPO, Thyroglobulin, Thyroglobulin_Antibody
- Related chemistry: Calcium, Ionized_Calcium, Phosphorus, Magnesium, PTH, Vitamin_D_25OH, Calcitonin, Creatinine (convert per standard factors)
- **Critical parsing note**: Input frequently contains quoted comma-decimals (e.g., `"7,2882"`, `"1874,4810"`). Use proper CSV parsing that respects quotes, then apply decimal replacement per field.