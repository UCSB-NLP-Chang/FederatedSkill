# Clinical Lab Conversion Factors

## Standard Conversion Factors (SI → US Conventional)

| Analyte    | SI Unit | US Unit | Factor | Direction | Derivation                          |
|------------|---------|---------|--------|-----------|-------------------------------------|
| Calcium    | mmol/L  | mg/dL   | 4.0    | multiply  | MW 40 mg/mmol (÷ 0.25)              |
| Glucose    | mmol/L  | mg/dL   | 18.0   | multiply  | MW 180 mg/mmol (÷ 0.0555)           |
| Creatinine | μmol/L  | mg/dL   | 88.4   | divide    | MW 113 mg/mmol, μmol→mmol factor    |
| Magnesium  | mmol/L  | mg/dL   | 2.43   | multiply  | MW 24.3 mg/mmol (÷ 0.411)           |
| Urea (BUN) | mmol/L  | mg/dL   | 2.8    | multiply  | MW 60 mg/mmol                       |
| Bilirubin  | μmol/L  | mg/dL   | 17.1   | divide    | MW 584 mg/mmol                      |
| Albumin    | g/L     | g/dL    | 10     | divide    | Decimal shift                       |
| Protein    | g/L     | g/dL    | 10     | divide    | Decimal shift                       |
| Hemoglobin | g/L     | g/dL    | 10     | divide    | Decimal shift                       |

**No conversion needed**: Sodium, Potassium, Chloride, Bicarbonate (mmol/L = mEq/L).

## Cardiology Panel Conversion Factors

### CRITICAL: BNP vs NT-proBNP

**BNP and NT-proBNP are DIFFERENT molecules with DIFFERENT molecular weights and DIFFERENT conversion factors.**

| Analyte    | SI Unit | US Unit    | Factor  | Direction | Safe SI Threshold | Notes                       |
|------------|---------|------------|---------|-----------|-------------------|-----------------------------|
| BNP        | pmol/L  | pg/mL      | 0.143   | multiply  | > 5000 pmol/L     | MW ~3464 Da. **NOT 0.289**  |
| NT_proBNP  | —       | pg/mL      | —       | —         | —                 | **NO CONVERSION**           |
| Troponin_I | μg/L    | ng/mL      | 1000    | multiply  | < 0.05 μg/L       | Values >1 already ng/mL     |
| Troponin_T | μg/L    | ng/mL      | 1000    | multiply  | < 0.1 μg/L        | Values >1 already ng/mL     |

**NT-proBNP Non-Conversion Rationale**:
- Both pmol/L and pg/mL are commonly reported by different assay manufacturers
- No reliable detection threshold exists (ranges vary by lab)
- Keep NT-proBNP values as-is unless explicit unit metadata is present

**BNP Factor Derivation**:
- BNP MW: ~3464 g/mol
- 1 pmol/L × 3464 g/mol ÷ 1000 mL/L ÷ 1000 pg/ng = **0.143 pg/mL**
- **Common error**: Using 0.289 (NT-proBNP-like factor) causes 2× error

**Troponin Scale Warning**:
- Values >1 are certainly already ng/mL (US conventional)
- A value like 16392 treated as μg/L → ×1000 gives 16M ng/mL (impossible)
- Only convert if value < 0.05 (Troponin_I) or < 0.1 (Troponin_T)

## Hepatic Panel Conversion Factors

| Analyte          | SI Unit   | US Unit | Factor | Direction | Safe SI Threshold | Notes                    |
|------------------|-----------|---------|--------|-----------|-------------------|--------------------------|
| Total_Bilirubin  | μmol/L    | mg/dL   | 17.1   | divide    | > 30 μmol/L       | Values <30 may be US     |
| Direct_Bilirubin | μmol/L    | mg/dL   | 17.1   | divide    | > 15 μmol/L       | Values <15 may be US     |
| Albumin          | g/L       | g/dL    | 10     | divide    | > 60 g/L          | Values <60 may be US     |
| Total_Protein    | g/L       | g/dL    | 10     | divide    | > 100 g/L         | Values <100 may be US    |
| Ammonia          | μmol/L    | μg/dL   | 5.87   | multiply  | > 100 μmol/L      | Check lab reference      |
| Bile_Acids       | μmol/L    | mg/L    | 0.4    | multiply  | > 50 μmol/L       | MW varies by acid        |
| AFP              | μg/L      | ng/mL   | 1      | none      | —                 | Same units               |
| Ferritin         | pmol/L    | μg/L    | 2.247  | multiply  | —                 | MW 445 kDa               |

**No conversion needed**: AST, ALT, ALP, GGT (U/L → U/L), INR (unitless), Platelets (check input format).

## Thyroid & Mineral Panel Conversion Factors

### Critical: Factor Direction

When conversion factor < 1, conventional values are SMALLER numerically than SI. You must MULTIPLY.

| Analyte          | SI Unit   | US Unit | Factor | Direction | Safe SI Threshold | Notes                    |
|------------------|-----------|---------|--------|-----------|-------------------|--------------------------|
| Free_T4          | pmol/L    | ng/dL   | 12.87  | divide    | > 30 pmol/L       | Values <10 likely US      |
| Free_T3          | pmol/L    | pg/mL   | 15.38  | divide    | > 30 pmol/L       | Values <10 likely US      |
| Total_T4         | nmol/L    | μg/dL   | 12.87  | divide    | > 200 nmol/L      | Values <60 likely US     |
| Total_T3         | nmol/L    | ng/dL   | 64.94  | multiply  | < 3.0 nmol/L      | **CRITICAL: <3.0 threshold** |
| PTH              | ng/L      | pg/mL   | 0.106  | divide    | > 500 ng/L        | Verify input unit        |
| Vitamin_D_25OH   | nmol/L    | ng/mL   | 2.5    | divide    | > 100 nmol/L      | Values <50 likely US     |
| Phosphorus       | mmol/L    | mg/dL   | 3.097  | multiply  | < 3.0 mmol/L      | Values >3 likely US      |
| Ionized_Calcium  | mmol/L    | mg/dL   | 4.008  | multiply  | 1.5–4.0 mmol/L    | Same as total Ca         |

**Total_T3 Threshold Note**: SI values are numerically SMALL (1.2-2.8 nmol/L normal range). Using >50 threshold misses these values. Use <3.0 threshold to catch SI values.

**No conversion needed**: TSH (mIU/L), Anti_TPO (IU/mL), Thyroglobulin (ng/mL), Thyroglobulin_Antibody (IU/mL), Calcitonin (pg/mL).

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

### Thyroid Hormones
- Free T4 US normal: 0.8-1.8 ng/dL (SI: 10-25 pmol/L)
- Free T3 US normal: 2.3-4.2 pg/mL (SI: 3.5-6.5 pmol/L)
- Total T4 US normal: 5.0-12.0 μg/dL (SI: 64-154 nmol/L)
- Total T3 US normal: 80-200 ng/dL (SI: 1.2-3.1 nmol/L)
- TSH US normal: 0.4-4.0 mIU/L (no conversion)

**Overlap zones and thresholds**:
- Free_T4: Use >30 pmol/L threshold (values 10-30 ambiguous)
- Free_T3: Use >30 pmol/L threshold (values 10-30 ambiguous)
- Total_T4: Use >200 nmol/L threshold (values 60-200 ambiguous)
- Total_T3: Use <3.0 nmol/L threshold (SI values are small, 1.2-2.8)

### Vitamin D & PTH
- 25-OH Vitamin D US normal: 30-100 ng/mL (SI: 75-250 nmol/L)
- PTH US normal: 10-65 pg/mL (SI: 1.1-6.8 pmol/L or ~94-613 ng/L)
- **Decision**: Convert Vit D if >100 nmol/L. Convert PTH if >500 ng/L.

### Phosphorus & Calcium
- Phosphorus US normal: 2.5-4.5 mg/dL (SI: 0.81-1.45 mmol/L)
- Ionized Calcium US normal: 4.5-5.6 mg/dL (SI: 1.12-1.40 mmol/L)
- **Decision**: Convert Phosphorus if <3.0 mmol/L. Convert Ionized Ca if 1.5-4.0 mmol/L.

### Cardiology Biomarkers
- BNP US normal: <100 pg/mL. Heart failure: >400 pg/mL. Severe: >1000 pg/mL.
- NT-proBNP US normal: <300 pg/mL. Heart failure: >900 pg/mL. Severe: >5000 pg/mL.
- Troponin I/T US normal: <0.04 ng/mL. Pathological: 0.04-50 ng/mL.
- **Decision**: Convert BNP if >5000. Convert Troponin if <0.05 (I) or <0.1 (T).

## Post-Conversion Plausibility Check

After conversion, verify values fall in physiologically plausible ranges:

| Analyte    | Plausible US Range (mg/dL) | Flag if outside            |
|------------|---------------------------|----------------------------|
| Glucose    | 30-600                    | >600 (DKA?) or <30 (crash) |
| Bilirubin  | 0.1-50                    | >50 (check unit)           |
| Albumin    | 1.0-6.0 g/dL              | >6.0 or <1.0               |
| Creatinine | 0.3-25                    | >25 (error?)               |
| Magnesium  | 0.5-10                    | >10 (check unit)           |
| Calcium    | 6.0-14                    | >14 (check unit)           |
| Free_T4    | 0.3-3.0 ng/dL             | >3.0 or <0.3               |
| Total_T4   | 1.0-25.0 μg/dL            | >25.0 or <1.0              |
| Total_T3   | 0.5-10 ng/dL              | >10 (check unit)           |
| TSH        | 0.1-100 mIU/L             | >100 (check unit)          |
| BNP        | 0-5000 pg/mL              | >10000 (check unit)        |
| NT_proBNP  | 0-35000 pg/mL             | >35000 (check unit)        |
| Troponin_I | 0-50000 ng/mL             | >50000 (check unit)        |
| Troponin_T | 0-10000 ng/mL             | >10000 (check unit)        |

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