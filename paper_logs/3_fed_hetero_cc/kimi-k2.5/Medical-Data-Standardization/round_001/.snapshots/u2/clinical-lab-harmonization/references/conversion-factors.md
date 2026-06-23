# Clinical Lab Conversion Factors

## Standard Conversion Factors

| Analyte | SI Unit | US Unit | Factor | Derivation |
|---------|---------|---------|--------|------------|
| Calcium | mmol/L | mg/dL | ×4.0 | 1/0.25 (molecular weight 40 mg/mmol) |
| Glucose | mmol/L | mg/dL | ×18.0 | 1/0.0555 (molecular weight 180 mg/mmol) |
| Creatinine | μmol/L | mg/dL | ÷88.4 | 1/88.4 (molecular weight 113 mg/mmol, unit conversion) |
| Magnesium | mmol/L | mg/dL | ×2.43 | 1/0.411 (molecular weight 24.3 mg/mmol) |
| Sodium | mmol/L | mEq/L | 1:1 | No conversion needed |
| Potassium | mmol/L | mEq/L | 1:1 | No conversion needed |
| Chloride | mmol/L | mEq/L | 1:1 | No conversion needed |
| Bicarbonate | mmol/L | mEq/L | 1:1 | No conversion needed |

## Physiological Reference Ranges

### Magnesium
- US normal: 1.5-2.5 mg/dL
- SI normal: 0.75-1.0 mmol/L
- Critical low: < 1.0 mg/dL
- Critical high: > 4.0 mg/dL (severe hypermagnesemia)

### Calcium (total)
- US normal: 8.5-10.5 mg/dL
- SI normal: 2.1-2.6 mmol/L
- Hypocalcemia: < 8.5 mg/dL (< 2.1 mmol/L)
- Hypercalcemia: > 10.5 mg/dL (> 2.6 mmol/L)

### Glucose (fasting)
- US normal: 70-100 mg/dL
- SI normal: 3.9-5.6 mmol/L
- Hypoglycemia: < 70 mg/dL (< 3.9 mmol/L)
- Diabetes threshold: ≥ 126 mg/dL (≥ 7.0 mmol/L)
- Severe hyperglycemia: > 500 mg/dL (> 27.8 mmol/L)

### Creatinine
- US normal: 0.7-1.3 mg/dL (men), 0.6-1.1 mg/dL (women)
- SI normal: 60-110 μmol/L (men), 50-90 μmol/L (women)
- Elevated: > 1.3 mg/dL (> 115 μmol/L)
- Severe elevation: > 10 mg/dL (> 884 μmol/L)

## Rounding Rules

- Standard clinical reporting: 2 decimal places
- Some labs use 1 decimal for electrolytes (Na, K, Cl, HCO3)
- Glucose often reported as integer in US labs
- Creatinine: 2 decimal places for precision in eGFR calculations

## Handling Edge Cases

### Scientific Notation
Parse values like `6.4372e+02` → `643.72` before conversion.

### Comma Decimals
European format `2,67` → `2.67` before conversion.

### Missing Values
Treat these as null and drop row or impute:
- Empty string: `''`
- Literal 'nan' or 'NaN'
- Actual None/null

### Ambiguous Values
When a value could plausibly be either unit (e.g., magnesium 1.2):
- Check other analytes in same row for unit consistency
- If most values suggest SI units, convert the ambiguous one
- If uncertain, default to US units (more common in US datasets)
