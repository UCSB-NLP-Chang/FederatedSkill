# ICU Metabolic Panel Reference

Extended reference for ICU metabolic panel harmonization with multi-source data files.

## Data Structure

Typical ICU metabolic panel consists of:
- **Main file**: Core electrolytes and metabolic markers
- **Additional file**: Extended renal, acid-base, and ketone markers
- **Common join key**: `record_id` (integer or string)

### Main File Columns
| Column | Unit (US) | Conversion | Plausible Range | Notes |
|--------|-----------|------------|-----------------|-------|
| Sodium | mEq/L | None | 120–160 | 1:1 with mmol/L |
| Potassium | mEq/L | None | 2.5–7.0 | 1:1 with mmol/L |
| Chloride | mEq/L | None | 80–130 | 1:1 with mmol/L |
| Bicarbonate | mEq/L | None | 5–45 | 1:1 with mmol/L |
| Glucose | mg/dL | ×18 (if mmol/L) | 20–600 | Check if already mg/dL |
| Lactate | mmol/L | None | 0.3–20 | Often same units |
| Calcium | mg/dL | ×4 (if mmol/L) | 5–15 | Check if already mg/dL |
| Magnesium | mg/dL | ×2.43 (if mmol/L) | 1.0–5.0 | Check if already mg/dL |
| Phosphorus | mg/dL | ×3.1 (if mmol/L) | 1.0–12.0 | Check if already mg/dL |

### Additional File Columns
| Column | Unit (US) | Conversion | Plausible Range | Notes |
|--------|-----------|------------|-----------------|-------|
| Creatinine | mg/dL | ÷88.42 (if μmol/L) | 0.3–20 | Check if already mg/dL |
| BUN | mg/dL | ×2.8 (if mmol/L) | 3–150 | Check if already mg/dL |
| Anion_Gap | mEq/L | None | 5–40 | Calculated value |
| Osmolality | mOsm/kg | None | 220–400 | |
| Beta_Hydroxybutyrate | mmol/L or mg/dL | Variable | 0–20 | Check units carefully |
| pH_Arterial | unitless | None | 6.8–7.8 | |
| pCO2_Arterial | mmHg | None | 20–100 | May be in kPa (×7.5) |

## Critical Detection Rules

### Electrolytes (Na, K, Cl, HCO3)
- **NO conversion needed**: mEq/L = mmol/L
- Values like `126.13`, `3.58`, `89.34` are already correct
- Detection: If value > 50 for Na, > 1 for K, assume already US conventional

### Glucose
- **Common error**: Converting mg/dL values as if mmol/L
- **Detection**: 
  - mmol/L range: 3–33 (fasting 3.9–6.1)
  - mg/dL range: 70–110 (fasting), up to 600+ (severe hyperglycemia)
  - If value > 30, almost certainly mg/dL
- **Example**: `164.73` is mg/dL (normal-high), NOT 164.73 mmol/L (impossibly high)

### Calcium
- **Common error**: Converting mg/dL values as if mmol/L
- **Detection**:
  - mmol/L range: 2.1–2.6 (normal)
  - mg/dL range: 8.4–10.4 (normal)
  - If value > 5, almost certainly mg/dL
- **Example**: `7.56` is mg/dL (low-normal), NOT 7.56 mmol/L (impossibly high)

### Creatinine
- **SI (μmol/L)**: 44–106 normal, up to 1000+ (renal failure)
- **US (mg/dL)**: 0.5–1.2 normal, up to 10+ (renal failure)
- **Detection**: If value > 20, assume μmol/L (SI) and convert
- **Example**: `1274.9979` → 1274.9979 ÷ 88.42 = 14.42 mg/dL
- **Example**: `14.76` → already mg/dL (elevated but plausible)

## Multi-File Join Verification

After joining main and additional files:

```python
# Expected: same number of rows as each input (inner join)
# If main has 12 rows and additional has 12 rows with matching IDs:
#   → merged should have 12 rows (or fewer if some IDs missing in one file)

# Verify no duplicate columns
assert not any('_x' in c or '_y' in c for c in df_merged.columns), \
    "Merge collision detected"

# Verify expected column order
expected_order = [
    'Sodium', 'Potassium', 'Chloride', 'Bicarbonate', 'Glucose',
    'Lactate', 'Calcium', 'Magnesium', 'Phosphorus',
    'Creatinine', 'BUN', 'Anion_Gap', 'Osmolality',
    'Beta_Hydroxybutyrate', 'pH_Arterial', 'pCO2_Arterial'
]
assert list(df_output.columns) == expected_order, "Column order mismatch"
```

## Missing Value Handling

ICU panels often have incomplete records:
- **Strategy**: Drop rows with ANY missing measurement values
- **Rationale**: Partial data is not useful for metabolic panel analysis
- **Verification**: After drop, `df.isnull().sum().sum() == 0`

## Output Verification Checklist

- [ ] No `record_id` or other join key in output
- [ ] Exactly 16 measurement columns
- [ ] All values formatted to exactly 2 decimal places
- [ ] No scientific notation
- [ ] No European decimal commas remaining
- [ ] No missing values (NaN)
- [ ] Column order matches specification
- [ ] Row count equals complete cases after join and drop

## Common ICU Panel Pitfalls

### Pitfall 1: Converting already-converted values
```python
# WRONG: Glucose 164.73 looks like it could be mmol/L (high but possible)
# So we multiply × 18 → 2965 mg/dL (impossibly high, diabetic ketoacidosis max ~800)
glucose_converted = 164.73 * 18  # WRONG!

# CORRECT: 164.73 is already mg/dL (moderately elevated fasting)
# Check: Is 164.73 in plausible mg/dL range (20-600)? YES → no conversion
```

### Pitfall 2: Creatinine unit confusion
```python
# Input: 1274.9979
# Could be: 1274.9979 μmol/L (SI) → 14.42 mg/dL (elevated, AKI)
# Or: 1274.9979 mg/dL (impossibly high)
# Detection: 1274 > 20 threshold → convert: 1274.9979 ÷ 88.42 = 14.42 mg/dL

# Input: 14.7598
# Could be: 14.7598 μmol/L (SI) → 0.17 mg/dL (impossibly low)
# Or: 14.7598 mg/dL (elevated, plausible)
# Detection: 14.76 is in plausible mg/dL range → no conversion
```

### Pitfall 3: pCO2 unit confusion
```python
# pCO2 may be in kPa (common in international labs)
# kPa → mmHg: multiply by 7.5
# Example: 5.2 kPa → 39 mmHg (normal)
# Detection: If pCO2 < 15, likely kPa and needs conversion
```
