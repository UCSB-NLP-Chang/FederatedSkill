# Clinical Lab Conversion Factors

## Standard Conversion Factors (SI → US Conventional)

| Analyte | SI Unit | US Unit | Factor | Derivation |
|---------|---------|---------|--------|------------|
| Calcium | mmol/L | mg/dL | ×4.0 | MW 40 mg/mmol (÷ 0.25) |
| Glucose | mmol/L | mg/dL | ×18.0 | MW 180 mg/mmol (÷ 0.0555) |
| Creatinine | μmol/L | mg/dL | ÷88.4 | MW 113 mg/mmol, μmol→mmol factor |
| Magnesium | mmol/L | mg/dL | ×2.43 | MW 24.3 mg/mmol (÷ 0.411) |
| Urea (BUN) | mmol/L | mg/dL | ×2.8 | MW 60 mg/mmol |
| Bilirubin | μmol/L | mg/dL | ÷17.1 | MW 584 mg/mmol |
| Albumin | g/L | g/dL | ÷10 | Decimal shift |
| Protein | g/L | g/dL | ÷10 | Decimal shift |
| Hemoglobin | g/L | g/dL | ÷10 | Decimal shift |

**No conversion needed**: Sodium, Potassium, Chloride, Bicarbonate (mmol/L = mEq/L).

## Hepatic Panel Conversion Factors

| Analyte | SI Unit | US Unit | Factor | Safe SI Threshold | Notes |
|---------|---------|---------|--------|-------------------|-------|
| Total_Bilirubin | μmol/L | mg/dL | ÷17.1 | > 30 μmol/L | Values <30 may be US |
| Direct_Bilirubin | μmol/L | mg/dL | ÷17.1 | > 15 μmol/L | Values <15 may be US |
| Albumin | g/L | g/dL | ÷10 | > 60 g/L | Values <60 may be US |
| Total_Protein | g/L | g/dL | ÷10 | > 100 g/L | Values <100 may be US |
| Ammonia | μmol/L | μg/dL | ×5.87 | > 100 μmol/L | Check lab reference |
| Bile_Acids | μmol/L | mg/L | ×0.4 | > 50 μmol/L | MW varies by acid |
| AFP | μg/L | ng/mL | 1:1 | — | Same units |
| Ferritin | pmol/L | μg/L | ×2.247 | — | MW 445 kDa |

**No conversion needed**: AST, ALT, ALP, GGT (U/L → U/L), INR (unitless), Platelets (check input format).

## Thyroid & Mineral Panel Conversion Factors

| Analyte | SI Unit | US Unit | Factor | Operation | Safe SI Threshold | Notes |
|---------|---------|---------|--------|-----------|-------------------|-------|
| Free_T4 | pmol/L | ng/dL | 12.87 | ÷ | > 30 pmol/L | Values <10 likely US |
| Free_T3 | pmol/L | pg/mL | 15.38 | ÷ | > 30 pmol/L | Values <5 likely US |
| Total_T4 | nmol/L | μg/dL | 12.87 | ÷ | > 200 nmol/L | Values <15 likely US |
| Total_T3 | nmol/L | ng/dL | 64.94 | × | < 3.0 nmol/L | Values >50 likely US |
| PTH | ng/L | pg/mL | 0.106 | × | > 500 ng/L | Verify input unit |
| Vitamin_D_25OH | nmol/L | ng/mL | 2.5 | ÷ | > 100 nmol/L | Values <50 likely US |
| Phosphorus | mmol/L | mg/dL | 3.097 | × | < 3.0 mmol/L | Values >3 likely US |
| Ionized_Calcium | mmol/L | mg/dL | 4.0 | × | 1.5–4.0 mmol/L | Same as total Ca |

**No conversion needed**: TSH (mIU/L), Anti_TPO (IU/mL), Thyroglobulin (ng/mL), Thyroglobulin_Antibody (IU/mL), Calcitonin (pg/mL).

### Total_T3 Special Case

Total_T3 is unique among thyroid hormones because **conventional values are numerically larger than SI values**:
- SI normal range: 1.2-2.8 nmol/L (small numbers)
- US normal range: 80-200 ng/dL (large numbers)
- Conversion: 1 nmol/L = 64.94 ng/dL, so multiply SI by 64.94

**Anti-pattern**: Using ÷0.0154 or ×0.0154. The factor 0.0154 is for ng/dL → nmol/L, not nmol/L → ng/dL.

## Physiological Reference Ranges

### Glucose (fasting)
- US normal: 70-100 mg/dL
- SI normal: 3.9-5.6 mmol/L
- Hypoglycemia: < 70 mg/dL (< 3.9 mmol/L)
- Severe hypoglycemia: < 40 mg/dL (< 2.2 mmol/L)
- Diabetes threshold: ≥ 126 mg/dL (≥ 7.0 mmol/L)
- Severe hyperglycemia: > 500 mg/dL (> 27.8 mmol/L)

**CRITICAL overlap zone**: Values 3-50 are ambiguous.
- 3.0 mmol/L = 54 mg/dL (hypoglycemia)
- 50 mmol/L = 900 mg/dL (severe DKA)
- Values in this range may be SI mmol/L OR US mg/dL
- **Decision**: Convert ONLY if <3.0 mmol/L. Values 3-50, keep as-is.

### Magnesium
- US normal: 1.5-2.5 mg/dL
- SI normal: 0.75-1.0 mmol/L
- Critical low: < 1.0 mg/dL
- Critical high: > 4.0 mg/dL (hypermagnesemia)

**Overlap zone**: Values 1.0-2.5 are ambiguous.
- 1.0 mmol/L = 2.43 mg/dL (normal US)
- 2.5 mmol/L = 6.08 mg/dL (hypermagnesemia)
- **Decision**: Convert ONLY if <1.0. Values 1.0-2.5, keep as-is.

### Bilirubin (Total)
- US normal: 0.2-1.2 mg/dL
- SI normal: 3-21 μmol/L
- Jaundice: > 2.0 mg/dL (> 34 μmol/L)
- Severe: > 10 mg/dL (> 171 μmol/L)

**Overlap zone**: Values 17-30 μmol/L are ambiguous.
- 17 μmol/L = 1.0 mg/dL (normal)
- 30 μmol/L = 1.8 mg/dL (mildly elevated)
- **Decision**: Convert ONLY if >30 μmol/L.

### Creatinine
- US normal: 0.7-1.3 mg/dL (men)
- SI normal: 60-110 μmol/L (men)
- Elevated: > 1.3 mg/dL (> 115 μmol/L)
- Severe: > 10 mg/dL (> 884 μmol/L)

**Decision**: Convert if >20 (clearly μmol/L). Values 1-20, keep as-is.

### Albumin
- US normal: 3.5-5.0 g/dL
- SI normal: 35-50 g/L
- Hypoalbuminemia: < 3.5 g/dL (< 35 g/L)

**Decision**: Convert if >60 g/L. Values <60 may be US g/dL.

### Thyroid Function
- TSH normal: 0.4-4.0 mIU/L (no conversion needed)
- Free T4 US normal: 0.8-1.8 ng/dL (SI: 10-23 pmol/L)
- Free T3 US normal: 2.3-4.2 pg/mL (SI: 3.5-6.5 pmol/L)
- Total T4 US normal: 5.0-12.0 μg/dL (SI: 64-154 nmol/L)
- Total T3 US normal: 80-200 ng/dL (SI: 1.2-3.1 nmol/L)

**Threshold decisions**:
- Free_T4: Convert if >30 pmol/L (conservative to avoid converting high US values like 2.0 ng/dL = 25.7 pmol/L)
- Free_T3: Convert if >30 pmol/L (similar conservative threshold)
- Total_T4: Convert if >200 nmol/L (SI and US ranges overlap 64-161 nmol/L, use high threshold)
- Total_T3: Convert if <3.0 nmol/L (SI values are small, 1.2-2.8 range)

### Vitamin D & PTH
- 25-OH Vitamin D US normal: 30-100 ng/mL (SI: 75-250 nmol/L)
- PTH US normal: 10-65 pg/mL (SI: 1.1-6.8 pmol/L or ~94-613 ng/L)
- **Decision**: Convert Vit D if >100 nmol/L. Convert PTH if >500 ng/L.

### Phosphorus & Calcium
- Phosphorus US normal: 2.5-4.5 mg/dL (SI: 0.81-1.45 mmol/L)
- Ionized Calcium US normal: 4.5-5.6 mg/dL (SI: 1.12-1.40 mmol/L)
- **Decision**: Convert Phosphorus if <3.0 mmol/L. Convert Ionized Ca if 1.5-4.0 mmol/L.

## Post-Conversion Plausibility Check

After conversion, verify values fall in physiologically plausible ranges:

| Analyte | Plausible US Range | Flag if outside |
|---------|-------------------|-----------------|
| Glucose | 30-600 mg/dL | >600 (DKA?) or <30 (crash) |
| Bilirubin | 0.1-50 mg/dL | >50 (check unit) |
| Albumin | 1.0-6.0 g/dL | >6.0 or <1.0 |
| Creatinine | 0.3-25 mg/dL | >25 (error?) |
| Magnesium | 0.5-10 mg/dL | >10 (check unit) |
| Calcium | 6.0-14 mg/dL | >14 (check unit) |
| Free_T4 | 0.3-3.0 ng/dL | >3.0 or <0.3 |
| Total_T4 | 1.0-25.0 μg/dL | >25.0 or <1.0 |
| Total_T3 | 0.5-10 ng/dL | >10 or <0.5 |
| TSH | 0.1-100 mIU/L | >100 (check unit) |

If converted value is >10× the upper bound, likely a false conversion — original was already US.

## Edge Case Handling

### Scientific Notation
Parse `3.7648e+00` → `3.7648` before conversion. For comma-decimal scientific (`1,23e+4`), replace comma → dot first.

### Comma Decimals (European)
If last comma appears after last dot, comma is decimal separator:
- `"142,0205"` → `142.0205`
- `"1.234,56"` → `1234.56` (dot is thousand separator)

### Missing Values
Drop row if any measurement column has:
- Empty string: `''`
- Literal `'nan'`, `'NaN'`, `'NA'`
- Whitespace-only: `'   '`
- Actual `None`/`null`

### Ambiguous Values
When a value could be either unit (in overlap zone):
1. Check other analytes in same row for unit consistency
2. If majority suggests SI → consider converting
3. **Default**: Keep as-is (assume US), flag for review