# Oncology Panel Unit Conversions

Extended conversion reference for oncology follow-up panels and tumor marker monitoring.

## Critical Conversions

| Analyte | SI Unit | US Unit | Conversion | Detection Rule | Plausible US Range |
|---------|---------|---------|------------|--------------|-------------------|
| Uric_Acid | μmol/L | mg/dL | SI ÷ 59.48 = US | > 20 → assume SI | 2.0–14.0 mg/dL |
| Creatinine | μmol/L | mg/dL | SI ÷ 88.42 = US | > 20 → assume SI | 0.5–15.0 mg/dL |
| Albumin | g/L | g/dL | SI ÷ 10 = US | > 10 → assume SI | 2.0–6.0 g/dL |
| Calcium | mmol/L | mg/dL | SI × 4 = US | < 5 → assume SI | 6.0–14.0 mg/dL |
| Phosphorus | mmol/L | mg/dL | SI × 3.1 = US | < 3 → assume SI | 2.0–9.0 mg/dL |
| Glucose | mmol/L | mg/dL | SI × 18 = US | < 30 → assume SI | 20–600 mg/dL |
| Magnesium | mmol/L | mg/dL | SI × 2.43 = US | < 2 → assume SI | 1.0–5.0 mg/dL |
| Potassium | mmol/L | mEq/L | 1:1 | — | 2.5–7.0 mEq/L |
| LDH | U/L | U/L | No conversion | — | 100–1000 U/L |
| WBC_Count | ×10⁹/L | ×10³/μL (K/μL) | 1:1 (both common) | — | 3.0–40.0 K/μL |

## Uric Acid: Critical Factor

**Uric Acid uses a unique conversion factor**: 59.48 (not 16.81 or other common factors).

- **MW uric acid**: 168.11 g/mol
- **SI to US**: μmol/L ÷ 59.48 = mg/dL
- **Example**: 512.17 μmol/L ÷ 59.48 = 8.61 mg/dL

Common error: Using creatinine factor (88.4) or direct MW division.

## Panel-Specific Patterns

### Oncology Follow-up Data Structure
- **case_id**: Patient identifier (C1, C2, etc.)
- **draw_order**: Temporal sequence (1, 2, 3...) per case
- **Multiple rows per case**: Must select one row per case
- **Selection rule**: Highest draw_order with complete data (no NaN)

### Dedup Logic
```python
def select_complete_cases(df, id_col='case_id', order_col='draw_order'):
    """Select highest draw_order with complete data per case."""
    # Sort by case_id and draw_order descending
    df_sorted = df.sort_values([id_col, order_col], ascending=[True, False])
    
    # Drop rows with any NaN in measurement columns
    measurement_cols = [c for c in df.columns if c not in [id_col, order_col]]
    df_complete = df.dropna(subset=measurement_cols)
    
    # Take first (highest draw_order) per case_id
    return df_complete.groupby(id_col, sort=False).first()
```

## Pathological Value Handling

Oncology patients often have abnormal values—do NOT reject outliers:

| Analyte | Normal Range | Pathological Seen |
|---------|--------------|-------------------|
| Uric Acid | 3.5–7.0 mg/dL | 15+ mg/dL (tumor lysis) |
| Calcium | 8.5–10.5 mg/dL | 14+ mg/dL (hypercalcemia of malignancy) |
| Creatinine | 0.6–1.2 mg/dL | 10+ mg/dL (renal failure) |
| WBC Count | 4.5–11 K/μL | 100+ K/μL (leukemia) |

## Verification Ranges (US Conventional)

After conversion, check plausibility:

| Analyte | Implausible Low | Implausible High | Notes |
|---------|-----------------|------------------|-------|
| Uric_Acid | < 1.0 mg/dL | > 20 mg/dL | Tumor lysis can reach 15-20 |
| Creatinine | < 0.3 mg/dL | > 20 mg/dL | Dialysis patients common |
| Albumin | < 1.0 g/dL | > 6.0 g/dL | Malnutrition vs dehydration |
| Calcium | < 5.0 mg/dL | > 16.0 mg/dL | Hypercalcemia of malignancy |
| Phosphorus | < 1.0 mg/dL | > 12.0 mg/dL | Tumor lysis syndrome |
| Glucose | < 20 mg/dL | > 1000 mg/dL | Steroid-induced hyperglycemia |
| LDH | < 50 U/L | > 5000 U/L | Lymphoma can be 2000+ |
| WBC_Count | < 1.0 K/μL | > 200 K/μL | AML blast crisis |

## Output Requirements

Typical oncology panel output constraints:
- **No identifier columns**: Remove case_id, draw_order, patient_id
- **Fixed decimal places**: Exactly 2 decimal places for all values
- **No scientific notation**: Force decimal format
- **Preserve column order**: Match input or template exactly
- **String formatting required**: `f"{val:.2f}"` not `round(val, 2)`

### String Formatting Pattern
```python
# WRONG - loses trailing zeros
output = str(round(val, 2))  # 2.6 → "2.6"

# CORRECT - preserves 2 decimals
output = f"{val:.2f}"  # 2.6 → "2.60"
```
