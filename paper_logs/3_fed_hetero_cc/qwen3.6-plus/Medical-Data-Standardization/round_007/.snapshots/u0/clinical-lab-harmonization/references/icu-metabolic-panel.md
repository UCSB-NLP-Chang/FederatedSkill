# ICU Metabolic Panel Conversion Factors

## Panel-Specific Analytes

ICU metabolic panels extend standard electrolyte/metabolic panels with blood gas and critical care parameters.

### Standard Conversions (from electrolyte-metabolic-panel)

| Analyte | SI Unit | US Unit | Factor | Operation | Threshold | Notes |
|---------|---------|---------|--------|-----------|-----------|-------|
| Glucose | mmol/L | mg/dL | 18.0 | multiply | < 3.0 | CRITICAL: only <3.0 threshold |
| Creatinine | μmol/L | mg/dL | 88.4 | divide | > 20 | Standard renal conversion |
| Calcium | mmol/L | mg/dL | 4.0 | multiply | 1.5–4.0 | Mid-range detection |
| Magnesium | mmol/L | mg/dL | 2.43 | multiply | < 1.0 | SI values are SMALL |
| Phosphorus | mmol/L | mg/dL | 3.097 | multiply | < 3.0 | SI values are SMALL |
| BUN/Urea | mmol/L | mg/dL | 2.8 | multiply | < 5.0 | Urea nitrogen conversion |

### Blood Gas Conversions

| Analyte | SI Unit | US Unit | Factor | Operation | Threshold | Notes |
|---------|---------|---------|--------|-----------|-----------|-------|
| pCO2_Arterial | kPa | mmHg | 7.5006 | multiply | < 15 | Normal mmHg: 35-45; normal kPa: 4.7-6.0 |
| pO2_Arterial | kPa | mmHg | 7.5006 | multiply | < 15 | Normal mmHg: 80-100 |

**Critical pCO2 detection**: Values < 15 are clearly kPa (would give < 112.5 mmHg after conversion). Normal mmHg values are 35-45, so any value < 15 must be kPa. Values in range 15-20 could be either very low mmHg (rare but possible in ICU) or moderately high kPa — use <15 as the safer threshold.

### No Conversion Needed

| Analyte | Reason |
|---------|--------|
| Sodium | mmol/L = mEq/L |
| Potassium | mmol/L = mEq/L |
| Chloride | mmol/L = mEq/L |
| Bicarbonate | mmol/L = mEq/L |
| Lactate | mmol/L standard in both SI and US |
| Beta_Hydroxybutyrate | mmol/L standard in both SI and US |
| Anion_Gap | Calculated, mEq/L |
| Osmolality | mOsm/kg standard |
| pH_Arterial | Unitless |

## Physiological Reference Ranges (US Conventional)

| Analyte | Normal Range | Critical Low | Critical High |
|---------|-------------|--------------|---------------|
| pCO2_Arterial | 35-45 mmHg | < 20 | > 60 |
| pO2_Arterial | 80-100 mmHg | < 60 | > 300 (hyperoxia) |
| Glucose | 70-100 mg/dL | < 40 | > 400 |
| BUN | 7-20 mg/dL | — | > 100 |
| Creatinine | 0.7-1.3 mg/dL | — | > 10 |
| Calcium | 8.5-10.5 mg/dL | < 7.0 | > 13 |
| Magnesium | 1.5-2.5 mg/dL | < 1.0 | > 4.0 |
| Phosphorus | 2.5-4.5 mg/dL | < 1.0 | > 8.0 |

## Common ICU Panel Errors

| Error | Manifestation | Fix |
|-------|--------------|-----|
| pCO2 not converted | 4.65 kPa left as 4.65 mmHg (should be 34.9) | Apply ×7.5006 if < 15 |
| pCO2 over-converted | 40 mmHg × 7.5 = 300 mmHg | Check threshold: > 15 is already mmHg |
| Rounding to 2 decimals | 47.40 instead of 47.400937 | **NEVER ROUND** - full precision |
| Glucose threshold error | Converting 24 mg/dL as mmol/L | Only convert if < 3.0 |
| Converting Lactate | Applying mmol/L → mg/dL conversion | Lactate is mmol/L globally |
| Converting Beta_Hydroxybutyrate | Applying conversion | mmol/L is global standard |
| Missing multi-file join | Processing files separately | Join on record_id first |

## Implementation Pattern

```python
# ICU metabolic panel conversion factors
# (factor, operation, threshold, threshold_direction)
ICU_CONVERSIONS = {
    'Glucose': (18.0, 'multiply', 3.0, '<'),
    'Creatinine': (88.4, 'divide', 20, '>'),
    'Calcium': (4.0, 'multiply', (1.5, 4.0), 'range'),
    'Magnesium': (2.43, 'multiply', 1.0, '<'),
    'Phosphorus': (3.097, 'multiply', 3.0, '<'),
    'BUN': (2.8, 'multiply', 5.0, '<'),
    'pCO2_Arterial': (7.5006, 'multiply', 15, '<'),
    'pO2_Arterial': (7.5006, 'multiply', 15, '<'),
}

ICU_NO_CONVERSION = {'Lactate', 'Beta_Hydroxybutyrate', 'pH_Arterial',
                     'Osmolality', 'Anion_Gap', 'Sodium', 'Potassium',
                     'Chloride', 'Bicarbonate'}

def convert_icu_value(col_name, value):
    """Apply ICU metabolic panel conversions."""
    if col_name in ICU_NO_CONVERSION:
        return value
    if col_name not in ICU_CONVERSIONS:
        return value

    factor, operation, threshold, direction = ICU_CONVERSIONS[col_name]

    # Check if conversion needed
    if direction == '<':
        should_convert = value < threshold
    elif direction == '>':
        should_convert = value > threshold
    elif direction == 'range':
        lo, hi = threshold
        should_convert = lo <= value <= hi
    else:
        should_convert = False

    if not should_convert:
        return value

    if operation == 'multiply':
        return value * factor
    else:
        return value / factor
```