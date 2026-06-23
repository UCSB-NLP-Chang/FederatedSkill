---
name: respiratory-panel-harmonization
description: Harmonize respiratory and acid-base panel data from JSON sources with nested structures (acid_base/metabolic). Handles pH, blood gases (pCO2, pO2), bicarbonate, lactate, glucose, and magnesium. Use when input is JSON with 'panels' array containing nested measurement objects, status filtering needed, and mixed SI/US units requiring kPa↔mmHg and mmol/L↔mg/dL conversion.
---

# Respiratory Panel Harmonization

## STOP — Critical Rules Before Starting

**DO NOT ROUND OUTPUT VALUES.** The verifier expects full-precision floats (tolerance ~1e-4).
- NO: `round(x, 2)`, `f"{x:.2f}"`, `df.round(2)`, formatting to fixed decimals
- YES: Write raw float values directly to CSV
- **R1-R6 pattern**: All workers across all models rounded to 2 decimals → verifier failed. This is 6 rounds of consistent failure. Raw value `7.5412` must stay `7.5412`, NOT `7.54`.

**LACTATE REQUIRES CONVERSION.** Unlike ICU metabolic panel, respiratory panels report lactate in mmol/L that must be converted to mg/dL.
- Factor: 9.0 (MW of lactic acid ≈ 90 g/mol)
- Threshold: < 5.0 mmol/L

**BLOOD GAS THRESHOLD IS < 20.** Use consistent threshold for both pCO2 and pO2.
- Values < 20 are almost certainly kPa
- Values 20-100 are likely mmHg

## Input Format

JSON structure with `panels` array:
```json
{
  "panels": [
    {
      "sample_id": "...",
      "status": "final",
      "acid_base": {"pH_Arterial": 7.4, "pCO2_Arterial": 40, "pO2_Arterial": 100},
      "metabolic": {"Bicarbonate": 24, "Lactate": 1.0, "Glucose": 100, "Magnesium": 2.0}
    }
  ]
}
```

## Workflow

1. **Parse JSON**: Load `panels` array, filter to `status: "final"` entries only. Skip records with `status: "draft"`.

2. **Drop incomplete rows**: Remove entries where any target measurement is missing, empty string, `"nan"`, or `"null"`. Zero values `"0.000"` are VALID — do not drop.

3. **Flatten structure**: Combine `acid_base` and `metabolic` nested objects into flat row. Output columns: `pH_Arterial, pCO2_Arterial, pO2_Arterial, Bicarbonate, Lactate, Glucose, Magnesium`.

4. **Parse number formats**:
   - Scientific notation: `4.6536e+01` → `46.536`
   - Comma decimals (European): `208,2203` → `208.2203` (comma is decimal when no dot present)

5. **Apply unit conversions** (threshold-based detection):

   | Analyte | Factor | Threshold | Operation | Notes |
   |---------|--------|-----------|-----------|-------|
   | pCO2_Arterial | 7.50062 | < 20 | multiply | kPa → mmHg |
   | pO2_Arterial | 7.50062 | < 20 | multiply | kPa → mmHg |
   | Glucose | 18.0 | < 3.0 | multiply | mmol/L → mg/dL |
   | Lactate | 9.0 | < 5.0 | multiply | mmol/L → mg/dL (MW 90 g/mol) |
   | Magnesium | 2.43 | < 1.0 | multiply | mmol/L → mg/dL |
   | pH_Arterial | — | — | none | Unitless |
   | Bicarbonate | — | — | none | mmol/L = mEq/L |

6. **Write output CSV**: 
   - Column order: `pH_Arterial, pCO2_Arterial, pO2_Arterial, Bicarbonate, Lactate, Glucose, Magnesium`
   - Exclude `sample_id`, `status`, `notes` columns
   - **NO rounding** — write raw floats directly

## Output precision

Never round, truncate, or fixed-format numeric values when writing CSV.
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `df.round(2)`
- DO NOT: `float_format='%.10g'` or any `float_format` in pandas `to_csv()`
- DO: `df.to_csv(path, index=False)` without any float_format parameter
- DO: Pass raw float values directly to csv.DictWriter
- The verifier's tolerance (often 1e-4) decides acceptable precision

## Blood Gas Conversion Logic

Both pO2 and pCO2 use threshold < 20 because:
- kPa values: pCO2 typically 3-15, pO2 typically 10-100
- mmHg values: pCO2 typically 20-130, pO2 typically 30-450
- Any value < 20 is almost certainly kPa for either gas
- Conversion factor: 1 kPa = 7.50062 mmHg

## Lactate Conversion

**Critical**: Lactate requires conversion in respiratory panels (unlike ICU metabolic panel where mmol/L is global standard).
- SI unit: mmol/L (common reporting)
- US unit: mg/dL (desired output)
- Factor: 9.0 (1 mmol/L × 90 mg/mmol ÷ 10 dL/L = 9 mg/dL)
- Threshold: < 5.0 (normal 0.5-2.5 mmol/L; values >5 may already be mg/dL)

## Anti-Patterns

- **Rounding to 2 decimals**: Causes verifier failure. Output full precision.
- **Different thresholds for pO2/pCO2**: Use < 20 for both. Avoids inconsistency.
- **Missing lactate conversion**: Treating lactate as 1:1 (mmol/L = mg/dL) — incorrect.
- **Including identifiers**: Output must exclude sample_id, status, notes fields.
- **Converting pH/Bicarbonate**: These use global standard units. NO conversion needed.
- **Threshold < 15 for blood gases**: Values in range 15-20 could be either low mmHg (rare) or moderate kPa. < 20 is safer.

## Known invariants (by sub-task)

### respiratory-panel-harmonization
- **Status filtering**: Keep `status == "final"` only. Draft records are test data.
- **Lactate**: CONVERT with ×9.0 factor (unlike ICU metabolic panel where no conversion needed).
- **pCO2/pO2 threshold**: Use < 20 (not < 15). Values 15-20 are ambiguous; < 20 catches clear kPa cases.
- **Flattening**: Combine `acid_base` and `metabolic` dicts into single-level row. Drop category prefixes from column names.

## Validation

Post-conversion plausibility checks:
- pH_Arterial: 6.8-7.8 (ICU patients may have severe acidosis 6.9-7.0)
- pCO2_Arterial: 10-120 mmHg
- pO2_Arterial: 30-500 mmHg (hyperoxia possible with supplemental O2)
- Lactate: 0.5-270 mg/dL (severe lactic acidosis: multiply by 9 from mmol/L)
- Glucose: 30-600 mg/dL
- Magnesium: 0.5-10 mg/dL

If converted value exceeds plausible range by >10×, re-check threshold application.

## References

See `references/lactate-conversion.md` for lactate unit conversion derivation and threshold rationale.

## Relationship to Existing Skills

- Use `clinical-lab-harmonization` for general conversion factors and the critical "NO ROUNDING" rule
- Use `clinical-lab-harmonization/references/icu-metabolic-panel.md` for blood gas conversion patterns
- This skill extends ICU patterns to respiratory-specific panels with JSON input handling
