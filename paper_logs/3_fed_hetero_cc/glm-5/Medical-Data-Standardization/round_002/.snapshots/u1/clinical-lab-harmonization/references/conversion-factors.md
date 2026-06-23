# Clinical Lab Conversion Factors

## Standard Conversion Factors (SI → US Conventional)

| Analyte | SI Unit | US Unit | Factor | Derivation |
|---------|---------|---------|--------|------------|
| Calcium | mmol/L | mg/dL | ×4.0 | 1/0.25 (molecular weight 40 mg/mmol) |
| Glucose | mmol/L | mg/dL | ×18.0 | 1/0.0555 (molecular weight 180 mg/mmol) |
| Creatinine | μmol/L | mg/dL | ÷88.4 | 1/88.4 (molecular weight 113 mg/mmol) |
| Magnesium | mmol/L | mg/dL | ×2.43 | 1/0.411 (molecular weight 24.3 mg/mmol) |
| Urea (BUN) | mmol/L | mg/dL | ×2.8 | Molecular weight 60 |
| Sodium | mmol/L | mEq/L | 1:1 | No conversion needed |
| Potassium | mmol/L | mEq/L | 1:1 | No conversion needed |
| Chloride | mmol/L | mEq/L | 1:1 | No conversion needed |
| Bicarbonate | mmol/L | mEq/L | 1:1 | No conversion needed |

## Hepatic Panel Conversion Factors

| Analyte | SI Unit | US Unit | Factor | US Range | SI Detection Threshold |
|---------|---------|---------|--------|----------|------------------------|
| Total Bilirubin | μmol/L | mg/dL | ÷17.1 | 0.1–1.2 mg/dL | > 30 μmol/L |
| Direct Bilirubin | μmol/L | mg/dL | ÷17.1 | 0.0–0.3 mg/dL | > 15 μmol/L |
| Albumin | g/L | g/dL | ÷10 | 3.5–5.0 g/dL | > 60 g/L |
| Total Protein | g/L | g/dL | ÷10 | 6.0–8.0 g/dL | > 100 g/L |
| Hemoglobin | g/L | g/dL | ÷10 | 12–17 g/dL | > 80 g/L |
| Ammonia | μmol/L | μg/dL | ×5.87 | 15–45 μg/dL | > 100 μmol/L |
| Ferritin | μg/L | ng/mL | 1:1 | 12–300 ng/mL | No conversion |

## No-Conversion Analytes (Format Normalization Only)

These analytes use the same units in SI and US systems:
- AST, ALT, ALP, GGT: U/L (both systems)
- INR: unitless ratio
- AFP: μg/L ≈ ng/mL (effectively 1:1)
- Platelets: counts are equivalent with appropriate unit notation
- Bile Acids: μmol/L (both systems)

## Physiological Reference Ranges

### Magnesium
- US normal: 1.5–2.5 mg/dL
- SI normal: 0.75–1.0 mmol/L
- Critical low: < 1.0 mg/dL
- Critical high: > 4.0 mg/dL (severe hypermagnesemia)
- **Detection**: value < 1.0 → clearly SI

### Calcium (total)
- US normal: 8.5–10.5 mg/dL
- SI normal: 2.1–2.6 mmol/L
- Hypocalcemia: < 8.5 mg/dL
- Hypercalcemia: > 10.5 mg/dL

### Glucose (fasting)
- US normal: 70–100 mg/dL
- SI normal: 3.9–5.6 mmol/L
- Hypoglycemia: < 70 mg/dL (severe: < 40 mg/dL)
- Diabetes threshold: ≥ 126 mg/dL
- Severe hyperglycemia: > 500 mg/dL
- **CRITICAL**: Values 20-70 mg/dL are valid hypoglycemia — do NOT convert

### Creatinine
- US normal: 0.7–1.3 mg/dL (men), 0.6–1.1 mg/dL (women)
- SI normal: 60–110 μmol/L (men), 50–90 μmol/L (women)
- Elevated: > 1.3 mg/dL

### Bilirubin (Total)
- US normal: 0.1–1.2 mg/dL
- SI normal: 2–20 μmol/L
- Elevated: > 1.2 mg/dL
- Severe: > 10 mg/dL

### Albumin
- US normal: 3.5–5.0 g/dL
- SI normal: 35–50 g/L
- Low: < 3.5 g/dL (indicates liver disease or malnutrition)

## Threshold Collision Rules

When SI and US ranges overlap:

| Analyte | Overlap zone | Decision rule |
|---------|--------------|---------------|
| Magnesium | 1.0–2.5 | < 1.0 → convert; else assume US |
| Calcium | 2.6–4.0 | 1.5–4.0 → convert; else assume US |
| Glucose | 3.0–50 | < 3.0 → convert; else assume US |
| Creatinine | 10–20 | > 20 → convert; else assume US |

**Default**: If uncertain, assume US (more common in US datasets).

## Edge Case Handling

### Scientific Notation
Parse `3.7648e+00` → `3.7648` before conversion. For comma-decimal scientific (`1,23e+4`), replace comma → dot first.

### Comma Decimals (European)
If last comma appears after last dot, comma is decimal separator:
- `"142,0205"` → `142.0205`
- `"1.234,56"` → `1234.56` (dot is thousand separator, comma is decimal)

### Missing Values
Treat as null and drop row:
- Empty string: `''`
- Literal `'nan'` or `'NaN'`
- Whitespace-only: `'   '`
- Actual `None`/`null`

### Ambiguous Values
When a value could be either unit:
1. Check other analytes in same row for unit consistency
2. If most values suggest SI → convert the ambiguous one
3. If uncertain → default to US
