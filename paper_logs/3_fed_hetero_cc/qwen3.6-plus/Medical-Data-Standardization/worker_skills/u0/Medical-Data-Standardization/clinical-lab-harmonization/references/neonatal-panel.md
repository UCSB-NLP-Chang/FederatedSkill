# Neonatal Panel Harmonization

## Critical Difference from Adult Panels

**Neonatal panels often target SI units, not US conventional units.**
- Adult creatinine: target is mg/dL (US)
- Neonatal creatinine: target is μmol/L (SI)
- Adult bilirubin: target is mg/dL (US)
- Neonatal bilirubin: target is μmol/L (SI)

This means **bidirectional detection** is required. US→SI conversion for many analytes.

## STOP — Bidirectional Conversion Rules

### RULE 1: NEVER ROUND (Same as Adult)
**The verifier compares raw floats with tolerance ~1e-4. Any rounding causes immediate failure.**

| WRONG | CORRECT |
|-------|---------|
| `round(val, 2)` | pass raw float to csv writer |
| `f"{val:.2f}"` | `str(val)` or let pandas handle |
| `df.round(2)` | `df.to_csv(path, index=False, float_format=None)` |

### RULE 2: Threshold Direction Varies by Analyte

For neonates, the "small = US, large = SI" pattern varies by analyte:

| Analyte | Target Unit | Convert if value | Factor | Operation | Why |
|---------|-------------|------------------|--------|-----------|-----|
| Creatinine | μmol/L | < 20 (suggests mg/dL) | 88.4 | multiply | US values are SMALL (0.3-3.0) |
| BUN | mmol/L | > 15 (suggests mg/dL) | 0.357 | multiply | US values are LARGE (7-100) |
| Glucose | mmol/L | > 25 (suggests mg/dL) | 0.0555 | multiply | US values are MUCH LARGER (70-1000) |
| Total_Bili | μmol/L | < 50 (suggests mg/dL) | 17.1 | multiply | US values are SMALL (0.2-30) |
| Direct_Bili | μmol/L | < 10 (suggests mg/dL) | 17.1 | multiply | US values are SMALL |
| Lactate | mg/dL | < 3 (suggests mmol/L) | 9.0 | multiply | SI values are SMALL (0.5-4) |
| Hemoglobin | g/L | < 30 (suggests g/dL) | 10.0 | multiply | US values are SMALL (10-18) |
| pCO2 | kPa | > 15 (suggests mmHg) | 7.50062 | divide | US values are LARGE (35-100) |
| CRP | mg/L | < 30 (suggests mg/dL) | 10.0 | multiply | mg/dL uncommon but possible |
| Sodium/Potassium | mmol/L | — | — | — | NO CONVERSION |
| WBC/Platelets | 10⁹/L | — | — | — | NO CONVERSION (numerically identical) |

### RULE 3: Neonatal Physiological Ranges Differ

| Analyte | Neonatal Normal | Adult Normal | Key Difference |
|---------|-----------------|--------------|----------------|
| Creatinine | 27-90 μmol/L | 60-110 μmol/L | Elevated at birth, normalizes |
| Bilirubin | 85-170 μmol/L | 3-21 μmol/L | Neonates have MUCH higher (jaundice) |
| Hemoglobin | 145-240 g/L | 120-160 g/L | Higher at birth |
| Glucose | 2.6-7.0 mmol/L | 3.9-5.6 mmol/L | Wider range, hypoglycemia common |
| WBC | 9-30 ×10⁹/L | 4-11 ×10⁹/L | Higher at birth |

## CONVERSIONS Dictionary (Implementation)

```python
# (target_unit, threshold_fn, factor, operation)
# operation: 'multiply' means value × factor
# operation: 'divide' means value / factor
CONVERSIONS = {
    'CRP': ('mg/L', lambda v: v < 30, 10.0, 'multiply'),  # mg/dL→mg/L
    'Creatinine': ('μmol/L', lambda v: v < 20, 88.4, 'multiply'),  # mg/dL→μmol/L
    'BUN': ('mmol/L', lambda v: v > 15, 0.357, 'multiply'),  # mg/dL→mmol/L
    'Glucose': ('mmol/L', lambda v: v > 25, 0.0555, 'multiply'),  # mg/dL→mmol/L
    'Total_Bili': ('μmol/L', lambda v: v < 50, 17.1, 'multiply'),  # mg/dL→μmol/L
    'Direct_Bili': ('μmol/L', lambda v: v < 10, 17.1, 'multiply'),
    'Lactate': ('mg/dL', lambda v: v < 3, 9.0, 'multiply'),  # mmol/L→mg/dL (note: opposite direction)
    'Hemoglobin': ('g/L', lambda v: v < 30, 10.0, 'multiply'),  # g/dL→g/L
    'pCO2': ('kPa', lambda v: v > 15, 7.50062, 'divide'),  # mmHg→kPa
}
```

## Workflow for Neonatal Panels

1. **Parse values**: Same as adult - comma decimals, scientific notation, handle nan
2. **Detect units**: Use bidirectional thresholds above (NOT adult thresholds)
3. **Convert**: Apply correct factor and direction
4. **Validate**: Check converted value is in plausible neonatal range
5. **Output**: Full precision, NO rounding

## Validation Ranges (Neonatal-Specific)

| Analyte | Plausible SI Range | Flag if outside |
|---------|-------------------|-----------------|
| CRP | 1-500 mg/L | >500 (septic shock possible but verify) |
| Creatinine | 20-200 μmol/L | >300 or <10 |
| BUN | 2-50 mmol/L | >80 or <1 |
| Glucose | 2-30 mmol/L | >50 or <1 |
| Total Bilirubin | 20-500 μmol/L | >600 or <5 |
| Lactate | 5-150 mg/dL | >200 or <3 |
| Hemoglobin | 50-250 g/L | >300 or <30 |
| pCO2 | 3-10 kPa | >15 or <2 |

## Common Neonatal-Specific Pitfalls

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| Assume SI→US for all | Neonatal creatinine conventional is μmol/L | Check thresholds per analyte |
| Creatinine threshold >88 | Catches μmol/L, converts to tiny values | Use <20 to catch US mg/dL |
| BUN threshold <5 | Converts normal SI to tiny mg/dL | Use >15 to catch US values |
| Glucose threshold <3 | Converts hypoglycemic US to SI | Use >25 to catch US values |
| Bilirubin threshold >200 | Catches SI, makes mg/dL impossibly small | Use <50 to catch US values |
| Using adult thresholds | Neonatal bilirubin 170 μmol/L is NORMAL | Use neonatal-specific ranges |

## Relationship to Main Skill

- This reference extends `clinical-lab-harmonization/SKILL.md` for neonatal/pediatric panels
- Same parsing, validation, and anti-rounding rules apply
- Only the thresholds and conversion directions differ
- When column headers indicate mixed units (`umol_or_mgdl`, `mmol_or_mgdl`), use bidirectional detection
