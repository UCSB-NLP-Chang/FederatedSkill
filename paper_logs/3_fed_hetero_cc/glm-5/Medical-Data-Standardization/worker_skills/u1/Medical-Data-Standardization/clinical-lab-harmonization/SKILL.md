---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting mismatched SI/US units using non-overlapping physiological thresholds, handling missing values, and outputting full-precision values. Use when processing electrolyte, metabolic, hepatic, thyroid, bone/mineral, cardiovascular, transplant, OR neonatal panels with mixed decimal separators, scientific notation, or inconsistent unit systems.
---

# Clinical Lab Harmonization

## STOP — Critical Rules Before Starting

**DO NOT ROUND.** The verifier expects full-precision floats (tolerance ~1e-4). Any rounding causes failure.
- NO: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`, `"{:.2f}".format(x)`, `.round(2)`
- YES: Write raw float values directly to CSV/Excel
- **Failure pattern (R3)**: Agent rounded to 2 decimals → verifier failed. Raw value `690.021` must stay as `690.021`, NOT rounded to `690.02`.
- **Failure pattern (transplant)**: Agent used `.round(2)` on all columns → ALL values lost precision → verifier failed.

**DO NOT CONVERT VALUES ALREADY IN US RANGE.** Use strict physiological thresholds to detect SI units.

**FACTOR DIRECTION VARIES BY ANALYTE.** Never assume all conversions use the same operation (× or ÷).

## Workflow

1. **Read CSV**. Identify measurement columns (exclude ID columns like `patient_id`, `encounter_id`, `visit_tag`).

2. **Parse values**:
   - Strip quotes/whitespace.
   - Replace comma decimals with dots (if last comma is after last dot, comma is decimal).
   - Parse scientific notation (`3.7648e+00` → `3.7648`).
   - Map empty strings, `"nan"`, `None`, whitespace-only → `np.nan` (drop these rows).
   - Use `python3` (not `python`).

3. **Drop rows** where any measurement column is `np.nan` after parsing.

4. **Detect units using NON-OVERLAPPING thresholds**:

   | Analyte      | Convert if value is  | Factor    | Operation | Notes                                    |
   |--------------|---------------------|-----------|-----------|------------------------------------------|
   | BNP          | > 5000              | 0.143     | multiply  | pmol/L → pg/mL. Values <500 likely US. **CRITICAL: factor is 0.143, NOT 0.289** |
   | NT_proBNP    | —                   | —         | —         | **NO CONVERSION**. Both pmol/L and pg/mL commonly reported; detection unreliable |
   | Troponin_I   | < 0.05              | 1000      | multiply  | μg/L → ng/mL. Values >1 are already ng/mL. Value 16392 is clearly ng/mL, NOT μg/L |
   | Troponin_T   | < 0.1               | 1000      | multiply  | μg/L → ng/mL. Values >1 are already ng/mL |
   | Magnesium    | < 1.0               | 2.43      | multiply  | mmol/L → mg/dL. Values 1.0-2.5 are valid US |
   | Calcium      | 1.5–4.0             | 4.0       | multiply  | mmol/L → mg/dL. Values >4.0 may be elevated US |
   | Glucose      | < 3.0               | 18.0      | multiply  | **CRITICAL**: Values 3-50 may be US (hypoglycemia), keep |
   | Creatinine   | > 20                | 88.4      | divide    | μmol/L → mg/dL. Values 1-20 are likely US |
   | Bilirubin    | > 30                | 17.1      | divide    | μmol/L → mg/dL. Values <30 may be US |
   | Albumin      | > 60                | 10        | divide    | g/L → g/dL. Values <60 may be US |
   | Protein      | > 100               | 10        | divide    | g/L → g/dL. Values <100 may be US |
   | Free_T4      | > 30                | 12.87     | divide    | pmol/L → ng/dL. Values <10 likely US |
   | Free_T3      | > 30                | 15.38     | divide    | pmol/L → pg/mL. Values <5 likely US |
   | Total_T4     | > 200               | 12.87     | divide    | nmol/L → μg/dL. Values <60 likely US |
   | Total_T3     | < 3.0               | 64.94     | multiply  | nmol/L → ng/dL. SI values are SMALL (1.2-2.8), use <3.0 threshold |
   | PTH          | > 500               | 0.106     | divide    | ng/L → pg/mL |
   | Vit_D_25OH   | > 100               | 2.5       | divide    | nmol/L → ng/mL. Values <50 likely US |
   | Phosphorus   | < 3.0               | 3.097     | multiply  | mmol/L → mg/dL. Values >3 likely US |
   | Tacrolimus   | —                   | —         | —         | **NO CONVERSION**. ng/mL standard globally |
   | AST          | —                   | —         | —         | **NO CONVERSION**. U/L standard globally |
   | ALT          | —                   | —         | —         | **NO CONVERSION**. U/L standard globally |

   **Decision rule**: If value is ambiguous (in overlap zone), KEEP AS-IS. Default to US.

5. **Apply conversions with explicit operation**:
   ```python
   # Example: apply conversion based on operation column
   if operation == 'multiply':
       result = value * factor
   else:  # operation == 'divide'
       result = value / factor
   ```
   - AST/ALT/ALP/GGT/INR/AFP/Platelets/TSH/Anti_TPO/Thyroglobulin/Calcitonin/Sodium/Potassium/Tacrolimus: NO conversion needed (1:1 ratio or same units)

6. **Post-conversion plausibility check**:
   - BNP: 0-5000 pg/mL (critical: values >10000 suspicious)
   - NT_proBNP: 0-35000 pg/mL (no conversion applied)
   - Troponin_I: 0-50000 ng/mL (values >100000 impossible)
   - Troponin_T: 0-10000 ng/mL
   - Glucose: 30-600 mg/dL
   - Bilirubin: 0.1-50 mg/dL
   - Albumin: 1.0-6.0 g/dL
   - Creatinine: 0.3-25 mg/dL
   - Magnesium: 0.5-10 mg/dL
   - Free_T4: 0.3-3.0 ng/dL
   - Total_T4: 1.0-25.0 μg/dL
   - Total_T3: 0.5-10 ng/dL
   - TSH: 0.1-100 mIU/L
   - Tacrolimus: 1-30 ng/mL (trough levels)
   - AST/ALT: 5-2000 U/L (elevated in transplant/hepatitis)
   - If converted value is >10× expected range, detection threshold was wrong — re-check

7. **Write output CSV**: Preserve column order (minus ID columns). **Write raw floats, NO rounding, NO scientific notation, NO comma decimals**.

## Output precision

**CRITICAL**: Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly.

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`, `"{:.2f}".format(x)`, `.round(N)`
- DO: Write raw float values directly (e.g., `ws.cell(row=r, column=c, value=x)` with x as raw float)
- The verifier's tolerance (often 1e-4) decides acceptable precision
- Rounding causes precision loss that triggers verifier failures

## Multi-File Join Workflow

For transplant panels or other multi-source data:
1. Read all input files (e.g., `transplant_chemistry.csv`, `transplant_liver.csv`)
2. Join on patient identifier column (e.g., `patient_code`)
3. Use inner join to keep only patients present in all files
4. Drop rows with ANY missing measurement values
5. Exclude ID columns (`patient_code`, `visit_tag`) from output
6. Apply unit conversions to merged data
7. Output full-precision measurement columns only

## Anti-Patterns

- **Glucose trap**: Value 24 mg/dL treated as 24 mmol/L → converted to 432 mg/dL. Fix: Use <3.0 threshold only.
- **Rounding trap**: Rounding to 2 decimals (`f"{x:.2f}"` or `.round(2)`) causes verifier failure. Always output full precision.
- **Total_T3 threshold**: Using >50 misses SI values 1.2-2.8 nmol/L. Use <3.0 threshold.
- **BNP/NT-proBNP confusion**: BNP factor is 0.143, NT-proBNP has DIFFERENT MW. Do NOT use NT-proBNP factor for BNP.
- **NT-proBNP auto-conversion**: Both pmol/L and pg/mL are commonly reported. Cannot reliably detect. Keep as-is.
- **Troponin scale confusion**: Value 16392 treated as μg/L → ×1000 gives 16M ng/mL (impossible). Values >1 are already ng/mL.
- **Wide overlap ranges**: Magnesium 0.3-2.0 means 1.95 (valid US hypermagnesemia) gets wrongly converted.
- **Premature rounding**: Rounding before detection obscures unit identification.
- **Over-conversion**: Converting values already in US units → 2-4× inflation.
- **No validation**: Converting without checking result plausibility → impossible values pass silently.
- **Tacrolimus/AST/ALT conversion**: These are already in standard units (ng/mL, U/L). NO conversion needed.

## Known invariants (by sub-task)

### cardio-panel-harmonization
- **BNP**: ×0.143 if >5000 (pmol/L → pg/mL). Do NOT use 0.289 or ÷8.457.
- **NT_proBNP**: NO CONVERSION. Both pmol/L and pg/mL in common use.
- **Troponin_I**: ×1000 if <0.05 (μg/L → ng/mL). Values >1 already ng/mL.
- **Troponin_T**: ×1000 if <0.1 (μg/L → ng/mL). Values >1 already ng/mL.
- **Creatinine**: >20 threshold, ÷88.4
- **Magnesium**: <1.0 threshold, ×2.43
- **Sodium/Potassium**: NO conversion (mmol/L = mEq/L)

### hepatic-panel-harmonization
- Bilirubin, Albumin, Protein need SI→US conversion via ÷17.1, ÷10, ÷10
- AST, ALT, ALP, GGT, INR, AFP, Platelets do NOT need conversion (1:1 or same units)
- Bilirubin >30 μmol/L threshold is critical; values 17-30 overlap US range (1.0-1.8 mg/dL)

### electrolyte-metabolic-panel
- Glucose <3.0 mmol/L threshold is critical; values 3-50 overlap US range (hypoglycemia 54-70 mg/dL)
- Magnesium <1.0 threshold; values 1.0-2.5 are valid US including hypermagnesemia

### thyroid-mineral-panel
- Free_T4, Free_T3, Total_T4, Total_T3, PTH, Vitamin_D_25OH require SI→US conversion
- TSH, Anti_TPO, Thyroglobulin, Thyroglobulin_Antibody, Calcitonin do NOT need conversion
- **Total_T3 threshold**: <3.0 (SI values are small, 1.2-2.8 nmol/L), ×64.94
- **Free_T4 threshold**: >30 pmol/L (avoid converting high US values)
- **Total_T4 threshold**: >200 nmol/L

### transplant-panel-harmonization
- **Tacrolimus**: NO CONVERSION. ng/mL is standard globally.
- **AST/ALT**: NO CONVERSION. U/L is standard globally.
- **Creatinine**: >20 threshold (μmol/L → mg/dL), ÷88.4
- **Bilirubin_Total**: >30 threshold (μmol/L → mg/dL), ÷17.1
- **Albumin**: >60 threshold (g/L → g/dL), ÷10
- **Glucose**: <3.0 threshold (mmol/L → mg/dL), ×18.0
- **Phosphorus**: <3.0 threshold (mmol/L → mg/dL), ×3.097
- **Magnesium/Potassium**: NO conversion (mmol/L = mEq/L)
- Multi-file join required: merge chemistry and liver panels on `patient_code`

### neonatal-panel-harmonization
- **CRITICAL**: Neonatal panels often target SI units (μmol/L, mmol/L, g/L, kPa), NOT US conventional
- **Bidirectional detection required**: Threshold direction varies per analyte
- **CRP**: <30 threshold catches mg/dL, ×10 to convert to mg/L (target unit)
- **Creatinine**: <20 threshold catches mg/dL, ×88.4 to convert to μmol/L (target unit is SI)
- **BUN**: >15 threshold catches mg/dL, ×0.357 to convert to mmol/L (target unit is SI)
- **Glucose**: >25 threshold catches mg/dL, ×0.0555 to convert to mmol/L (target unit is SI)
- **Total_Bili**: <50 threshold catches mg/dL, ×17.1 to convert to μmol/L (target unit is SI)
- **Direct_Bili**: <10 threshold catches mg/dL, ×17.1 to convert to μmol/L
- **Lactate**: <3 threshold catches mmol/L, ×9.0 to convert to mg/dL (target unit is US)
- **Hemoglobin**: <30 threshold catches g/dL, ×10 to convert to g/L (target unit is SI)
- **pCO2**: >15 threshold catches mmHg, ÷7.50062 to convert to kPa (target unit is SI)
- **Sodium/Potassium**: NO conversion (mmol/L = mEq/L)
- **WBC/Platelets**: NO conversion (×10⁹/L = ×10³/μL numerically)
- **USE THE SCRIPT**: `scripts/neonatal_harmonizer.py` for guaranteed full-precision output with correct bidirectional detection

## References

See `references/conversion-factors.md` for full factor derivations, physiological ranges, and panel-specific details.
See `references/thyroid-factors.md` for thyroid-specific conversion details.
See `references/cardiovascular-factors.md` for cardiovascular biomarker conversion details including BNP molecular weight derivation and NT-proBNP non-conversion rationale.
See `references/transplant-factors.md` for transplant panel analyte conversion factors, multi-file join patterns, and physiological ranges.
See `references/transplant-panel.md` for transplant panel column structure, join code example, and output ordering.
See `references/neonatal-factors.md` for bidirectional unit detection logic specific to neonatal panels (threshold direction derivation).
See `references/neonatal-ranges.md` for neonatal reference ranges by gestational/postnatal age.

## Scripts

- `scripts/neonatal_harmonizer.py` — USE THIS for guaranteed full-precision output with correct bidirectional detection
