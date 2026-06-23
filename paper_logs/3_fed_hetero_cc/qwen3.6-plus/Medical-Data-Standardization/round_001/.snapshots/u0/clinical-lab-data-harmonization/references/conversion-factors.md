# Clinical Lab Conversion Factors

## Standard Conversion Factors (SI → US Conventional)

| Analyte   | SI Unit  | US Unit | Factor | Operation | Derivation                        |
|-----------|----------|---------|--------|-----------|-----------------------------------|
| Calcium   | mmol/L   | mg/dL   | ×4.0   | multiply  | 1/0.25 (molecular weight 40)      |
| Glucose   | mmol/L   | mg/dL   | ×18.0  | multiply  | 1/0.0555 (molecular weight 180)   |
| Creatinine| μmol/L   | mg/dL   | ÷88.4  | divide    | 1/88.4 (molecular weight 113)     |
| Magnesium | mmol/L   | mg/dL   | ×2.43  | multiply  | 1/0.411 (molecular weight 24.3)   |
| Urea (BUN)| mmol/L   | mg/dL   | ×2.8   | multiply  |                                   |
| Bilirubin | μmol/L   | mg/dL   | ÷17.1  | divide    |                                   |

Note: Sodium, Potassium, Chloride, Bicarbonate — mmol/L equals mEq/L. No conversion needed.

## Physiological Reference Ranges

### Magnesium
- US normal: 1.5–2.5 mg/dL
- SI normal: 0.75–1.0 mmol/L
- Critical low: < 1.0 mg/dL
- Critical high: > 4.0 mg/dL (severe hypermagnesemia)
- **Detection**: value < 1.0 → clearly SI. Value 1.0–2.5 → ambiguous; default to US.

### Calcium (total)
- US normal: 8.5–10.5 mg/dL
- SI normal: 2.1–2.6 mmol/L
- Hypocalcemia: < 8.5 mg/dL (< 2.1 mmol/L)
- Hypercalcemia: > 10.5 mg/dL (> 2.6 mmol/L)
- **Detection**: value 1.5–4.0 → likely SI mmol/L. Value > 4.0 → may be elevated mg/dL; check context.

### Glucose (fasting)
- US normal: 70–100 mg/dL
- SI normal: 3.9–5.6 mmol/L
- Hypoglycemia: < 70 mg/dL (< 3.9 mmol/L)
- Diabetes threshold: ≥ 126 mg/dL (≥ 7.0 mmol/L)
- Severe hyperglycemia: > 500 mg/dL (> 27.8 mmol/L)
- **Detection**: value 1–50 → likely SI mmol/L. Value > 50 → check context (diabetic patients can have > 400 mg/dL legitimately).

### Creatinine
- US normal: 0.7–1.3 mg/dL (men), 0.6–1.1 mg/dL (women)
- SI normal: 60–110 μmol/L (men), 50–90 μmol/L (women)
- Elevated: > 1.3 mg/dL (> 115 μmol/L)
- Severe: > 10 mg/dL (> 884 μmol/L)
- **Detection**: value > 20 → likely SI μmol/L. Value 1–20 → likely mg/dL.

## Threshold Collision Rules

When SI and US ranges overlap significantly:

| Analyte   | Overlap zone     | Decision rule                               |
|-----------|------------------|---------------------------------------------|
| Magnesium | 1.0–2.5          | < 1.0 → convert; else assume US             |
| Calcium   | 2.6–4.0          | < 4.0 and outside US range → convert        |
| Glucose   | 5–50             | Complex; cross-reference other analytes     |
| Creatinine| 10–20            | > 20 → convert; 1–20 → assume US            |

Default: if uncertain, assume US (more common in US datasets).

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
When a value could be either unit (e.g., magnesium 1.2):
1. Check other analytes in same row for unit consistency
2. If most values suggest SI → convert the ambiguous one
3. If uncertain → default to US

## Rounding Rules

Standard clinical reporting: 2 decimal places. Exception: glucose often reported as integer in US labs. Creatinine needs 2 decimals for eGFR calculations.

Apply rounding AFTER unit conversion, not before.