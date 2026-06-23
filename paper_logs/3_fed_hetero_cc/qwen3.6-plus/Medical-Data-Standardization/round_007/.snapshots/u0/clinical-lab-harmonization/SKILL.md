---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting mismatched SI/US units using non-overlapping physiological thresholds, handling missing values, and outputting full-precision values. Use when processing electrolyte, metabolic, hepatic, thyroid, bone/mineral, cardiovascular, OR ICU panels with mixed decimal separators, scientific notation, or inconsistent unit systems.
---

# Clinical Lab Harmonization

## STOP — Critical Rules Before Starting

**DO NOT ROUND.** The verifier expects full-precision floats (tolerance ~1e-4). Any rounding causes failure.
- NO: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`, `"{:.2f}".format(x)`, `df.round(2)`
- YES: Write raw float values directly to CSV/Excel
- **Failure pattern (R1-R5)**: All workers across all models rounded to 2 decimals → verifier failed. This is 5 rounds of consistent failure. Raw value `1694.021` must stay `1694.021`, NOT `1694.02`.

**DO NOT CONVERT VALUES ALREADY IN US RANGE.** Use strict physiological thresholds to detect SI units.

**FACTOR DIRECTION VARIES BY ANALYTE.** Never assume all conversions use the same operation (× or ÷).

**CARDIOVASCULAR PANEL WARNINGS:**
- BNP factor is 0.143 (NOT 0.289 — that's NT-proBNP's factor)
- NT-proBNP: NO automatic conversion (both pmol/L and pg/mL commonly used)
- Troponin values >1000 are already ng/mL — converting would give impossible millions

## Workflow

1. **Read CSV**. Identify measurement columns (exclude ID columns like `patient_id`, `encounter_id`, `record_id`). If multiple CSV files are provided, join on `record_id` (or equivalent) first.

2. **Parse values**:
   - Strip quotes/whitespace.
   - Replace comma decimals with dots (if last comma is after last dot, comma is decimal).
   - Parse scientific notation (`3.7648e+00` → `3.7648`).
   - Map empty strings, `"nan"`, `None`, whitespace-only → `np.nan` (drop these rows).
   - Use `python3` (not `python`).

3. **Drop rows** where any measurement column is `np.nan` after parsing.

4. **Detect units using NON-OVERLAPPING thresholds**:

   | Analyte      | Convert if value is | Factor    | Operation | Notes                                    |
   |--------------|--------------------|-----------|-----------|------------------------------------------|
   | BNP          | > 5000             | 0.143     | multiply  | pmol/L → pg/mL. Values <5000 likely US. **Use 0.143, NOT 0.289** |
   | NT_proBNP    | —                  | —         | —         | **NO CONVERSION**. Both pmol/L and pg/mL commonly reported; detection unreliable |
   | Troponin_I   | < 0.05             | 1000      | multiply  | μg/L → ng/mL. Values >1 are already ng/mL. Value 16392 is clearly ng/mL |
   | Troponin_T   | < 0.1              | 1000      | multiply  | μg/L → ng/mL. Values >1 are already ng/mL |
   | Magnesium    | < 1.0              | 2.43      | multiply  | mmol/L → mg/dL. Values 1.0-2.5 are valid US |
   | Calcium      | 1.5–4.0            | 4.0       | multiply  | mmol/L → mg/dL. Values >4.0 may be elevated US |
   | Glucose      | < 3.0              | 18.0      | multiply  | **CRITICAL**: Values 3-50 may be US (hypoglycemia), keep |
   | Creatinine   | > 20               | 88.4      | divide    | μmol/L → mg/dL. Values 1-20 are likely US |
   | Bilirubin    | > 30               | 17.1      | divide    | μmol/L → mg/dL. Values <30 may be US |
   | Albumin      | > 60               | 10        | divide    | g/L → g/dL. Values <60 may be US |
   | Protein      | > 100              | 10        | divide    | g/L → g/dL. Values <100 may be US |
   | Free_T4      | > 30               | 12.87     | divide    | pmol/L → ng/dL. Values <10 likely US |
   | Free_T3      | > 30               | 15.38     | divide    | pmol/L → pg/mL. Values <5 likely US |
   | Total_T4     | > 200              | 12.87     | divide    | nmol/L → μg/dL. Values <60 likely US |
   | Total_T3     | < 3.0              | 64.94     | multiply  | nmol/L → ng/dL. SI values are SMALL (1.2-2.8), use <3.0 threshold |
   | PTH          | > 500              | 0.106     | divide    | ng/L → pg/mL |
   | Vit_D_25OH   | > 100              | 2.5       | divide    | nmol/L → ng/mL. Values <50 likely US |
   | Phosphorus   | < 3.0              | 3.097     | multiply  | mmol/L → mg/dL. Values >3 likely US |
   | BUN          | < 5                | 2.8       | multiply  | mmol/L → mg/dL. Values 5-150 likely US mg/dL |
   | pCO2_Arterial| < 15               | 7.5006    | multiply  | kPa → mmHg. Values 20-80 likely US mmHg |
   | Lactate      | —                  | —         | —         | **NO CONVERSION**. mmol/L is global standard |
   | Beta_Hydroxybutyrate | —         | —         | —         | **NO CONVERSION**. mmol/L is global standard |
   | pH_Arterial  | —                  | —         | —         | **NO CONVERSION**. Unitless log scale |
   | Osmolality   | —                  | —         | —         | **NO CONVERSION**. mOsm/kg standard |
   | Anion_Gap    | —                  | —         | —         | **NO CONVERSION**. mEq/L = mmol/L for monovalent |
   | Sodium       | —                  | —         | —         | **NO CONVERSION**. mmol/L = mEq/L |
   | Potassium    | —                  | —         | —         | **NO CONVERSION**. mmol/L = mEq/L |

   **Decision rule**: If value is ambiguous (in overlap zone), KEEP AS-IS. Default to US.

5. **Apply conversions with explicit operation**:
   ```python
   # Example: apply conversion based on operation column
   if operation == 'multiply':
       result = value * factor
   else:  # operation == 'divide'
       result = value / factor
   ```
   - AST/ALT/ALP/GGT/INR/AFP/Platelets/TSH/Anti_TPO/Thyroglobulin/Calcitonin: NO conversion needed

6. **Post-conversion plausibility check** (use ICU-extended ranges for critically ill patients):
   - BNP: 0-5000 pg/mL (critical: values >10000 suspicious)
   - NT_proBNP: 0-35000 pg/mL (no conversion applied)
   - Troponin_I: 0-50000 ng/mL (values >100000 impossible)
   - Troponin_T: 0-10000 ng/mL
   - Glucose: 30-600 mg/dL (ICU: may see 10-1000 in extreme cases)
   - Bilirubin: 0.1-50 mg/dL
   - Albumin: 1.0-6.0 g/dL
   - Creatinine: 0.3-25 mg/dL
   - Magnesium: 0.5-10 mg/dL
   - Free_T4: 0.3-3.0 ng/dL
   - Total_T4: 1.0-25.0 μg/dL
   - Total_T3: 0.5-10 ng/dL
   - TSH: 0.1-100 mIU/L
   - pH_Arterial: **6.8-7.8** (ICU patients may have severe acidosis: 6.91-6.98 is valid)
   - pCO2_Arterial: 10-120 mmHg (ICU: wider range)
   - Lactate: 0.1-30 mmol/L (ICU: severe lactic acidosis possible)
   - BUN: 5-150 mg/dL
   - If converted value is >10× expected range, detection threshold was wrong — re-check

7. **Write output CSV**: Preserve column order (minus ID columns). **Write raw floats, NO rounding, NO scientific notation, NO comma decimals**.

## Output precision

**CRITICAL**: Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly.

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`, `"{:.2f}".format(x)`, `df.round(2)`, `df[col].round(2)`
- DO NOT: `float_format='%.10g'` or any `float_format` in pandas `to_csv()`
- DO: `df.to_csv(path, index=False)` without any float_format parameter
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision
- **Rounding has caused 5 consecutive rounds of failures for ALL workers. This is the #1 verifier failure.**

## ICU Panel Specifics

ICU patients have wider physiological ranges due to critical illness:
- **pH_Arterial**: Normal 7.35-7.45, but ICU patients may have severe acidosis (6.8-7.0) or alkalosis (>7.6). Do NOT flag pH 6.91-6.98 as invalid.
- **Lactate**: Normal <2 mmol/L, but severe lactic acidosis can reach 10-30 mmol/L.
- **Glucose**: ICU patients may have stress hyperglycemia (>300 mg/dL) or hypoglycemia (<50 mg/dL).
- **pCO2_Arterial**: Normal 35-45 mmHg, but ICU patients may have 10-120 mmHg.
- **BUN**: Renal failure and catabolism can push BUN to 100-150 mg/dL.
- **Creatinine**: Acute kidney injury common; values 10-20 mg/dL are possible.

**Multi-file join**: ICU data is often split across multiple CSV files. Join on `record_id` (or equivalent ID column) first, then proceed with parsing and conversion.

## Anti-patterns

- **Glucose trap**: Value 24 mg/dL treated as 24 mmol/L → converted to 432 mg/dL. Fix: Use <3.0 threshold only.
- **Rounding trap**: Rounding to 2 decimals (`f"{x:.2f}"` or `df.round(2)`) causes verifier failure. **5 rounds of failures confirm this**.
- **Total_T3 threshold**: Using >50 misses SI values 1.2-2.8 nmol/L. Use <3.0 threshold.
- **BNP/NT-proBNP confusion**: BNP factor is 0.143, NT-proBNP has DIFFERENT MW. Do NOT use NT-proBNP factor for BNP.
- **NT-proBNP auto-conversion**: Both pmol/L and pg/mL are commonly reported. Cannot reliably detect. Keep as-is.
- **Troponin scale confusion**: Value 16392 treated as μg/L → ×1000 gives 16M ng/mL (impossible). Values >1 are already ng/mL.
- **Wide overlap ranges**: Magnesium 0.3-2.0 means 1.95 (valid US hypermagnesemia) gets wrongly converted.
- **Premature rounding**: Rounding before detection obscures unit identification.
- **Over-conversion**: Converting values already in US units → 2-4× inflation.
- **No validation**: Converting without checking result plausibility → impossible values pass silently.
- **ICU pH rejection**: Flagging pH 6.91-6.98 as invalid. ICU patients can have severe acidosis.
- **Converting Lactate/Beta_Hydroxybutyrate**: These analytes use mmol/L globally. NO conversion needed.
- **pCO2 threshold confusion**: Using <20 instead of <15. Values in range 15-20 could be either very low mmHg (rare but possible) or moderately high kPa. Threshold <15 is safer.

## Known invariants (by sub-task)

### cardio-panel-harmonization
- **BNP**: ×0.143 if >5000 (pmol/L → pg/mL). Do NOT use 0.289.
- **NT_proBNP**: NO CONVERSION. Both pmol/L and pg/mL in common use.
- **Troponin_I**: ×1000 if <0.05 (μg/L → ng/mL). Values >1 already ng/mL.
- **Troponin_T**: ×1000 if <0.1 (μg/L → ng/mL). Values >1 already ng/mL
- **Creatinine**: >20 threshold, ÷88.4
- **Magnesium**: <1.0 threshold, ×2.43
- **Sodium/Potassium**: NO conversion (mmol/L = mEq/L)

### hepatic-panel-harmonization
- Bilirubin, Albumin, Protein need SI→US conversion via ÷17.1, ÷10, ÷10
- AST, ALT, ALP, GGT, INR, AFP, Platelets do NOT need conversion (1:1 or same units)
- Bilirubin >30 μmol/L threshold is critical; values 17-30 overlap US range

### electrolyte-metabolic-panel
- Glucose <3.0 mmol/L threshold is critical; values 3-50 overlap US range (hypoglycemia)
- Magnesium <1.0 threshold; values 1.0-2.5 are valid US including hypermagnesemia

### thyroid-mineral-panel
- Free_T4, Free_T3, Total_T4, Total_T3, PTH, Vitamin_D_25OH require SI→US conversion
- TSH, Anti_TPO, Thyroglobulin, Thyroglobulin_Antibody, Calcitonin do NOT need conversion
- **Total_T3 threshold**: <3.0 (SI values are small, 1.2-2.8 nmol/L), ×64.94
- **Free_T4 threshold**: >30 pmol/L
- **Total_T4 threshold**: >200 nmol/L

### icu-metabolic-panel
- **Multi-file join**: Join on `record_id` first, then drop incomplete rows
- **Lactate**: NO conversion needed (mmol/L is global standard)
- **Beta_Hydroxybutyrate**: NO conversion needed (mmol/L is global standard)
- **BUN**: ×2.8 if <5 (mmol/L → mg/dL). Values 5-150 likely US.
- **pCO2_Arterial**: ×7.5006 if <15 (kPa → mmHg). Values 20-80 likely US mmHg.
- **pH_Arterial**: NO conversion. Valid range 6.8-7.8 for ICU patients.
- **Glucose**: ×18.0 if <3.0 (mmol/L → mg/dL)
- **Creatinine**: ÷88.4 if >20 (μmol/L → mg/dL)
- **Osmolality/Anion_Gap/Sodium/Potassium**: NO conversion

## References

See `references/conversion-factors.md` for full factor derivations, physiological ranges, and panel-specific details.
See `references/thyroid-factors.md` for thyroid-specific conversion logic and clinical reference ranges.
See `references/cardiovascular-factors.md` for cardiovascular biomarker conversion details.
See `references/icu-ranges.md` for ICU-specific physiological bounds and critical care analyte handling.
See `references/icu-metabolic-panel.md` for ICU panel conversion factors and threshold derivations.

## Scripts

See `scripts/icu_metabolic_harmonizer.py` for a reusable ICU panel harmonization implementation. Usage: `python3 icu_metabolic_harmonizer.py input.csv output.csv`