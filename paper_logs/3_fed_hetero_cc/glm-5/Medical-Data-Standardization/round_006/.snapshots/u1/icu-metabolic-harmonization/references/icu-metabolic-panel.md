# ICU Metabolic Panel Conversion Factors

## Panel-Specific Analytes

ICU metabolic panels extend standard panels with blood gas and critical care parameters.

### Blood Gas Conversions

| Analyte | SI Unit | US Unit | Factor | Operation | Threshold | Notes |
|---------|---------|---------|--------|-----------|-----------|-------|
| pCO2_Arterial | kPa | mmHg | 7.50062 | multiply | < 15 | Normal mmHg: 35-45; normal kPa: 4.7-6.0 |
| pO2_Arterial | kPa | mmHg | 7.50062 | multiply | < 15 | Normal mmHg: 80-100 |

**Critical pCO2 detection**: Values <15 are clearly kPa. Normal mmHg values are 35-45, so any value <15 must be kPa.

### No Conversion Needed

| Analyte | Reason |
|---------|--------|
| Sodium | mmol/L = mEq/L |
| Potassium | mmol/L = mEq/L |
| Chloride | mmol/L = mEq/L |
| Bicarbonate | mmol/L = mEq/L |
| Lactate | mmol/L standard globally |
| Anion_Gap | Calculated, mEq/L |
| Osmolality | mOsm/kg standard |
| pH_Arterial | Unitless |
| Beta_Hydroxybutyrate | mmol/L standard |

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
|-------|---------------|-----|
| pCO2 not converted | 4.65 kPa left as 4.65 mmHg | Apply x7.50062 if <15 |
| pCO2 over-converted | 40 mmHg x 7.5 = 300 mmHg | Check threshold: >15 is mmHg |
| Rounding | 47.40 instead of 47.400937 | NEVER round - use %.10g |
| Glucose threshold error | Converting 24 mg/dL as mmol/L | Only convert if <3.0 |
| BUN direction wrong | Dividing instead of multiplying | BUN: multiply by 2.8 |
