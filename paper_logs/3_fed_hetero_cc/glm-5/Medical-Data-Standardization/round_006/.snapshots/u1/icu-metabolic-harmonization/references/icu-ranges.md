# ICU Metabolic Panel Ranges and Factors

## ICU-Specific Analytes

ICU patients have wider physiological ranges due to critical illness. Use these extended bounds:

| Analyte | US Normal | US Pathological | SI Normal | SI Pathological | Factor (SI->US) | Notes |
|---------|-----------|-----------------|-----------|-----------------|-----------------|-------|
| Creatinine | 0.7-1.3 mg/dL | 0.3-25 mg/dL | 60-115 umol/L | 20-2200 umol/L | 88.4 (divide) | ESRD may have >25 |
| BUN | 7-20 mg/dL | 5-150 mg/dL | 2.5-7.1 mmol/L | 1.8-35.7 mmol/L | 2.8 (multiply) | Urea nitrogen |
| Glucose | 70-100 mg/dL | 10-1000 mg/dL | 3.9-5.6 mmol/L | 1.7-55 mmol/L | 18.0 (multiply) | DKA/HHS extremes |
| Calcium | 8.5-10.5 mg/dL | 6.0-14 mg/dL | 2.1-2.6 mmol/L | 1.5-3.5 mmol/L | 4.0 (multiply) | Hypocalcemia in sepsis |
| Magnesium | 1.7-2.2 mg/dL | 1.0-4.0 mg/dL | 0.7-0.9 mmol/L | 0.4-1.6 mmol/L | 2.43 (multiply) | Renal failure |
| Phosphorus | 2.5-4.5 mg/dL | 0.5-12 mg/dL | 0.8-1.45 mmol/L | 0.2-3.9 mmol/L | 3.097 (multiply) | Tumor lysis |
| pCO2_Arterial | 35-45 mmHg | 10-120 mmHg | 4.7-6.0 kPa | 1.3-16 kPa | 7.50062 (multiply) | Permissive hypercapnia |
| Lactate | 0.5-2.0 mmol/L | 0.1-30 mmol/L | SAME | SAME | None | Severe shock states |
| Beta_Hydroxybutyrate | 0.02-0.5 mmol/L | 0.02-8.0 mmol/L | SAME | SAME | None | DKA marker |
| Osmolality | 275-295 mOsm/kg | 270-320 mOsm/kg | SAME | SAME | None | Calculated/measured |
| Anion_Gap | 8-12 mEq/L | 8-16 mEq/L | SAME | SAME | None | mEq/L = mmol/L |
| pH_Arterial | 7.35-7.45 | 6.8-7.8 | SAME | SAME | None | Severe acidosis valid |

## Detection Thresholds (SI Detection)

| Analyte | Detection Logic | Threshold |
|---------|-----------------|-----------|
| Creatinine | If >20 and in SI range | >20 umol/L-like values |
| BUN | If <5 and in SI range | <5 mmol/L-like values |
| Glucose | If <3.0 and in SI range | <3.0 mmol/L-like values |
| Calcium | If 1.5-4.0 | SI range window |
| Magnesium | If <1.0 and in SI range | <1.0 mmol/L-like values |
| Phosphorus | If <3.0 and in SI range | <3.0 mmol/L-like values |
| pCO2_Arterial | If <15 | kPa values (normal mmHg is 35-45) |

## Critical ICU Validation Rules

- **pH 6.91-6.98**: Valid severe metabolic acidosis (lactic acidosis, DKA, septic shock)
- **Lactate 10-30 mmol/L**: Valid severe lactic acidosis
- **Glucose 500-900 mg/dL**: Valid DKA/HHS
- **Creatinine 10-20 mg/dL**: Valid AKI requiring dialysis
- **pCO2 10-120 mmHg**: Valid permissive hypercapnia/hyperventilation

## Common ICU Errors

| Error | Manifestation | Fix |
|-------|---------------|-----|
| pCO2 not converted | 4.65 left as 4.65 mmHg (should be 34.9) | Apply 7.50062 if <15 |
| pCO2 over-converted | 40 mmHg x 7.5 = 300 mmHg | Check threshold: >15 is mmHg |
| Rounding | 47.40 instead of 47.400937 | NEVER round - use %.10g |
| BUN direction wrong | Dividing instead of multiplying | BUN: multiply by 2.8 |
| Rejecting low pH | Flagging pH 6.91 invalid | Accept pH 6.8-7.8 for ICU |

## Python Detection Pattern

```python
US_RANGES = {
    'Creatinine': (0.3, 25),
    'BUN': (5, 150),
    'Glucose': (30, 1000),
    'Calcium': (6.0, 14.0),
    'Magnesium': (1.0, 4.0),
    'Phosphorus': (2.0, 6.0),
    'pCO2_Arterial': (10, 120),
}

SI_RANGES = {
    'Creatinine': (20, 2200),
    'BUN': (1.8, 35.7),
    'Glucose': (1.7, 55),
    'Calcium': (1.5, 3.5),
    'Magnesium': (0.4, 1.6),
    'Phosphorus': (0.2, 3.9),
    'pCO2_Arterial': (1.3, 16),
}

FACTORS = {
    'Creatinine': (88.4, 'divide'),
    'BUN': (2.8, 'multiply'),
    'Glucose': (18.0, 'multiply'),
    'Calcium': (4.0, 'multiply'),
    'Magnesium': (2.43, 'multiply'),
    'Phosphorus': (3.097, 'multiply'),
    'pCO2_Arterial': (7.50062, 'multiply'),
}

def should_convert(col, val):
    us_lo, us_hi = US_RANGES.get(col, (0, float('inf')))
    si_lo, si_hi = SI_RANGES.get(col, (0, float('inf')))
    if us_lo <= val <= us_hi:
        return False  # Already US
    if si_lo <= val <= si_hi:
        return True   # Likely SI
    return False      # Outside both: keep as-is
```