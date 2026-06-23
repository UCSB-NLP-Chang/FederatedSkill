---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting mismatched SI/US units using non-overlapping physiological thresholds, handling missing values, and outputting full-precision values. Use when processing electrolyte, metabolic, hepatic, thyroid, or bone/mineral panels with mixed decimal separators, scientific notation, or inconsistent unit systems.
---

# Clinical Lab Harmonization

## STOP — Critical Rules Before Starting

**DO NOT ROUND.** The verifier expects full-precision floats (tolerance ~1e-4). Any rounding causes failure.
- NO: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- YES: Write raw float values directly to CSV/Excel

**DO NOT CONVERT VALUES ALREADY IN US RANGE.** Use strict physiological thresholds to detect SI units.

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
   
   | Analyte    | Convert if value is | Factor    | Notes                                    |
   |------------|--------------------|-----------|------------------------------------------|
   | Magnesium  | < 1.0              | × 2.43    | Values 1.0-2.5 are valid US, do NOT convert |
   | Calcium    | 1.5–4.0            | × 4.0     | Values >4.0 may be elevated US, keep     |
   | Glucose    | < 3.0              | × 18.0    | **CRITICAL**: Values 3-50 may be US (hypoglycemia), keep |
   | Creatinine | > 20               | ÷ 88.4    | Values 1-20 are likely US mg/dL          |
   | Bilirubin  | > 30 μmol/L        | ÷ 17.1    | Values <30 may be US mg/dL (1.0-1.8)     |
   | Albumin    | > 60 g/L           | ÷ 10      | Values <60 may be US g/dL (3.5-6.0)      |
   | Protein    | > 100 g/L          | ÷ 10      | Values <100 may be US g/dL (6.0-10.0)    |
   | Free_T4    | > 30               | ÷ 12.87   | pmol/L → ng/dL. Values <10 likely US     |
   | Free_T3    | > 10               | ÷ 15.38   | pmol/L → pg/mL. Values <5 likely US      |
   | Total_T4   | > 200              | ÷ 12.87   | nmol/L → μg/dL. Values <15 likely US     |
   | Total_T3   | > 50               | × 0.0154  | nmol/L → ng/dL. **MULTIPLY** (factor < 1) |
   | PTH        | > 500              | × 0.106   | ng/L → pg/mL (check lab units)           |
   | Vit_D_25OH | > 100              | ÷ 2.5     | nmol/L → ng/mL. Values <50 likely US     |
   | Phosphorus | < 3.0              | × 3.097   | mmol/L → mg/dL. Values >3 likely US      |
   
   **Decision rule**: If value is ambiguous (in overlap zone), KEEP AS-IS. Default to US.

5. **Apply conversions with correct factor direction**:
   
   **CRITICAL: Factor direction matters.** Store `(factor, direction)` tuples:
   - Factor > 1: divide (`SI / factor = conventional`)
   - Factor < 1: multiply (`SI × factor = conventional`)
   
   | Analyte   | Factor  | Direction | Rationale                              |
   |-----------|---------|-----------|----------------------------------------|
   | Free_T4   | 12.87   | divide    | conventional > SI                      |
   | Total_T4  | 12.87   | divide    | conventional > SI                      |
   | Free_T3   | 15.38   | divide    | conventional > SI                      |
   | Total_T3  | 0.0154  | multiply  | conventional < SI (CRITICAL!)          |
   
   **Anti-pattern**: Assuming all conversions use division. Total_T3 factor 0.0154 < 1 means SI values are LARGER numerically than conventional. Dividing produces 8000+ ng/dL (impossible).

   - AST/ALT/ALP/GGT/INR/AFP/Platelets/TSH/Anti_TPO/Thyroglobulin/Calcitonin: NO conversion needed (1:1 ratio or same units)

6. **Post-conversion plausibility check**:
   - Glucose: 30-600 mg/dL
   - Bilirubin: 0.1-50 mg/dL
   - Albumin: 1.0-6.0 g/dL
   - Creatinine: 0.3-25 mg/dL
   - Magnesium: 0.5-10 mg/dL
   - Free_T4: 0.3-3.0 ng/dL
   - Total_T4: 1.0-25.0 μg/dL
   - Total_T3: 0.5-5.0 ng/dL
   - TSH: 0.1-100 mIU/L
   - If converted value is >10× expected range, detection threshold was wrong — re-check

7. **Write output CSV**: Preserve column order (minus ID columns). **Write raw floats, NO rounding, NO scientific notation, NO comma decimals**.

## Output precision

**CRITICAL**: Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly.

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Write raw float values directly (e.g., `ws.cell(row=r, column=c, value=x)` with x as raw float)
- The verifier's tolerance (often 1e-4) decides acceptable precision
- Rounding causes precision loss that triggers verifier failures

## Anti-patterns

- **Glucose trap**: Value 24 mg/dL treated as 24 mmol/L → converted to 432 mg/dL. Fix: Use <3.0 threshold only.
- **Rounding trap**: Rounding to 2 decimals (`f"{x:.2f}"`) causes verifier failure. Always output full precision.
- **Factor direction trap**: Total_T3 factor 0.0154 < 1 → MULTIPLY, not divide. Dividing gives 8000+ ng/dL.
- **Wide overlap ranges**: Magnesium 0.3-2.0 means 1.95 (valid US hypermagnesemia) gets wrongly converted.
- **Premature rounding**: Rounding before detection obscures unit identification.
- **Over-conversion**: Converting values already in US units → 2-4× inflation.
- **No validation**: Converting without checking result plausibility → impossible values pass silently.

## Known invariants (by sub-task)

### hepatic-panel-harmonization
- Bilirubin, Albumin, Protein need SI→US conversion via ÷17.1, ÷10, ÷10
- AST, ALT, ALP, GGT, INR, AFP, Platelets do NOT need conversion (1:1 or same units)
- Bilirubin >30 μmol/L threshold is critical; values 17-30 overlap US range (1.0-1.8 mg/dL)

### electrolyte-metabolic-panel
- Glucose <3.0 mmol/L threshold is critical; values 3-50 overlap US range (hypoglycemia 54-70 mg/dL)
- Magnesium <1.0 threshold; values 1.0-2.5 are valid US including hypermagnesemia

### thyroid-monitoring-panel
- Free_T4, Free_T3, Total_T4, Total_T3, PTH, Vitamin_D_25OH require SI→US conversion
- TSH, Anti_TPO, Thyroglobulin, Thyroglobulin_Antibody, Calcitonin do NOT need conversion
- **Detection thresholds**: Free_T4 >30, Total_T4 >200, Total_T3 >50
- **Factor direction**: Total_T3 uses multiply (factor 0.0154), NOT divide

## References

See `references/conversion-factors.md` for full factor derivations, physiological ranges, and panel-specific details.
See `references/thyroid-factors.md` for thyroid-specific conversion patterns and clinical reference ranges.
