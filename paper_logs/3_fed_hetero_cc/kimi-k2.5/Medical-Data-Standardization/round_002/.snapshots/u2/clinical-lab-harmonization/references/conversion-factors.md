# Clinical Lab Conversion Factors

## Standard Conversion Factors

| Analyte | SI Unit | US Unit | Factor | Derivation |
|---------|---------|---------|--------|------------|
| Calcium | mmol/L | mg/dL | ×4.0 | MW 40 mg/mmol |
| Glucose | mmol/L | mg/dL | ×18.0 | MW 180 mg/mmol |
| Creatinine | μmol/L | mg/dL | ÷88.4 | MW 113 mg/mmol, μmol→mmol factor |
| Magnesium | mmol/L | mg/dL | ×2.43 | MW 24.3 mg/mmol |
| Sodium | mmol/L | mEq/L | 1:1 | No conversion |
| Potassium | mmol/L | mEq/L | 1:1 | No conversion |
| Chloride | mmol/L | mEq/L | 1:1 | No conversion |
| Bicarbonate | mmol/L | mEq/L | 1:1 | No conversion |

## Hepatic Panel Conversion Factors

| Analyte | SI Unit | US Unit | Factor | Notes |
|---------|---------|---------|--------|-------|
| Total_Bilirubin | μmol/L | mg/dL | ÷17.1 | 1 mg/dL = 17.1 μmol/L |
| Direct_Bilirubin | μmol/L | mg/dL | ÷17.1 | Same as total |
| Albumin | g/L | g/dL | ÷10 | Simple decimal shift |
| Total_Protein | g/L | g/dL | ÷10 | Simple decimal shift |
| Ammonia | μmol/L | μg/dL | ×5.87 | MW 17, unit conversion |
| Bile_Acids | μmol/L | mg/L | ×0.4 | MW ~400, varies by acid |
| Hemoglobin | g/L | g/dL | ÷10 | Simple decimal shift |
| Ferritin | pmol/L | μg/L | ×2.247 | MW 445 kDa |

## No Conversion Needed (Format Only)

| Analyte | Unit | Notes |
|---------|------|-------|
| AST | U/L | Same units SI and US |
| ALT | U/L | Same units SI and US |
| ALP | U/L | Same units SI and US |
| GGT | U/L | Same units SI and US |
| INR | unitless | Dimensionless ratio |
| AFP | ng/mL | Same as μg/L |
| Sodium | mEq/L | Same as mmol/L |
| Platelets | /μL | May need ×1000 if input is ×10⁹/L |

## Physiological Reference Ranges

### Glucose (Fasting)
- US normal: 70-100 mg/dL
- SI normal: 3.9-5.6 mmol/L
- Hypoglycemia: < 70 mg/dL (< 3.9 mmol/L)
- Severe hypoglycemia: < 40 mg/dL (< 2.2 mmol/L)
- Diabetes threshold: ≥ 126 mg/dL (≥ 7.0 mmol/L)

**CRITICAL overlap zone**: 50-70 mg/dL could be:
- 2.8-3.9 mmol/L (SI normal range) OR
- Hypoglycemic US values

**Safe conversion rule**: Only convert glucose if value < 3.0 mmol/L (≈54 mg/dL). Values above this threshold could be either valid hypoglycemic US values OR normal SI values. Default: keep as-is (assume US).

### Bilirubin
- US normal total: 0.2-1.2 mg/dL
- SI normal total: 3-21 μmol/L
- Jaundice: > 2.0 mg/dL (> 34 μmol/L)
- Severe: > 10 mg/dL (> 171 μmol/L)

**CRITICAL overlap zone**: 17-30 μmol/L overlaps with 1.0-1.8 mg/dL.

**Safe conversion rule**: Only convert if > 30 μmol/L. Values 17-30 μmol/L could be normal SI values OR elevated US values. Default: keep as-is.

### Albumin
- US normal: 3.5-5.0 g/dL
- SI normal: 35-50 g/L
- Hypoalbuminemia: < 3.5 g/dL (< 35 g/L)

**CRITICAL overlap zone**: 30-60 g/L is ambiguous.

**Safe conversion rule**: Only convert if > 60 g/L.

### Magnesium
- US normal: 1.5-2.5 mg/dL
- SI normal: 0.75-1.0 mmol/L

**No significant overlap**: Values < 1.0 are clearly SI. Values 1.0-1.5 are ambiguous but rare as SI. Default: convert if < 1.0.

### Creatinine
- US normal: 0.7-1.3 mg/dL (men), 0.6-1.1 mg/dL (women)
- SI normal: 60-110 μmol/L (men), 50-90 μmol/L (women)

**Safe conversion rule**: Convert if > 20 μmol/L. Values < 20 μmol/L are clearly mg/dL.

## Threshold Collision Rules

When SI and US ranges overlap significantly:

| Analyte | Overlap zone | Decision rule |
|---------|--------------|---------------|
| Magnesium | 1.0-2.5 mg/dL vs mmol/L | < 1.0 → convert; else assume US |
| Calcium | 2.6-4.0 mmol/L range | < 2.0 → convert; 2.0-4.0 → check context |
| Glucose | 3.0-5.6 mmol/L vs 54-100 mg/dL | **< 3.0 mmol/L → convert; else assume US** |
| Creatinine | 10-20 μmol/L vs mg/dL | > 20 μmol/L → convert; else assume US |
| Bilirubin | 17-30 μmol/L | > 30 μmol/L → convert; else assume US |
| Albumin | 35-60 g/L | > 60 g/L → convert; else assume US |

**Default rule**: When uncertain, assume US units (more common in US datasets).

## Handling Edge Cases

### Scientific Notation
Parse values like `6.4372e+02` → `643.72` before conversion. For comma-decimal scientific (`1,23e+4`), replace comma → dot first.

### Comma Decimals (European)
If last comma appears after last dot, comma is decimal separator:
- `"142,0205"` → `142.0205`
- `"1.234,56"` → `1234.56` (dot is thousand separator, comma is decimal)

### Missing Values
Treat as null and drop row:
- Empty string: `''`
- Literal `'nan'`, `'NaN'`, `'NA'`
- Whitespace-only: `'   '`
- Actual `None`/`null`

### Ambiguous Values (In Overlap Zone)
When a value could plausibly be either unit:
1. Check other analytes in same row for unit consistency
2. If majority suggests SI → consider converting
3. **Default**: Keep as-is (assume US), flag for manual review if needed

## Rounding Rules

**For verifiers**: Never round. Output raw floats with full precision.

**For clinical reports** (separate concern):
- Standard clinical reporting: 2 decimal places
- Some labs use 1 decimal for electrolytes (Na, K, Cl, HCO3)
- Glucose often reported as integer in US labs
- Never round in intermediate calculations; only final display