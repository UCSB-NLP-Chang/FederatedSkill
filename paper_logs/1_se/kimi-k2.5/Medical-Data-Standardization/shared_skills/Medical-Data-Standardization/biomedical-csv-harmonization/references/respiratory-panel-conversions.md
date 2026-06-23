# Respiratory Panel Unit Conversions

Extended reference for blood gas and respiratory panel harmonization from JSON sources.

## Critical Blood Gas Unit Trap

**pCO2 and pO2 have TWO common unit systems that are easily confused:**

| Unit | Normal Range | Context |
|------|-------------|---------|
| **mmHg** | pCO2: 35-45, pO2: 75-100 | US conventional, most common |
| **kPa** | pCO2: 4.7-6.0, pO2: 10-13.3 | European, international |

**Conversion**: 1 kPa = 7.50062 mmHg (multiply kPa → mmHg)

## Detection Heuristics (CRITICAL)

| Analyte | Assume kPa (convert) if | Assume mmHg (keep) if |
|---------|------------------------|----------------------|
| pCO2 | < 20 | 20–150 |
| pO2 | < 30 | 30–600 |
| pH | Always unitless | Always 6.8–7.8 |

**Key insight**: pCO2 of 10 is either 10 kPa (→ 75 mmHg, normal) or 10 mmHg (critically low, incompatible with life). Values < 20 are almost certainly kPa.

## Common JSON Patterns

```json
{
  "sample_id": "1",
  "status": "final",  // CRITICAL: Filter to "final" only
  "measurements": {
    "acid_base": {
      "pH_Arterial": "7,5412",      // European decimal comma
      "pCO2_Arterial": "10.1975",   // Likely kPa (needs ×7.5)
      "pO2_Arterial": "4.6536e+01"  // Scientific notation + maybe kPa
    },
    "metabolic": {
      "Lactate": "13,0262",         // European decimal
      "Glucose": "19.08674",        // Likely mmol/L (needs ×18)
      "Magnesium": "0.5813"         // Likely mmol/L (needs ×2.43)
    }
  }
}
```

## Conversion Summary

| Analyte | Source Unit | Target Unit | Factor | Detection |
|---------|-------------|-------------|--------|-----------|
| pCO2 | kPa | mmHg | × 7.50062 | < 20 |
| pO2 | kPa | mmHg | × 7.50062 | < 30 |
| Glucose | mmol/L | mg/dL | × 18.018 | < 30 |
| Magnesium | mmol/L | mg/dL | × 2.431 | < 2 |
| Lactate | mmol/L | mg/dL | × 9.008 | < 5 |
| Bicarbonate | mmol/L | mEq/L | 1:1 | — |
| pH | unitless | unitless | — | — |

## Verification Ranges (US Conventional)

After conversion, values MUST be in these ranges or conversion is wrong:

| Analyte | Implausible Low | Implausible High | Notes |
|---------|-----------------|------------------|-------|
| pH | < 6.8 | > 7.8 | Fatal acidosis/alkalosis |
| pCO2 | < 10 mmHg | > 150 mmHg | Ventilation extremes |
| pO2 | < 20 mmHg | > 600 mmHg | Hyperbaric exceeds 600 |
| Glucose | < 20 mg/dL | > 1000 mg/dL | Fatal hypoglycemia |
| Magnesium | < 1.0 mg/dL | > 5.0 mg/dL | Critical depletion |
| Lactate | < 0.3 mg/dL | > 200 mg/dL | Severe shock |

## Critical Errors from Failed Runs

### Error 1: Wrong pO2 conversion direction
```python
# WRONG: Converting mmHg to kPa instead of kPa to mmHg
pO2_mmHg = pO2_val * 7.5 if pO2_val > 100 else pO2_val  # 176 → 1320 mmHg (impossible!)

# CORRECT: Detect kPa by low value, convert to mmHg
pO2_mmHg = pO2_val * 7.5 if pO2_val < 30 else pO2_val   # 46.5 kPa → 349 mmHg
```

### Error 2: Inconsistent handling of paired gases
If pCO2 is < 20 (kPa), pO2 from same sample is likely also kPa, even if pO2 > 30.

### Error 3: European decimals in scientific notation
`"2.3955e+01"` → parse as 23.955 (already US format)
`"2,3955e+01"` → replace comma first → 2.3955e+01 → 23.955

### Error 4: Dropping records with "nan" string
Input may contain literal `"nan"` or `""` — treat as missing, drop row.

## JSON-Specific Workflow

```python
import json

def load_respiratory_json(path):
    with open(path) as f:
        data = json.load(f)
    
    records = []
    for panel in data['panels']:
        if panel['status'] != 'final':  # CRITICAL: Skip drafts
            continue
            
        flat = {'sample_id': panel['sample_id']}
        
        # Flatten nested measurements
        for category in panel['measurements'].values():
            flat.update(category)
        
        records.append(flat)
    
    return records

def parse_value(val):
    """Handle European decimals, scientific notation, empty."""
    if val in ('', 'nan', 'NaN', None):
        return None
    # Replace comma decimal, then parse
    cleaned = str(val).replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return None

def convert_blood_gas(val, analyte):
    """Convert with plausibility check."""
    if val is None:
        return None
        
    if analyte in ('pCO2', 'pO2'):
        # kPa detection: values < threshold
        kPa_threshold = 20 if analyte == 'pCO2' else 30
        if val < kPa_threshold:
            converted = val * 7.50062
            # Verify: converted should be 20-600 mmHg
            if 20 <= converted <= 600:
                return converted
        # Check if already plausible mmHg
        if (analyte == 'pCO2' and 10 <= val <= 150) or \
           (analyyte == 'pO2' and 20 <= val <= 600):
            return val
    
    # ... other analytes
    
    return val  # Unknown or pathological
```

## Record Filtering Rules

1. **Status filter**: Keep only `"status": "final"` records
2. **Complete data**: Drop rows with ANY missing measurement
3. **Plausibility check**: After conversion, verify all values in physiologic ranges

## Output Requirements

- Exactly 2 decimal places: `f"{val:.2f}"`
- No scientific notation
- No join keys (sample_id removed)
- Header order must match specification
