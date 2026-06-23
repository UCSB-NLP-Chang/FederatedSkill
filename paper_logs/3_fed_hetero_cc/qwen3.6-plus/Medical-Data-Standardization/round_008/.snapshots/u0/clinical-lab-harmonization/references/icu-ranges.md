# ICU Metabolic Panel Ranges and Factors

## ICU-Specific Analytes

ICU metabolic panels extend standard electrolyte/metabolic panels with blood gas and critical care parameters. ICU patients have wider physiological ranges due to critical illness.

### Standard Conversions (shared with electrolyte-metabolic-panel)

| Analyte | SI Unit | US Unit | Factor | Operation | Detection Threshold | Notes |
|---------|---------|---------|--------|-----------|---------------------|-------|
| Glucose | mmol/L | mg/dL | 18.0 | multiply | < 3.0 | CRITICAL: only <3.0 threshold |
| Creatinine | μmol/L | mg/dL | 88.4 | divide | > 20 | Standard renal conversion |
| Calcium | mmol/L | mg/dL | 4.0 | multiply | 1.5–4.0 | Mid-range detection |
| Magnesium | mmol/L | mg/dL | 2.43 | multiply | < 1.0 | SI values are SMALL |
| Phosphorus | mmol/L | mg/dL | 3.097 | multiply | < 3.0 | SI values are SMALL |
| BUN/Urea | mmol/L | mg/dL | 2.8 | multiply | < 5.0 | Urea nitrogen conversion |

### ICU-Specific Conversions

| Analyte | SI Unit | US Unit | Factor | Operation | Detection Threshold | Notes |
|---------|---------|---------|--------|-----------|---------------------|-------|
| pCO2_Arterial | kPa | mmHg | 7.5006 | multiply | < 15 | Normal mmHg: 35-45; normal kPa: 4.7-6.0 |

### No Conversion Needed (global mmol/L standard or unitless)

| Analyte | Reason |
|---------|--------|
| Lactate | mmol/L is global standard in both SI and US |
| Beta_Hydroxybutyrate | mmol/L is global standard (DKA marker) |
| pH_Arterial | Unitless log scale; no conversion applicable |
| Osmolality | mOsm/kg standard globally |
| Anion_Gap | mEq/L = mmol/L for monovalent ions |
| Sodium | mmol/L = mEq/L |
| Potassium | mmol/L = mEq/L |
| Chloride | mmol/L = mEq/L |
| Bicarbonate | mmol/L = mEq/L |

## ICU Physiological Ranges (Extended)

ICU patients have wider physiological ranges than standard populations. Use these extended bounds for validation:

| Analyte | Normal Range | ICU Extended Range | Notes |
|---------|-------------|-------------------|-------|
| pH_Arterial | 7.35-7.45 | **6.8-7.8** | Severe acidosis (6.8-7.0) common in ICU. Do NOT flag as invalid. |
| Lactate | 0.5-2.0 mmol/L | 0.1-30 mmol/L | Severe lactic acidosis can reach 10-30 mmol/L. |
| Glucose | 70-100 mg/dL | 10-1000 mg/dL | Stress hyperglycemia (>300) and hypoglycemia (<50) both common. |
| pCO2_Arterial | 35-45 mmHg | 10-120 mmHg | Permissive hypercapnia in ARDS; hyperventilation in metabolic acidosis. |
| Creatinine | 0.7-1.3 mg/dL | 0.3-25 mg/dL | Acute kidney injury common. |
| BUN | 7-20 mg/dL | 5-150 mg/dL | Renal failure and catabolism. |
| Sodium | 135-145 mEq/L | 110-180 mEq/L | Severe hypo/hypernatremia in ICU. |
| Potassium | 3.5-5.0 mEq/L | 2.0-8.0 mEq/L | Life-threatening dyskalemia. |
| Magnesium | 1.5-2.5 mg/dL | 0.5-10 mg/dL | Both deficiency and toxicity. |
| Phosphorus | 2.5-4.5 mg/dL | 0.5-12 mg/dL | Tumor lysis, refeeding syndrome. |
| Calcium | 8.5-10.5 mg/dL | 6.0-14.0 mg/dL | Hypocalcemia common in sepsis. |

## Detailed Physiological Bounds

| Analyte | US Normal | US Pathological | SI Normal | SI Pathological | Factor (SI→US) | Notes |
|---------|-----------|-----------------|-----------|-----------------|----------------|-------|
| Creatinine | 0.7-1.3 mg/dL | 1.3-25 mg/dL | 60-115 μmol/L | 115-2200 μmol/L | ÷ 88.4 | Values >25 mg/dL rare but possible in ESRD |
| BUN | 7-20 mg/dL | 20-100 mg/dL | 2.5-7.1 mmol/L | 7.1-35.7 mmol/L | × 2.8 | Urea nitrogen; overlaps with SI at high values |
| Glucose | 70-100 mg/dL | 30-600 mg/dL | 3.9-5.6 mmol/L | 1.7-33.3 mmol/L | × 18.0 | ICU: 10-1000 covers DKA to hypoglycemia |
| Calcium | 8.5-10.5 mg/dL | 6.0-14 mg/dL | 2.1-2.6 mmol/L | 1.5-3.5 mmol/L | × 4.0 | Ionized or total; factor assumes total |
| Magnesium | 1.7-2.2 mg/dL | 1.0-4.0 mg/dL | 0.7-0.9 mmol/L | 0.4-1.6 mmol/L | × 2.43 | Hypermagnesemia common in renal failure |
| Phosphorus | 2.5-4.5 mg/dL | 2.0-6.0 mg/dL | 0.8-1.45 mmol/L | 0.6-1.9 mmol/L | × 3.097 | Tumor lysis or renal failure elevates |
| pCO2 | 35-45 mmHg | 20-80 mmHg | 4.7-6.0 kPa | 2.7-10.7 kPa | × 7.5006 | Arterial blood gas; kPa to mmHg |
| Lactate | 0.5-2.0 mmol/L | 0.5-20 mmol/L | Same | Same | None | Already in mmol/L globally |
| Beta_Hydroxybutyrate | 0.02-0.5 mmol/L | 0.02-8.0 mmol/L | Same | Same | None | DKA marker; mmol/L standard |
| Osmolality | 275-295 mOsm/kg | 270-320 mOsm/kg | Same | Same | None | Calculated or measured |
| Anion_Gap | 8-12 mEq/L | 8-16 mEq/L | Same | Same | None | mEq/L = mmol/L for monovalent |
| pH_Arterial | 7.35-7.45 | 7.20-7.60 | Same | Same | None | Log scale; no conversion |

## Conversion Validation Rules

1. **US First**: If value falls within US pathological range, assume US units. Do not convert.
2. **SI Second**: If outside US range but inside SI range, convert.
3. **Fallback**: If outside both, keep original. Flag for manual review if extreme.
4. **Post-Conversion Check**: Converted value must fall within US pathological range. If >10x upper bound, revert.

## Common ICU Panel Errors

| Error | Manifestation | Fix |
|-------|--------------|-----|
| Rejecting low pH | Flagging pH 6.91 as invalid | Accept pH 6.8-7.8 for ICU patients |
| Converting Lactate | Applying SI→US conversion | Lactate uses same units (mmol/L) |
| Converting Beta_Hydroxybutyrate | Applying SI→US conversion | mmol/L is global standard |
| Wrong BUN direction | Dividing instead of multiplying | BUN: ×2.8 (mmol/L → mg/dL) |
| pCO2 unit confusion | Treating mmHg as kPa | Values 20-80 are mmHg; <15 may be kPa |
| pCO2 threshold too wide | Using <20 threshold | Use <15 threshold; 15-20 could be either unit |
| Rounding ICU values | `.round(2)` on output | NEVER round - full precision required |
| Missing multi-file join | Processing one file independently | ICU data often split across files; join on record_id first |

## Python Implementation Pattern

```python
ICU_CONVERSIONS = {
    'Glucose': (18.0, 'multiply', 3.0, '<'),
    'Creatinine': (88.4, 'divide', 20, '>'),
    'Calcium': (4.0, 'multiply', None, 'range'),  # 1.5-4.0
    'Magnesium': (2.43, 'multiply', 1.0, '<'),
    'Phosphorus': (3.097, 'multiply', 3.0, '<'),
    'BUN': (2.8, 'multiply', 5.0, '<'),
    'pCO2_Arterial': (7.5006, 'multiply', 15, '<'),
}

ICU_NO_CONVERSION = {'Lactate', 'Beta_Hydroxybutyrate', 'pH_Arterial',
                     'Osmolality', 'Anion_Gap', 'Sodium', 'Potassium'}

ICU_EXTENDED_RANGES = {
    'pH_Arterial': (6.8, 7.8),
    'Lactate': (0.1, 30),
    'pCO2_Arterial': (10, 120),
    'Glucose': (10, 1000),
    'BUN': (5, 150),
}

def convert_icu_value(col_name, value):
    """Apply ICU panel conversions."""
    if col_name in ICU_NO_CONVERSION:
        return value
    if col_name not in ICU_CONVERSIONS:
        return value

    factor, operation, threshold, direction = ICU_CONVERSIONS[col_name]

    if direction == '<':
        should_convert = value < threshold
    elif direction == '>':
        should_convert = value > threshold
    elif direction == 'range':
        should_convert = 1.5 <= value <= 4.0  # Calcium specific
    else:
        should_convert = False

    if not should_convert:
        return value

    if operation == 'multiply':
        return value * factor
    else:
        return value / factor
```