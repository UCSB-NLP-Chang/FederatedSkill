# Hepatic Panel Unit Conversions

Extended conversion reference for liver function and related analytes.

## Conversion Factors

| Analyte | SI Unit | US Unit | Conversion | Detection Rule |
|---------|---------|---------|------------|----------------|
| Total_Bilirubin | μmol/L | mg/dL | SI ÷ 17.1 = US | > 20 → assume SI |
| Direct_Bilirubin | μmol/L | mg/dL | SI ÷ 17.1 = US | > 10 → assume SI |
| Albumin | g/L | g/dL | SI ÷ 10 = US | > 10 → assume SI |
| Total_Protein | g/L | g/dL | SI ÷ 10 = US | > 20 → assume SI |
| Ammonia | μmol/L | μg/dL | SI × 1.703 = US | > 50 → assume SI |
| Creatinine | μmol/L | mg/dL | SI ÷ 88.42 = US | > 20 → assume SI |
| Hemoglobin | mmol/L | g/dL | SI ÷ 1.613 = US (or × 0.6206) | > 3 → assume SI |
| Ferritin | pmol/L | μg/L | SI ÷ 2.247 = US | > 500 → assume SI |
| Glucose | mmol/L | mg/dL | SI × 18 = US | < 20 → assume SI |

## Critical Corrections from Failed Run

**Ferritin**: The agent incorrectly multiplied instead of divided. Correct: pmol/L ÷ 2.247 = μg/L.

**Ammonia**: The agent used incorrect factor. Correct: μmol/L × 1.703 = μg/dL.

**Hemoglobin**: mmol/L (SI) to g/dL (US), not the reverse. Divide by 1.613.

## Liver Disease Context Adjustments

In hepatic panels, values are often pathological - do NOT use "normal range" for detection:

| Analyte | Typical SI (normal) | Pathological SI seen | US equivalent |
|---------|---------------------|----------------------|---------------|
| Total_Bilirubin | 5-21 μmol/L | 200-400 μmol/L | 1.2-23 mg/dL |
| Ammonia | 11-32 μmol/L | 100-300 μmol/L | 19-500 μg/dL |
| Albumin | 35-50 g/L | 15-30 g/L (liver disease) | 3.5-5.0 g/dL |

**Key insight**: Detection thresholds must use absolute cutoffs (e.g., > 20 for bilirubin), not "is this in normal range?"

## Verification Ranges

After conversion, check values are physiologically plausible:

| Analyte | Implausible US Low | Implausible US High |
|---------|-------------------|---------------------|
| Total_Bilirubin | < 0.1 mg/dL | > 40 mg/dL (severe failure) |
| Direct_Bilirubin | < 0 | > 20 mg/dL |
| Albumin | < 1.0 g/dL | > 6.0 g/dL |
| Total_Protein | < 3.0 g/dL | > 10.0 g/dL |
| Ammonia | < 10 μg/dL | > 1000 μg/dL |
| Creatinine | < 0.3 mg/dL | > 20 mg/dL |
| Hemoglobin | < 3 g/dL | > 20 g/dL |
| Ferritin | < 5 μg/L | > 5000 μg/L (hemochromatosis) |
| Glucose | < 20 mg/dL | > 1000 mg/dL |

If converted values exceed these, re-check conversion direction.