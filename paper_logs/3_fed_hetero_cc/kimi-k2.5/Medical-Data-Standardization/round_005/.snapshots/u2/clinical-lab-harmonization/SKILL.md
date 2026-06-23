---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting mismatched SI/US units using non-overlapping physiological thresholds, handling missing values, deduplicating multi-draw cases, and outputting full-precision values. Use when processing electrolyte, metabolic, hepatic, thyroid, bone/mineral, cardiovascular, OR oncology follow-up panels with mixed decimal separators, scientific notation, or inconsistent unit systems.
---

# Clinical Lab Harmonization

## STOP — Critical Rules Before Starting

**DO NOT ROUND.** The verifier expects full-precision floats (tolerance ~1e-4). Any rounding causes failure.
- NO: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`, `"{:.2f}".format(x)`
- YES: Write raw float values directly to CSV/Excel
- **Failure pattern (R3)**: Agent rounded to 2 decimals → verifier failed. Raw value `690.021` must stay as `690.021`, NOT rounded to `690.02`.

**DO NOT CONVERT VALUES ALREADY IN US RANGE.** Use strict physiological thresholds to detect SI units.

**FACTOR DIRECTION VARIES BY ANALYTE.** Never assume all conversions use the same operation (× or ÷).

**DO NOT USE PLAUSIBLE-RANGE HEURISTICS.** Use the specific non-overlapping thresholds in the table below. A "check if value is in plausible US range, then convert if not" approach produces wrong results because many SI values fall within plausible US ranges after wrong conversion.

## Workflow

1. **Read CSV**. Identify measurement columns (exclude ID columns like `patient_id`, `encounter_id`, `case_id`, `draw_order`).

2. **Deduplicate multi-draw cases** (if `case_id`/`draw_order` columns exist):
   - Group rows by `case_id`
   - For each case, select the row with the **highest `draw_order`** that has **all measurement columns non-missing**
   - If the highest draw_order has missing values, try the next highest
   - Drop `case_id` and `draw_order` from output

3. **Parse values**:
   - Strip quotes/whitespace.
   - **Comma handling — CRITICAL**: Distinguish comma-as-decimal from comma-as-thousands-separator:
     - If value has ONE comma and NO dots: comma is decimal → replace with dot (e.g., `"3,2591"` → `3.2591`)
     - If value has comma AND dot: dot is decimal, comma is thousands → remove comma (e.g., `"1.234,56"` → `1234.56`; `"1,234.56"` → `1234.56`)
     - If value has multiple commas with no dots: last comma is decimal, others are thousands → remove thousands commas, replace last with dot
     - **NEVER** blindly replace all commas with dots — this corrupts thousand-separated values like `"615,1100"` (which is `615.1100`, not `615.1100` from `6151100`)
   - Parse scientific notation (`3.7648e+00` → `3.7648`).
   - Map empty strings, `"nan"`, `None`, whitespace-only → `np.nan` (drop these rows).
   - Use `python3` (not `python`).

4. **Drop rows** where any measurement column is `np.nan` after parsing.

5. **Detect units using NON-OVERLAPPING thresholds**:

   | Analyte      | Convert if value is  | Factor    | Operation | Notes                                    |
   |--------------|---------------------|-----------|-----------|------------------------------------------|
   | BNP          | > 5000              | 0.143     | multiply  | pmol/L → pg/mL. **CRITICAL: factor is 0.143, NOT 0.289** |
   | NT_proBNP    | —                   | —         | —         | **NO CONVERSION**. Detection unreliable  |
   | Troponin_I   | < 0.05              | 1000      | multiply  | μg/L → ng/mL. Values >1 are already ng/mL |
   | Troponin_T   | < 0.1               | 1000      | multiply  | μg/L → ng/mL. Values >1 are already ng/mL |
   | Magnesium    | < 1.0               | 2.43      | multiply  | mmol/L → mg/dL. Values 1.0-2.5 are valid US |
   | Calcium      | 1.5–4.0             | 4.0       | multiply  | mmol/L → mg/dL. Values >4.0 may be elevated US |
   | Glucose      | < 3.0               | 18.0      | multiply  | **CRITICAL**: Values 3-50 may be US (hypoglycemia), keep |
   | Creatinine   | > 20                | 88.4      | divide    | μmol/L → mg/dL. Values 1-20 are likely US |
   | Uric_Acid    | > 20                | 59.48     | divide    | μmol/L → mg/dL. Values 2-15 are likely US mg/dL |
   | Bilirubin    | > 30                | 17.1      | divide    | μmol/L → mg/dL. Values <30 may be US |
   | Albumin      | > 60                | 10        | divide    | g/L → g/dL. Values <60 may be US |
   | Protein      | > 100               | 10        | divide    | g/L → g/dL. Values <100 may be US |
   | Free_T4      | > 30                | 12.87     | divide    | pmol/L → ng/dL. Values <10 likely US |
   | Free_T3      | > 30                | 15.38     | divide    | pmol/L → ng/dL. Values <5 likely US |
   | Total_T4     | > 200               | 12.87     | divide    | nmol/L → μg/dL. Values <60 likely US |
   | Total_T3     | < 3.0               | 64.94     | multiply  | nmol/L → ng/dL. SI values are SMALL (1.2-2.8), use <3.0 threshold |
   | PTH          | > 500               | 0.106     | divide    | ng/L → pg/mL |
   | Vit_D_25OH   | > 100               | 2.5       | divide    | nmol/L → ng/mL. Values <50 likely US |
   | Phosphorus   | < 3.0               | 3.097     | multiply  | mmol/L → mg/dL. Values >3 likely US |
   | LDH          | —                   | —         | —         | **NO CONVERSION**. U/L in both SI and US |
   | WBC_Count    | —                   | —         | —         | **NO CONVERSION**. ×10⁹/L = ×10³/μL (same scale) |
   | Potassium    | —                   | —         | —         | **NO CONVERSION**. mmol/L = mEq/L |
   | Sodium       | —                   | —         | —         | **NO CONVERSION**. mmol/L = mEq/L |

   **Decision rule**: If value is ambiguous (in overlap zone), KEEP AS-IS. Default to US.

6. **Apply conversions with explicit operation**:
   ```python
   if operation == 'multiply':
       result = value * factor
   else:  # operation == 'divide'
       result = value / factor
   ```
   - AST/ALT/ALP/GGT/INR/AFP/Platelets/TSH/Anti_TPO/Thyroglobulin/Calcitonin: NO conversion needed

7. **Post-conversion plausibility check**:
   - BNP: 0-5000 pg/mL; NT_proBNP: 0-35000 pg/mL
   - Troponin_I: 0-50000 ng/mL; Troponin_T: 0-10000 ng/mL
   - Glucose: 30-600 mg/dL; Creatinine: 0.3-25 mg/dL
   - Uric_Acid: 2-15 mg/dL (values >20 after conversion suspicious)
   - Bilirubin: 0.1-50 mg/dL; Albumin: 1.0-6.0 g/dL
   - Magnesium: 0.5-10 mg/dL; Calcium: 6-14 mg/dL
   - Phosphorus: 1-15 mg/dL; LDH: 100-1500 U/L
   - Free_T4: 0.3-3.0 ng/dL; Total_T4: 1.0-25.0 μg/dL
   - Total_T3: 0.5-10 ng/dL; TSH: 0.1-100 mIU/L
   - If converted value is >10× expected range, detection threshold was wrong — re-check

8. **Write output CSV**: Preserve column order (minus ID columns). **Write raw floats, NO rounding, NO scientific notation, NO comma decimals**.

## Output precision

**CRITICAL**: Never round, truncate, or fixed-format numeric values when writing outputs.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`, `"{:.2f}".format(x)`
- DO: Write raw float values directly (e.g., `ws.cell(row=r, column=c, value=x)` with x as raw float)
- The verifier's tolerance (often 1e-4) decides acceptable precision

## Anti-patterns

- **Rounding trap**: Rounding to 2 decimals causes verifier failure. Always output full precision.
- **Plausible-range heuristic**: Checking "is value in US range? if not, convert" is WRONG. Use specific thresholds. SI values can land in plausible US range after wrong conversion.
- **Glucose trap**: Value 24 mg/dL treated as 24 mmol/L → converted to 432 mg/dL. Fix: Use <3.0 threshold only.
- **Total_T3 threshold**: Using >50 misses SI values 1.2-2.8 nmol/L. Use <3.0 threshold.
- **BNP/NT-proBNP confusion**: BNP factor is 0.143, NT-proBNP has DIFFERENT MW.
- **NT-proBNP auto-conversion**: Cannot reliably detect. Keep as-is.
- **Troponin scale confusion**: Values >1 are already ng/mL.
- **Comma-as-decimal vs thousands**: Blindly replacing all commas with dots corrupts thousand-separated values. Parse contextually.
- **Over-conversion**: Converting values already in US units → 2-4× inflation.
- **No validation**: Converting without checking result plausibility → impossible values pass silently.
- **Uric_Acid threshold**: Values 2-15 are normal US mg/dL. Only convert if >20 (clearly μmol/L).
- **Phosphorus direction**: SI mmol/L values are SMALL (<3.0). Multiply by 3.097, do NOT divide.

## Known invariants (by sub-task)

### cardio-panel-harmonization
- **BNP**: ×0.143 if >5000. Do NOT use 0.289 or ÷8.457.
- **NT_proBNP**: NO CONVERSION.
- **Troponin_I**: ×1000 if <0.05. Values >1 already ng/mL.
- **Troponin_T**: ×1000 if <0.1. Values >1 already ng/mL.
- **Creatinine**: >20 threshold, ÷88.4
- **Magnesium**: <1.0 threshold, ×2.43
- **Sodium/Potassium**: NO conversion

### hepatic-panel-harmonization
- Bilirubin, Albumin, Protein: ÷17.1, ÷10, ÷10
- AST, ALT, ALP, GGT, INR, AFP, Platelets: NO conversion

### electrolyte-metabolic-panel
- Glucose <3.0 mmol/L threshold; values 3-50 overlap US range
- Magnesium <1.0 threshold; values 1.0-2.5 are valid US

### thyroid-mineral-panel
- Free_T4, Free_T3, Total_T4, Total_T3, PTH, Vitamin_D_25OH require SI→US conversion
- TSH, Anti_TPO, Thyroglobulin, Calcitonin: NO conversion
- **Total_T3 threshold**: <3.0, ×64.94
- **Free_T4 threshold**: >30 pmol/L
- **Total_T4 threshold**: >200 nmol/L

### oncology-followup-panel
- **Deduplication**: Select highest complete draw_order per case_id
- **LDH**: NO conversion (U/L same in SI and US)
- **Uric_Acid**: >20 threshold, ÷59.48 (μmol/L → mg/dL)
- **WBC_Count**: NO conversion (×10⁹/L = ×10³/μL)
- **Phosphorus**: <3.0 threshold, ×3.097 (mmol/L → mg/dL)
- **Creatinine**: >20 threshold, ÷88.4
- **Calcium**: 1.5-4.0 range, ×4.0
- **Albumin**: >60 threshold, ÷10
- **Glucose**: <3.0 threshold, ×18.0
- **Magnesium**: <1.0 threshold, ×2.43
- **Potassium**: NO conversion

## References

See `references/conversion-factors.md` for full factor derivations, physiological ranges, and panel-specific details.
See `references/thyroid-factors.md` for thyroid-specific conversion details.
See `references/cardiovascular-factors.md` for cardiovascular biomarker conversion details.
See `references/oncology-factors.md` for oncology follow-up panel details including Uric_Acid derivation and deduplication workflow.
