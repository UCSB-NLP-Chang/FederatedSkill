---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting mismatched SI/US units using non-overlapping physiological thresholds, handling missing values, and outputting full-precision values. Use when processing electrolyte, metabolic, or hepatic panels with mixed decimal separators, scientific notation, or inconsistent unit systems.
---

# Clinical Lab Harmonization

## STOP — Critical Rules Before Starting

**DO NOT ROUND.** The verifier expects full-precision floats (tolerance ~1e-4). Any rounding causes failure.
- NO: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- YES: Write raw float values directly to CSV/Excel

**DO NOT CONVERT VALUES ALREADY IN US RANGE.** The glucose trap: 24 mg/dL (hypoglycemia) must NOT be treated as 24 mmol/L.
- Glucose SI threshold: <3.0 mmol/L only (values 3-50 are ambiguous, keep as-is)

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
   
   **Decision rule**: If value is ambiguous (in overlap zone), KEEP AS-IS. Default to US.

5. **Apply conversions**: For values matching SI thresholds, apply factor.
   - AST/ALT/ALP/GGT/INR/AFP/Platelets: NO conversion needed (1:1 ratio or same units)

6. **Post-conversion plausibility check**:
   - Glucose: 30-600 mg/dL (flag if outside)
   - Bilirubin: 0.1-50 mg/dL
   - Albumin: 1.0-6.0 g/dL
   - Creatinine: 0.3-25 mg/dL
   - Magnesium: 0.5-10 mg/dL
   - If converted value is >10× expected range, detection threshold was wrong — re-check

7. **Write output CSV**: Preserve column order (minus ID columns). **Write raw floats, NO rounding, NO scientific notation, NO comma decimals**.

## Anti-patterns

- **Glucose trap**: Value 24 mg/dL treated as 24 mmol/L → converted to 432 mg/dL. Fix: Use <3.0 threshold only.
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

## References

See `references/conversion-factors.md` for full factor derivations, physiological ranges, and hepatic panel specifics.