# Unit Conversion Reference for Common Lab Values

## Quick Reference

| Analyte | SI Unit | US Conventional | Conversion Factor | Detection Threshold |
|---------|---------|-----------------|-------------------|---------------------|
| Calcium | mmol/L | mg/dL | SI × 4 = US | < 5 → assume SI |
| Glucose | mmol/L | mg/dL | SI × 18 = US | < 20 → assume SI |
| Creatinine | μmol/L | mg/dL | SI ÷ 88.42 = US | > 20 → assume SI |
| Sodium | mmol/L | mEq/L | 1:1 (no conversion) | — |
| Potassium | mmol/L | mEq/L | 1:1 (no conversion) | — |
| Chloride | mmol/L | mEq/L | 1:1 (no conversion) | — |
| Bicarbonate | mmol/L | mEq/L | 1:1 (no conversion) | — |
| Magnesium | mmol/L | mg/dL | SI × 2.43 = US | < 1.5 → assume SI |

## Detailed Rationale

### Calcium (Ca²⁺)
- **SI reference**: 2.1–2.6 mmol/L
- **US reference**: 8.4–10.4 mg/dL
- **Molecular weight**: 40.08 g/mol
- **Formula**: mmol/L × 4 = mg/dL (exact: × 4.008)

### Glucose
- **SI reference**: 3.9–6.1 mmol/L (fasting)
- **US reference**: 70–110 mg/dL
- **Molecular weight**: 180.16 g/mol
- **Formula**: mmol/L × 18 = mg/dL (exact: × 18.016)

### Creatinine
- **SI reference**: 44–106 μmol/L (women), 62–106 μmol/L (men)
- **US reference**: 0.5–1.2 mg/dL
- **Molecular weight**: 113.12 g/mol
- **Formula**: μmol/L ÷ 88.42 = mg/dL

### Magnesium
- **SI reference**: 0.75–0.95 mmol/L
- **US reference**: 1.8–2.3 mg/dL
- **Molecular weight**: 24.305 g/mol
- **Formula**: mmol/L × 2.43 = mg/dL

## Detection Strategy

When source unit is unknown, use range-based detection:

```python
def detect_and_convert_calcium(val):
    # Normal SI range: 2.1-2.6, Normal US: 8.4-10.4
    # If value < 5, almost certainly SI mmol/L
    if val < 5:
        return val * 4  # Convert to mg/dL
    return val  # Already US conventional

def detect_and_convert_glucose(val):
    # Normal SI: 3.9-6.1, Normal US: 70-110
    # If value < 20, almost certainly SI mmol/L
    if val < 20:
        return val * 18
    return val

def detect_and_convert_creatinine(val):
    # Normal SI: 44-106 μmol/L, Normal US: 0.5-1.2 mg/dL
    # If value > 20, almost certainly SI μmol/L
    if val > 20:
        return val / 88.42
    return val
```

## Edge Cases

- **Hypercalcemia in SI**: 3.5 mmol/L = 14 mg/dL — still < 20, detection works
- **Hypoglycemia in SI**: 2.5 mmol/L = 45 mg/dL — < 20, detection works
- **Renal failure creatinine**: 1000 μmol/L = 11.3 mg/dL — > 20, detection works
- **Critical glucose**: 0.5 mmol/L = 9 mg/dL — rare but < 20, detection works

## Validation

After conversion, verify values fall in physiologically plausible ranges:
- Calcium: 5–15 mg/dL (critical < 6 or > 13.5)
- Glucose: 20–600 mg/dL (critical < 40 or > 400)
- Creatinine: 0.3–15 mg/dL (dialysis patients may exceed)
