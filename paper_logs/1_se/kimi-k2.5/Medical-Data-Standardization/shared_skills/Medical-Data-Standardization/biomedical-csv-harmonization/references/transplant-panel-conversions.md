# Transplant Panel Unit Conversions

Extended reference for solid organ transplant monitoring panels combining immunosuppressant drug levels with organ function markers.

## Panel Structure

Transplant panels typically combine:
- **Immunosuppressant levels**: Tacrolimus (FK506), Cyclosporine, Sirolimus, Everolimus — trough concentrations in ng/mL
- **Chemistry/metabolic**: Creatinine, Magnesium, Potassium, Glucose (renal function, electrolytes)
- **Organ-specific function**: Liver enzymes (AST, ALT), Bilirubin, Albumin, Phosphorus (hepatic function)

## Critical Column Order

Output typically requires **chemistry markers first**, then **organ-specific markers**:
1. Tacrolimus
2. Creatinine
3. Magnesium
4. Potassium
5. Glucose
6. Bilirubin_Total
7. Albumin
8. AST
9. ALT
10. Phosphorus

## Immunosuppressant Drug Levels (NO CONVERSION)

| Drug | Unit | Typical Range | Notes |
|------|------|---------------|-------|
| Tacrolimus | ng/mL | 5–20 (therapeutic) | Trough level, highly variable by time post-transplant |
| Cyclosporine | ng/mL | 100–400 (varies by assay) | No unit conversion needed |
| Sirolimus | ng/mL | 5–15 | Trough level |
| Everolimus | ng/mL | 3–8 | Trough level |

**Critical**: Do NOT convert immunosuppressant levels. They are always reported in ng/mL (or μg/L, same scale) and are already in the conventional unit.

## Common Conversions in Transplant Panels

| Analyte | SI Unit | US Unit | Conversion | Detection | Plausible US Range |
|---------|---------|---------|------------|-----------|-------------------|
| Creatinine | μmol/L | mg/dL | ÷ 88.42 | > 20 | 0.3–20 mg/dL |
| Glucose | mmol/L | mg/dL | × 18 | < 20 | 20–600 mg/dL |
| Bilirubin_Total | μmol/L | mg/dL | ÷ 17.1 | > 20 | 0.1–50 mg/dL |
| Albumin | g/L | g/dL | ÷ 10 | > 10 | 1.0–6.0 g/dL |
| Magnesium | mmol/L | mg/dL | × 2.43 | < 1.5 | 1.0–5.0 mg/dL |
| Phosphorus | mmol/L | mg/dL | × 3.1 | < 3 | 1.0–12 mg/dL |
| Potassium | mmol/L | mEq/L | 1:1 | — | 2.5–7.0 mEq/L |

## Data Quality Rules

### Incomplete Patient Exclusion
Must check completeness in **BOTH** source files before including patient:
- If chemistry file has missing values → exclude
- If liver/organ file has missing values → exclude
- Only patients with complete data in ALL files are included

### Pathological Values in Transplant Patients
Transplant recipients often have abnormal values — do NOT reject:
- **Tacrolimus toxicity**: > 20 ng/mL (nephrotoxic)
- **Rejection episodes**: Bilirubin may spike to 300+ μmol/L
- **Post-transplant AKI**: Creatinine 200–1000+ μmol/L
- **Hypomagnesemia**: < 1.5 mg/dL (tacrolimus effect)

## Multi-File Alignment Pattern

```python
import pandas as pd

# Read chemistry panel
df_chem = pd.read_csv('chemistry.csv', dtype=str, sep='\t')
df_chem.columns = ['patient_code', 'Tacrolimus', 'Creatinine', 
                   'Magnesium', 'Potassium', 'Glucose']

# Read organ function panel
df_organ = pd.read_csv('organ.csv', dtype=str, sep='\t')
df_organ.columns = ['visit_tag', 'patient_code', 'Bilirubin_Total',
                    'Albumin', 'AST', 'ALT', 'Phosphorus']

# Find common patients (inner join logic)
common_patients = set(df_chem['patient_code']) & set(df_organ['patient_code'])

# Merge and exclude incomplete
merged = df_chem.merge(df_organ, on='patient_code', how='inner')
# Drop rows with ANY missing in measurement columns
measurement_cols = ['Tacrolimus', 'Creatinine', 'Magnesium', 'Potassium', 
                    'Glucose', 'Bilirubin_Total', 'Albumin', 'AST', 'ALT', 'Phosphorus']
merged = merged.dropna(subset=measurement_cols)
```

## Output Verification

| Check | Expected |
|-------|----------|
| Row count | Equal to complete patients only |
| Column count | Exactly 10 (or per specification) |
| Column order | Chemistry first, then organ-specific |
| Decimal places | Exactly 2 for all values |
| No identifiers | patient_code excluded from output |
| Tacrolimus range | 3–30 ng/mL (rough check for errors) |

## Common Pitfalls

### Pitfall 1: Converting Tacrolimus
```python
# WRONG: Applying creatinine-style conversion to drug level
tac_us = tac_si / 88.42  # Nonsense! Tacrolimus is already ng/mL

# CORRECT: Pass through unchanged
tac_final = tac_raw  # Already in target units
```

### Pitfall 2: Including incomplete patients
Patient 9 may have chemistry but missing liver data — must exclude entirely, not partial data.

### Pitfall 3: Wrong column order
Liver enzymes before chemistry violates typical transplant panel output spec.
