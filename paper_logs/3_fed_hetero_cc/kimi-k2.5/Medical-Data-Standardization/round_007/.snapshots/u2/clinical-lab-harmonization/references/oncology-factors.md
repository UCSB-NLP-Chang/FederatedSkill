# Oncology Follow-Up Panel Conversion Factors

## Panel Analytes

| Analyte | SI Unit | US Unit | Factor | Operation | Threshold | Notes |
|---------|---------|---------|--------|-----------|-----------|-------|
| LDH | U/L | U/L | 1 | none | — | Same units, NO conversion |
| Uric_Acid | μmol/L | mg/dL | 59.48 | divide | > 20 | MW 168.11 g/mol |
| Creatinine | μmol/L | mg/dL | 88.4 | divide | > 20 | Standard conversion |
| Phosphorus | mmol/L | mg/dL | 3.097 | multiply | < 3.0 | SI values are SMALL |
| Calcium | mmol/L | mg/dL | 4.0 | multiply | 1.5–4.0 | Mid-range detection |
| Albumin | g/L | g/dL | 10 | divide | > 60 | Decimal shift |
| Glucose | mmol/L | mg/dL | 18.0 | multiply | < 3.0 | CRITICAL: only <3.0 |
| Magnesium | mmol/L | mg/dL | 2.43 | multiply | < 1.0 | SI values are SMALL |
| Potassium | mmol/L | mEq/L | 1 | none | — | Same units, NO conversion |
| WBC_Count | ×10⁹/L | ×10³/μL | 1 | none | — | Same scale, NO conversion |

## Uric Acid Conversion Derivation

- Uric acid MW: 168.11 g/mol
- 1 μmol/L × 168.11 g/mol ÷ 10⁶ μmol/mol ÷ 10 dL/L × 10³ mg/g = 0.01681 mg/dL
- So: mg/dL = μmol/L ÷ 59.48
- US normal range: 2.5-7.0 mg/dL (men), 1.5-6.0 mg/dL (women)
- SI normal range: 150-420 μmol/L (men), 90-360 μmol/L (women)
- Threshold: >20 clearly μmol/L (would give 0.34 mg/dL after conversion, which is very low but possible)
- Values 2-15 are clearly US mg/dL
- Values 15-20 are ambiguous but default to US

## Deduplication Workflow

When input has `case_id` and `draw_order` columns:

1. Group all rows by `case_id`
2. Sort each group by `draw_order` descending
3. Select the first row (highest draw_order) where ALL measurement columns are non-missing
4. If highest draw_order has missing values, try next highest
5. Remove `case_id` and `draw_order` from output columns
6. Output one row per case

```python
def select_best_row(group, measurement_cols):
    """Select highest draw_order with complete data."""
    group = group.sort_values('draw_order', ascending=False)
    for _, row in group.iterrows():
        if all(pd.notna(row[col]) for col in measurement_cols):
            return row
    return group.iloc[0]  # fallback to highest draw_order even if incomplete
```

## Comma Parsing for Oncology Panels

Oncology data frequently uses comma as decimal separator (European format):
- `"615,1100"` → `615.1100` (comma is decimal)
- `"10,6577"` → `10.6577` (comma is decimal)
- `"2,2160"` → `2.2160` (comma is decimal)
- `"3,2591"` → `3.2591` (comma is decimal)

**Rule**: If the value is quoted and contains a single comma with no dot, the comma is a decimal separator.

**Do NOT** blindly replace all commas with dots — this works for comma-decimal values but destroys thousand-separated values.

## Common Oncology Panel Errors

| Error | Manifestation | Fix |
|-------|--------------|-----|
| Rounding to 2 decimals | 615.11 instead of 615.1100 | NEVER round — full precision |
| Uric_Acid wrong direction | 512 μmol/L × 59.48 = 30457 | Divide by 59.48, not multiply |
| Phosphorus wrong direction | 3.26 mmol/L ÷ 3.097 = 1.05 | Multiply by 3.097, not divide |
| Magnesium wrong threshold | Converting values 1.5-4 | Only convert <1.0 |
| Glucose wrong threshold | Converting value 31.5 mg/dL | Only convert <3.0; 31.5 is US |
| Comma parsing | "615,1100" → 6151100.0 | Parse as comma-decimal: 615.1100 |
| Plausible-range heuristic | Converting based on "is in US range?" | Use specific thresholds instead |
