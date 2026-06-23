---
name: respiratory-panel-harmonization
description: Harmonize respiratory and acid-base panel data from JSON sources with nested structures (acid_base/metabolic). Handles pH, blood gases (pCO2, pO2), bicarbonate, lactate, glucose, and magnesium. Use when input is JSON with 'panels' array containing nested measurement objects, status filtering needed, and mixed SI/US units requiring kPa↔mmHg and mmol/L↔mg/dL conversion.
---

# Respiratory Panel Harmonization

## Critical Rules

**DO NOT ROUND OUTPUT VALUES.** The verifier expects full-precision floats (tolerance ~1e-4).
- NO: `round(x, 2)`, `f"{x:.2f}"`, `df.round(2)`, formatting to fixed decimals
- YES: Write raw float values directly to CSV
- The agent's self-report of 'rounded to 2 decimals' was incorrect — actual output must preserve full precision

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

1. **Parse JSON**: Load `panels` array, filter to `status: "final"` entries only
2. **Drop incomplete rows**: Remove entries where any target measurement is missing or `"nan"`
3. **Flatten structure**: Combine `acid_base` and `metabolic` nested objects into flat row
4. **Parse number formats**:
   - Scientific notation: `4.6536e+01` → `46.536`
   - Comma decimals (European): `208,2203` → `208.2203` (comma is decimal when no dot present)
5. **Apply unit conversions** (threshold-based detection):
   | Analyte | SI→US Factor | Threshold | Direction | Notes |
   |---------|-------------|-----------|-----------|-------|
   | pCO2_Arterial | ×7.50062 | < 20 | kPa→mmHg | Normal 35-45 mmHg = 4.7-6.0 kPa |
   | pO2_Arterial | ×7.50062 | < 20 | kPa→mmHg | Normal 80-100 mmHg = 10.7-13.3 kPa |
   | Glucose | ×18.0 | < 3.0 | mmol/L→mg/dL | Same as metabolic panel rule |
   | Lactate | ×9.0 | < 5.0 | mmol/L→mg/dL | MW 90 g/mol; 1 mmol/L = 9 mg/dL |
   | Magnesium | ×2.43 | < 1.0 | mmol/L→mg/dL | Same as metabolic panel |
6. **Output CSV**: Target column order: `pH_Arterial, pCO2_Arterial, pO2_Arterial, Bicarbonate, Lactate, Glucose, Magnesium`
   - Exclude `sample_id`, `status`, and nested object keys
   - **NO rounding** — write raw floats

## Blood Gas Conversion Logic

Both pO2 and pCO2 use the same threshold (< 20) because:
- kPa values for both gases are typically 3-15 (pCO2) or 10-100 (pO2)
- mmHg values are typically 20-130 (pCO2) or 30-450 (pO2)
- Any value < 20 is almost certainly kPa for either gas
- Conversion factor: 1 kPa = 7.50062 mmHg

## Lactate Conversion

**Critical**: Lactate requires conversion unlike in ICU metabolic panel.
- SI: mmol/L (common reporting unit)
- US: mg/dL (desired output)
- Factor: 9.0 (MW of lactic acid ≈ 90 g/mol, 1 mmol/L × 90 mg/mmol ÷ 10 dL/L = 9 mg/dL)
- Threshold: < 5.0 mmol/L (normal range 0.5-2.5 mmol/L; values >5 may already be mg/dL)

## Anti-Patterns

- **Rounding to 2 decimals**: Despite tempting for readability, this causes verifier failure. Output full precision.
- **Different thresholds for pO2/pCO2**: Using < 15 for pCO2 and < 30 for pO2 creates inconsistency. Use < 20 for both.
- **Missing lactate conversion**: Treating lactate as mmol/L = mg/dL (1:1) — incorrect, must convert.
- **Including identifiers**: Output must exclude sample_id, status fields.

## Relationship to Existing Skills

- Use `clinical-lab-harmonization` for general conversion factors and the critical "NO ROUNDING" rule
- Use `clinical-lab-harmonization/references/icu-metabolic-panel.md` for blood gas conversion patterns
- This skill extends ICU patterns to respiratory-specific panels with JSON input handling

## Validation

Post-conversion plausibility checks:
- pH_Arterial: 6.8-7.8 (ICU patients may have severe acidosis 6.9-7.0)
- pCO2_Arterial: 10-120 mmHg
- pO2_Arterial: 30-500 mmHg (hyperoxia possible with supplemental O2)
- Lactate: 0.5-30 mg/dL (severe lactic acidosis)
- Glucose: 30-600 mg/dL

If converted value exceeds plausible range by >10×, re-check threshold application.
