# Transplant Panel Harmonization Reference

## Typical Panel Structure

Transplant monitoring combines chemistry and liver function panels:

### Chemistry File Columns
- `patient_code` (join key)
- `Tacrolimus` — immunosuppressant, ng/mL (no conversion)
- `Creatinine` — renal function, mg/dL or μmol/L
- `Magnesium` — electrolyte, mg/dL or mmol/L
- `Potassium` — electrolyte, mEq/L (no conversion)
- `Glucose` — metabolic, mg/dL or mmol/L

### Liver Function File Columns
- `visit_tag` (metadata, exclude from output)
- `patient_code` (join key)
- `Bilirubin_Total` — hepatic, mg/dL or μmol/L
- `Albumin` — hepatic, g/dL or g/L
- `AST` — hepatic enzyme, U/L (no conversion)
- `ALT` — hepatic enzyme, U/L (no conversion)
- `Phosphorus` — mineral, mg/dL or mmol/L

## Conversion Rules for Transplant Panels

| Analyte | SI Unit | US Unit | Factor | Operation | Threshold | Notes |
|---------|---------|---------|--------|-----------|-----------|-------|
| Bilirubin_Total | μmol/L | mg/dL | 17.1 | divide | > 30 | Values 17-30 overlap US range |
| Albumin | g/L | g/dL | 10 | divide | > 60 | Values <60 may be US |
| Phosphorus | mmol/L | mg/dL | 3.097 | multiply | < 3.0 | SI values are small |
| Creatinine | μmol/L | mg/dL | 88.4 | divide | > 20 | Standard renal conversion |
| Glucose | mmol/L | mg/dL | 18.0 | multiply | < 3.0 | Values 3-50 may be US |
| Magnesium | mmol/L | mg/dL | 2.43 | multiply | < 1.0 | SI values are small |

### No Conversion Needed
- Tacrolimus (ng/mL standard)
- Potassium (mEq/L = mmol/L)
- AST, ALT (U/L standard)

## Multi-File Join Pattern

```python
import csv
from pathlib import Path

# Read both files
with open(chem_path, newline="") as f:
    chem_rows = {row["patient_code"]: row for row in csv.DictReader(f)}
with open(liver_path, newline="") as f:
    liver_rows = {row["patient_code"]: row for row in csv.DictReader(f)}

# Find common patients, sorted numerically
common_patients = sorted(
    set(chem_rows.keys()) & set(liver_rows.keys()),
    key=lambda x: int(x)
)

# Drop patients with any missing measurement
complete_patients = []
for pid in common_patients:
    chem_vals = chem_rows[pid]
    liver_vals = liver_rows[pid]
    # Check all measurement columns are present
    if all(chem_vals.get(c) for c in chem_cols) and all(liver_vals.get(c) for c in liver_cols):
        complete_patients.append(pid)
```

## Output Column Order

Preserve this order: chemistry columns first (excluding patient_code), then liver columns (excluding patient_code and visit_tag).

Example: `Tacrolimus,Creatinine,Magnesium,Potassium,Glucose,Bilirubin_Total,Albumin,AST,ALT,Phosphorus`

## Common Pitfalls

1. **Rounding output**: Verifier expects full-precision floats. Never use `f"{val:.2f}"`.
2. **Including identifiers**: Output must exclude `patient_code`, `visit_tag`, and other metadata columns.
3. **Missing join**: Processing files independently instead of joining on `patient_code`.
4. **Keeping incomplete patients**: Patient 9 in trace had missing Creatinine — must be dropped.
5. **Wrong Bilirubin threshold**: Using >50 instead of >30. Values 30-50 are ambiguous but >30 is safer for SI detection.