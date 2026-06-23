# Bidirectional Unit Detection in Neonatal Labs

## Why Conventional Units Vary

In adult medicine, US conventional units dominate (mg/dL, mmol/L for some). In neonatal/pediatric medicine, many labs report SI units as conventional:

| Analyte | Adult US Conventional | Neonatal Conventional | Notes |
|---------|----------------------|-----------------------|-------|
| Creatinine | mg/dL | μmol/L | SI units standard in pediatrics |
| BUN | mg/dL | mmol/L | SI units standard internationally |
| Bilirubin | mg/dL | μmol/L | Critical for hyperbilirubinemia management |
| Glucose | mg/dL | mmol/L | Growing SI adoption |
| CRP | mg/L | mg/L | SI unit, but mg/dL sometimes reported |

## Threshold Derivation

### Creatinine: < 20 threshold
- US normal: 0.3-1.2 mg/dL
- SI normal: 27-106 μmol/L
- Conversion: 1 mg/dL = 88.4 μmol/L
- US values 0.3-1.5 mg/dL → SI 27-133 μmol/L
- SI values 20-200 μmol/L are typical neonatal range
- Detection: Values < 20 must be mg/dL (would give 1768+ μmol/L if misinterpreted)
- Threshold < 20 catches US mg/dL values, converts to μmol/L (SI target)

### BUN: > 15 threshold
- US normal: 7-20 mg/dL
- SI normal: 2.5-7.1 mmol/L
- Conversion: 1 mg/dL BUN = 0.357 mmol/L
- US values 15-100 mg/dL → SI 5.4-35.7 mmol/L
- SI values 2-15 mmol/L → US 5.6-42 mg/dL
- Threshold > 15 catches clear US elevations

### Glucose: > 25 threshold
- US normal: 70-100 mg/dL; neonatal hypoglycemia <40 mg/dL
- SI normal: 3.9-5.6 mmol/L; hypoglycemia <2.2 mmol/L
- Conversion: 1 mmol/L = 18 mg/dL; 1 mg/dL = 0.0555 mmol/L
- US values 40-1000 mg/dL
- SI values 2-55 mmol/L
- Threshold > 25: SI values never exceed 25 in survivable range; >25 must be mg/dL

### Bilirubin: < 50 threshold
- US normal: 0.2-1.2 mg/dL; neonatal jaundice up to 20 mg/dL
- SI normal: 3-21 μmol/L; neonatal up to 340 μmol/L
- Conversion: 1 mg/dL = 17.1 μmol/L
- US 1-20 mg/dL → SI 17-342 μmol/L
- SI values 50-500+ in hyperbilirubinemia
- Threshold < 50: catches US mg/dL (would be 3-21 after conversion); SI values start at ~20

### Lactate: > 10 threshold
- SI normal: 0.5-2.0 mmol/L
- US normal: 4.5-18 mg/dL (×9 factor)
- If input is 5.0 mmol/L, that's elevated SI, convert to 45 mg/dL — BUT neonatal TARGET is mmol/L
- If input is 45 mg/dL, that's moderate US, convert to 5.0 mmol/L
- Threshold > 10: values >10 are almost certainly mg/dL (10 mmol/L = 90 mg/dL is severe acidosis)
- Values 3-10 are ambiguous; keep as-is in this zone

### Hemoglobin: < 30 threshold
- US: 10-18 g/dL; SI: 100-180 g/L
- Clear separation: <30 must be g/dL (10-18 range), >50 must be g/L (100-180 range)
- Threshold < 30 catches g/dL input

### pCO2: > 15 threshold
- US: 35-45 mmHg; SI: 4.7-6.0 kPa
- Conversion: 1 kPa = 7.50062 mmHg; mmHg ÷ 7.5 = kPa
- SI values 3-12 kPa; US values 20-150 mmHg
- Threshold > 15: catches mmHg (15 mmHg = 2 kPa, extreme but possible)

## Common Detection Errors

| Error | Wrong Threshold | Right Threshold | Why |
|-------|-----------------|-----------------|-----|
| Creatinine use >88 | Catches SI, converts to tiny values | <20 | US values are small numbers |
| BUN use <5 | Converts normal SI to tiny mg/dL | >15 | US values are larger numbers |
| Glucose use <3 | Converts hypoglycemic US to SI | >25 | US values are much larger |
| Bilirubin use >200 | Catches SI, makes mg/dL impossibly small | <50 | US values are smaller |
| Lactate use <3 for neonatal | Converts normal mmol/L to mg/dL (wrong target) | >10 | Neonatal target IS mmol/L |
