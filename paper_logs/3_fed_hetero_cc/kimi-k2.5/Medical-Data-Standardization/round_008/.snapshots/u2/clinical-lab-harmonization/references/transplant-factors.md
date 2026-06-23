# Transplant Panel Conversion Factors

## Analytes Specific to Transplant Monitoring

Transplant panels combine immunosuppressant drug monitoring with renal/hepatic function markers.

### Immunosuppressants (No Conversion Needed)

| Analyte | Standard Unit | Notes |
|---------|---------------|-------|
| Tacrolimus | ng/mL | Whole blood trough level. No SI/US variation. |
| Cyclosporine | ng/mL | Whole blood trough level. No SI/US variation. |
| Sirolimus | ng/mL | Whole blood trough level. No SI/US variation. |

**Tacrolimus therapeutic range**: 5-20 ng/mL (varies by transplant type and time post-transplant)

### Renal Function Markers

| Analyte | SI Unit | US Unit | Factor | Operation | Threshold |
|---------|---------|---------|--------|-----------|----------|
| Creatinine | μmol/L | mg/dL | 88.4 | divide | >20 |
| BUN | mmol/L | mg/dL | 2.8 | multiply | <5 |

### Hepatic Function Markers

| Analyte | SI Unit | US Unit | Factor | Operation | Threshold |
|---------|---------|---------|--------|-----------|----------|
| Bilirubin_Total | μmol/L | mg/dL | 17.1 | divide | >30 |
| Albumin | g/L | g/dL | 10 | divide | >60 |
| AST | U/L | U/L | — | none | — |
| ALT | U/L | U/L | — | none | — |
| ALP | U/L | U/L | — | none | — |
| GGT | U/L | U/L | — | none | — |

### Electrolytes & Metabolites

| Analyte | SI Unit | US Unit | Factor | Operation | Threshold |
|---------|---------|---------|--------|-----------|----------|
| Magnesium | mmol/L | mg/dL | 2.43 | multiply | <1.0 |
| Phosphorus | mmol/L | mg/dL | 3.097 | multiply | <3.0 |
| Glucose | mmol/L | mg/dL | 18.0 | multiply | <3.0 |
| Potassium | mmol/L | mEq/L | — | none | — |
| Sodium | mmol/L | mEq/L | — | none | — |

## Multi-File Join Pattern

Transplant data often split across multiple files:
1. `transplant_chemistry.csv`: patient_code, Tacrolimus, Creatinine, Magnesium, Potassium, Glucose
2. `transplant_liver.csv`: visit_tag, patient_code, Bilirubin_Total, Albumin, AST, ALT, Phosphorus

**Critical join rules:**
- **Join key**: `patient_code` ONLY
- **NOT a join key**: `visit_tag` (this is metadata to exclude)
- **Join type**: Inner join to ensure complete data only
- **Drop rows**: Where ANY of the 10 measurement columns is NaN

```python
import pandas as pd

chem_df = pd.read_csv('transplant_chemistry.csv')
liver_df = pd.read_csv('transplant_liver.csv')

# Inner join on patient_code (NOT visit_tag)
merged = pd.merge(chem_df, liver_df, on='patient_code', how='inner')

# Drop rows with any missing measurements
measurement_cols = ['Tacrolimus', 'Creatinine', 'Magnesium', 'Potassium', 'Glucose',
                   'Bilirubin_Total', 'Albumin', 'AST', 'ALT', 'Phosphorus']
merged = merged.dropna(subset=measurement_cols)

# Exclude ID columns from output
output_cols = measurement_cols
merged[output_cols].to_csv('output.csv', index=False)  # NO float_format!
```

## Output Column Order

**Required exact order:**
```
Tacrolimus,Creatinine,Magnesium,Potassium,Glucose,Bilirubin_Total,Albumin,AST,ALT,Phosphorus
```

Use: `df[output_cols].to_csv(output_path, index=False)` — NO float_format parameter.

## Physiological Ranges for Transplant Patients

| Analyte | Normal Range | Transplant Range | Notes |
|---------|-------------|------------------|-------|
| Tacrolimus | 5-20 ng/mL | 5-20 ng/mL | Target varies by organ |
| Creatinine | 0.7-1.3 mg/dL | 0.5-5.0 mg/dL | Elevated in rejection, nephrotoxicity |
| Bilirubin_Total | 0.2-1.2 mg/dL | 0.2-30 mg/dL | Elevated in hepatic rejection |
| AST | 10-40 U/L | 10-2000 U/L | Hepatocellular injury |
| ALT | 7-56 U/L | 7-2000 U/L | Hepatocellular injury |
| Albumin | 3.5-5.0 g/dL | 2.0-5.0 g/dL | May be low in chronic illness |

## Common Transplant Panel Errors

| Error | Manifestation | Fix |
|-------|---------------|-----|
| Rounding output | 14.33 instead of 14.329... | NEVER round - full precision |
| Converting Tacrolimus | 15 ng/mL → wrong value | NO conversion needed |
| Converting AST/ALT | 500 U/L → wrong value | NO conversion needed |
| Missing join | Duplicate or missing patients | Inner join on patient_code |
| Wrong join key | Using visit_tag as key | patient_code is the ONLY join key |
| Albumin threshold wrong | Converting 4.0 g/dL | Use >60 threshold (g/L values are large) |
| Missing headers | Output without column names | Always include header row |
| Including IDs in output | patient_code/visit_tag in CSV | Exclude both from output |
