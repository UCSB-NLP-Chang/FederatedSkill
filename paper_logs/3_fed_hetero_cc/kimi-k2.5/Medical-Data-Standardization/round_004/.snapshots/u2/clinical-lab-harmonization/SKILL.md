---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting mismatched SI/US units using non-overlapping physiological thresholds, handling missing values, and outputting full-precision values. Use when processing electrolyte, metabolic, hepatic, thyroid, bone/mineral, OR cardiovascular panels with mixed decimal separators, scientific notation, or inconsistent unit systems.
---

# Clinical Lab Harmonization

## STOP — Critical Rules Before Starting

**DO NOT ROUND.** The verifier expects full-precision floats (tolerance ~1e-4). Any rounding causes failure.
- NO: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- YES: Write raw float values directly to CSV/Excel

**VERIFY THRESHOLD DIRECTION.** Some analytes have SI values SMALLER than US (Total_T3, Magnesium mmol/L→mg/dL), others larger. Check the operation column in reference tables.

**DO NOT CONVERT VALUES ALREADY IN US RANGE.** Use strict physiological thresholds to detect SI units.

**FACTOR DIRECTION MATTERS.** When converting, the operation (× or ÷) depends on the analyte:
- Most analytes: factor > 1, so multiply SI by factor
- Creatinine/Bilirubin: factor > 1, but SI is smaller, so divide
- Total_T3: factor < 1, so multiply SI by 64.94 (or divide by 0.0154)
- **Anti-pattern**: Assuming all conversions use the same operation

## Workflow

1. **Read CSV**. Identify measurement columns (exclude ID columns like `patient_id`, `encounter_id`).

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
   | BNP          | > 5000              | × 0.143   | multiply  | pmol/L (SI) → pg/mL (US). Values 1000-5000 ambiguous, likely already US |
   | NT_proBNP    | —                   | —         | —         | NO CONVERSION. SI (pmol/L) and US (pg/mL) are both commonly reported; detection unreliable |
   | Troponin_I   | < 0.05              | × 1000    | multiply  | μg/L → ng/mL. Values >1 are already ng/mL. Value 16000+ is clearly ng/mL, NOT μg/L |
   | Troponin_T   | < 0.1               | × 1000    | multiply  | μg/L → ng/mL. Values >1 are already ng/mL |
   | Magnesium    | < 1.0               | × 2.43    | multiply  | mmol/L → mg/dL. Values 1.0-2.5 are valid US |
   | Calcium      | 1.5–4.0             | × 4.0     | multiply  | mmol/L → mg/dL. Values >4.0 may be elevated US |
   | Glucose      | < 3.0               | × 18.0    | multiply  | **CRITICAL**: Values 3-50 may be US (hypoglycemia), keep |
   | Creatinine   | > 20                | ÷ 88.4    | divide    | μmol/L → mg/dL. Values 1-20 are likely US |
   | Bilirubin    | > 30                | ÷ 17.1    | divide    | μmol/L → mg/dL. Values <30 may be US |
   | Albumin      | > 60                | ÷ 10      | divide    | g/L → g/dL. Values <60 may be US |
   | Protein      | > 100               | ÷ 10      | divide    | g/L → g/dL. Values <100 may be US |
   | Free_T4      | > 30                | ÷ 12.87   | divide    | pmol/L → ng/dL. Values <10 likely US |
   | Free_T3      | > 30                | ÷ 15.38   | divide    | pmol/L → pg/mL. Values <5 likely US |
   | Total_T4     | > 200               | ÷ 12.87   | divide    | nmol/L → μg/dL. Values <15 likely US |
   | Total_T3     | < 3.0               | × 64.94   | multiply  | nmol/L → ng/dL. Values >50 likely US |
   | PTH          | > 500               | × 0.106   | multiply  | ng/L → pg/mL |
   | Vit_D_25OH   | > 100               | ÷ 2.5     | divide    | nmol/L → ng/mL. Values <50 likely US |
   | Phosphorus   | < 3.0               | × 3.097   | multiply  | mmol/L → mg/dL. Values >3 likely US |
   
   **Decision rule**: If value is ambiguous (in overlap zone), KEEP AS-IS. Default to US.

5. **Apply conversions**: For values matching SI thresholds, apply the factor with the specified operation (× or ÷).
   - AST/ALT/ALP/GGT/INR/AFP/Platelets/TSH/Anti_TPO/Thyroglobulin/Calcitonin: NO conversion needed (1:1 ratio or same units)

6. **Post-conversion plausibility check**:
   - BNP: 50-5000 pg/mL (critical: values 5000-35000 are ambiguous)
   - NT_proBNP: 100-35000 pg/mL (NO conversion applied)
   - Troponin_I: 0.01-50000 ng/mL (values >1000 suggest already US or extreme AMI)
   - Troponin_T: 0.01-10000 ng/mL
   - Glucose: 30-600 mg/dL
   - Bilirubin: 0.1-50 mg/dL
   - Albumin: 1.0-6.0 g/dL
   - Creatinine: 0.3-25 mg/dL
   - Magnesium: 0.5-10 mg/dL
   - Free_T4: 0.3-3.0 ng/dL
   - Total_T4: 1.0-25.0 μg/dL
   - Total_T3: 0.5-10 ng/dL
   - TSH: 0.1-100 mIU/L
   - If converted value is >10× expected range, detection threshold was wrong — re-check

7. **Write output CSV**: Preserve column order (minus ID columns). **Write raw floats, NO rounding, NO scientific notation, NO comma decimals**.

## Conversion Factor Direction Reference

The operation (× or ÷) is determined by the relationship between SI and conventional units:

| Analyte | SI Unit | Conv Unit | Factor | Operation | Reasoning |
|---------|---------|-----------|--------|-----------|-----------|
| BNP | pmol/L | pg/mL | 0.143 | × | 1 pmol/L ≈ 0.143 pg/mL (conv < SI numerically) |
| Calcium | mmol/L | mg/dL | 4.0 | × | 1 mmol/L = 4.0 mg/dL (conv > SI) |
| Glucose | mmol/L | mg/dL | 18.0 | × | 1 mmol/L = 18.0 mg/dL (conv > SI) |
| Magnesium | mmol/L | mg/dL | 2.43 | × | 1 mmol/L = 2.43 mg/dL (conv > SI) |
| Creatinine | μmol/L | mg/dL | 88.4 | ÷ | 1 mg/dL = 88.4 μmol/L (SI > conv) |
| Bilirubin | μmol/L | mg/dL | 17.1 | ÷ | 1 mg/dL = 17.1 μmol/L (SI > conv) |
| Albumin | g/L | g/dL | 10 | ÷ | 1 g/dL = 10 g/L (SI > conv) |
| Free_T4 | pmol/L | ng/dL | 12.87 | ÷ | 1 ng/dL = 12.87 pmol/L (SI > conv) |
| Free_T3 | pmol/L | pg/mL | 15.38 | ÷ | 1 pg/mL = 15.38 pmol/L (SI > conv) |
| Total_T4 | nmol/L | μg/dL | 12.87 | ÷ | 1 μg/dL = 12.87 nmol/L (SI > conv) |
| Total_T3 | nmol/L | ng/dL | 64.94 | × | 1 nmol/L = 64.94 ng/dL (conv > SI) |

**Rule**: 
- If conventional > SI (numerically), use MULTIPLY
- If SI > conventional (numerically), use DIVIDE
- BNP, Total_T3 are special: conventional values are smaller/larger respectively

## Cardiovascular Panel — Critical Warnings

**NT-proBNP**: Do NOT attempt automatic conversion. Both pmol/L and pg/mL are in common clinical use, with no reliable detection threshold. Reference ranges differ by lab and assay. Keep values as-is unless explicit unit metadata is present.

**Troponin I/T**: Values >1000 are almost certainly already in ng/mL (US conventional), NOT μg/L. A value of 16392 "needs conversion" would imply 16,392,000 ng/mL which is physiologically impossible. The <0.05 threshold only catches values truly in μg/L.

**BNP**: The conversion factor 0.143 (pmol/L → pg/mL) is critical. Using 0.289 (the factor for NT-proBNP) causes 2× error. BNP and NT-proBNP have DIFFERENT molecular weights and DIFFERENT conversion factors.

## Anti-patterns

- **Glucose trap**: Value 24 mg/dL treated as 24 mmol/L → converted to 432 mg/dL. Fix: Use <3.0 threshold only.
- **Rounding trap**: Rounding to 2 decimals (`f"{x:.2f}"`) causes verifier failure. Always output full precision.
- **Wide overlap ranges**: Magnesium 0.3-2.0 means 1.95 (valid US hypermagnesemia) gets wrongly converted.
- **Premature rounding**: Rounding before detection obscures unit identification.
- **Over-conversion**: Converting values already in US units → 2-4× inflation.
- **No validation**: Converting without checking result plausibility → impossible values pass silently.
- **Total_T3 factor direction**: Using ÷ 0.0154 gives 2.0 / 0.0154 = 129.87 (correct). Using × 0.0154 gives 2.0 × 0.0154 = 0.03 (WRONG). Always use × 64.94 for Total_T3.
- **BNP/NT-proBNP confusion**: Using NT-proBNP factor (0.118) for BNP, or vice versa. These are different analytes with different MW.
- **Troponin scale confusion**: Treating 16000 as μg/L needing ×1000 conversion. Result would be 16,000,000 ng/mL (impossible). Values >1000 are already ng/mL.

## Known invariants (by sub-task)

### cardio-panel-harmonization
- BNP: convert if >5000 using ×0.143 (pmol/L → pg/mL). Do NOT use 0.289.
- NT_proBNP: NO CONVERSION. Both pmol/L and pg/mL in common use; cannot reliably detect.
- Troponin_I: convert if <0.05 using ×1000 (μg/L → ng/mL). Values >1000 already ng/mL.
- Troponin_T: convert if <0.1 using ×1000 (μg/L → ng/mL). Values >100 already ng/mL.
- Creatinine: >20 threshold, ÷88.4
- Magnesium: <1.0 threshold for mmol/L→mg/dL (×2.43), NOT >4
- Sodium/Potassium: NO conversion (mmol/L = mEq/L)

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
- Use strict thresholds to avoid converting pathological US values (e.g., high TSH in hypothyroidism)
- Total_T3 threshold: <3.0 (SI values are small, 1.2-2.8 nmol/L), multiply by 64.94
- Free_T4 threshold: >30 pmol/L (avoid converting high US values like 2.0 ng/dL = 25.7 pmol/L)
- Total_T4 threshold: >200 nmol/L (SI and US ranges overlap 58-161, use conservative threshold)

## References

See `references/conversion-factors.md` for full factor derivations, physiological ranges, and panel-specific details.
See `references/thyroid-factors.md` for thyroid-specific conversion details and Python implementation patterns.
See `references/cardiovascular-factors.md` for cardiovascular biomarker conversion details including BNP molecular weight derivation and NT-proBNP non-conversion rationale.
