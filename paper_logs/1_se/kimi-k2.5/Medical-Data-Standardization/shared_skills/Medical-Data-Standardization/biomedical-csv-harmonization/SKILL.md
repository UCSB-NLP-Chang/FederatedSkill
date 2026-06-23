---
name: biomedical-csv-harmonization
description: Harmonize messy biomedical data with mixed number formats, SI/US unit detection, deduplication logic, and strict output formatting. Use when processing lab results, clinical panels, or scientific data from CSV, JSON, or nested formats with European decimal commas, scientific notation, unit conversions required, or duplicate records per subject. Critical for hepatic panels, thyroid panels, cardiology panels (BNP, troponins), metabolic panels, respiratory/blood gas panels (kPa↔mmHg), oncology follow-up panels, ICU multi-source data, transplant monitoring panels (Tacrolimus + organ function), neonatal sepsis panels (different ranges), and any data where values may be pathological or outside normal ranges.
---

# Biomedical CSV Harmonization

Clean and standardize biomedical data with mixed formatting, unit detection, conversion requirements, and deduplication.

## When to use
- **Input format**: CSV, JSON with nested measurements, or similar structured lab data
- Comma decimal separators (e.g., `142,0205` for `142.0205`)
- Scientific notation mixed with fixed decimals (e.g., `3.7648e+00`, `6.4372e+02`)
- SI to US conventional unit conversions needed (mmol/L↔mg/dL, μmol/L↔mg/dL, pmol/L↔ng/dL, ng/L↔ng/mL, **kPa↔mmHg**)
- Strict output formatting required (fixed decimal places, no scientific notation)
- Missing value handling required (drop rows with NaN)
- **Multi-file join**: Multiple CSVs linked by common ID (e.g., `record_id`) that must be merged
- **Deduplication needed**: Multiple rows per subject (case_id) with draw_order or timestamp
- **Status filtering**: Records marked "final" vs "draft" or similar status fields
- **Hepatic/liver panels**: see `references/hepatic-panel-conversions.md`
- **Thyroid panels**: see `references/thyroid-panel-conversions.md` — TSH, Free_T4, Free_T3, Total_T4, Total_T3, Anti_TPO, Thyroglobulin, Calcitonin
- **Cardiology panels**: see `references/cardiology-panel-conversions.md` — BNP, NT-proBNP, Troponin I/T, creatinine, magnesium
- **Respiratory/blood gas panels**: see `references/respiratory-panel-conversions.md` — pCO2, pO2, pH with **critical kPa↔mmHg detection**
- **Oncology panels**: see `references/oncology-panel-conversions.md` — Uric Acid (critical: ÷59.48), deduplication by highest complete draw_order
- **Transplant monitoring panels**: see `references/transplant-panel-conversions.md` — Tacrolimus levels (NO conversion), combined chemistry + organ function, strict column ordering
- **Neonatal sepsis panels**: see `references/neonatal-panel-conversions.md` — **CRP already in mg/L, Hemoglobin g/L→g/dL ÷10 (not mmol/L conversion), Lactate ×9.008, different plausibility ranges**

## Core Workflow

1. **Inspect raw data first** — Look at actual string values before parsing. Numbers like `142,0205` look like CSV fields but are European decimals; `12,4787` is a decimal, not a separator.

2. **Status filter (JSON/XML panels)**: If data has `status` field, keep only `"final"` records, drop `"draft"` or preliminary.

3. **Multi-file join (if applicable)**:
   - Identify common join key (typically `record_id`, `case_id`, `patient_id`)
   - Read all files as strings first to preserve original formatting
   - Validate join key exists in all files before merging
   - **Check completeness in ALL files** — exclude patients missing data in any source file
   - Use inner join to keep only complete records
   - Preserve column order: main file columns first, then additional file columns

4. **Parse with explicit handling**:
   - Replace comma decimals: `val.replace(',', '.')` before numeric conversion
   - Handle scientific notation: Python's `float()` handles `e+00` automatically after comma fix
   - Validate: check for remaining non-numeric characters after cleaning

5. **Deduplication (if multiple rows per subject)**:
   - Identify subject key: typically `case_id`, `patient_id`, or `subject_id`
   - Identify ordering column: `draw_order`, `visit_number`, `timestamp`
   - Select highest order with **complete data** (no NaN in measurement columns)
   - See `references/oncology-panel-conversions.md` for pattern

6. **Unit Detection Heuristics** (apply before conversion):

   | Lab Value | SI Range (typical) | US Range (typical) | Conversion |
   |-----------|-------------------|-------------------|------------|
   | Calcium | 2.1–2.6 mmol/L | 8.4–10.4 mg/dL | × 4 (mmol/L → mg/dL) |
   | Glucose | 3.9–6.1 mmol/L | 70–110 mg/dL | × 18 (mmol/L → mg/dL) |
   | Creatinine | 44–106 μmol/L | 0.5–1.2 mg/dL | ÷ 88.42 (μmol/L → mg/dL) |
   | BNP | ~5–100 pmol/L | ~5–100 pg/mL | × 0.289 (pmol/L → pg/mL) |
   | Troponin I | 0–50 ng/L | 0–0.05 ng/mL | ÷ 1000 (ng/L → ng/mL) |
   | Uric Acid | ~200–400 μmol/L | ~3–7 mg/dL | **÷ 59.48** (μmol/L → mg/dL) |
   | **pCO2** | **4.7–6.0 kPa** | **35–45 mmHg** | **× 7.5** (kPa → mmHg) |
   | **pO2** | **10–13 kPa** | **75–100 mmHg** | **× 7.5** (kPa → mmHg) |
   | **Tacrolimus** | **ng/mL** | **ng/mL** | **NO CONVERSION** |
   | **CRP** | **mg/L** | **mg/L** | **NO CONVERSION** (same unit) |
   | **Hemoglobin (neonatal)** | **g/L** | **g/dL** | **÷ 10** (NOT mmol/L conversion) |
   | **Lactate** | **mmol/L** | **mg/dL** | **× 9.008** (MW-based, not ×9) |
   
   **Blood gas detection**: pCO2 < 20 or pO2 < 30 → assume kPa and convert. See `references/respiratory-panel-conversions.md`.
   
   **Immunosuppressant detection**: Tacrolimus, Cyclosporine, Sirolimus levels are always in ng/mL — do not apply metabolic conversions.
   
   **Neonatal CRP**: Already in mg/L — no conversion needed. Values 300+ are sepsis, not "already converted."
   
   **Detection rule**: If value < plausible US minimum, assume SI and convert. For cardiac markers where SI is smaller (pmol/L), if value > threshold assume SI.

7. **Apply conversions with PLAUSIBILITY CHECKING** — This is the critical step:
   - **First check: Is value already in target units?** If value is in plausible US range, DO NOT convert
   - **BUT: Check SI conversion FIRST for values that look like they could be SI** — This prevents unconverted SI values passing through
   - After any conversion, immediately verify the result falls in physiologically plausible range
   - If converted value is implausible, **invert the operation** (multiply↔divide) and recheck
   - **Immunosuppressants**: Skip conversion entirely — verify only that values are in therapeutic range
   - **Neonatal panels**: Use neonatal plausibility ranges, not adult — see `references/neonatal-panel-conversions.md`
   - See per-analyte reference for plausible ranges

8. **Extended conversions**: 
   - Hepatic panels: see `references/hepatic-panel-conversions.md`
   - Thyroid panels: see `references/thyroid-panel-conversions.md`
   - Cardiology panels: see `references/cardiology-panel-conversions.md`
   - **Respiratory/blood gas: see `references/respiratory-panel-conversions.md`** — critical for kPa↔mmHg
   - **Transplant panels: see `references/transplant-panel-conversions.md`** — critical for Tacrolimus handling and column ordering
   - **Oncology panels: see `references/oncology-panel-conversions.md`**
   - **Neonatal sepsis: see `references/neonatal-panel-conversions.md`** — critical for CRP, hemoglobin, lactate

9. **Force output format** — Use string formatting to ensure exactly N decimal places: `f"{val:.2f}"` then write as text, not floats. Pandas `to_csv()` may truncate trailing zeros; use manual string output for strict formatting.

10. **Verification steps**:
    - Check no scientific notation in output: `re.search(r'[eE][+-]\\d+', text)` should be None
    - Check decimal places: split on '.' and verify len(decimal_part) == 2
    - Check no missing values: `df.isnull().sum().sum() == 0`
    - **Validate converted values**: After unit conversion, verify values fall in physiologically plausible ranges (see references for per-analyte ranges)
    - **Use correct reference ranges** — neonatal panels need neonatal ranges, not adult
    - **Verify deduplication**: Confirm one row per subject, highest complete order selected
    - **Verify multi-file join**: Confirm expected row count, no duplicate columns from merge suffixes
    - **Blood gas specific**: pCO2 in 10–150 mmHg, pO2 in 20–600 mmHg after conversion
    - **Verify column order**: Match specification exactly — some panels require chemistry first, then organ-specific markers

## Critical Decision: Conversion Direction

**ALWAYS check if value is already in target units BEFORE converting, BUT prioritize SI detection when value could be either:**

```python
# WRONG: Converting without checking if already converted
def convert_glucose(val):
    if val < 20:  # Detection threshold
        return val * 18  # But what if val=100 (already mg/dL)?
    return val  # Returns 100, but we never checked if conversion needed

# CORRECT: Check plausible range first, but try SI conversion if borderline
def convert_glucose_safe(val):
    us_range = (20, 600)  # Plausible mg/dL range
    si_range = (1, 33)    # Plausible mmol/L range
    
    # Could be SI? Convert and validate
    if val < 30:  # Could be SI mmol/L
        converted = val * 18
        if us_range[0] <= converted <= us_range[1]:
            return converted
    
    # Already in target units?
    if us_range[0] <= val <= us_range[1]:
        return val
    
    # In SI units?
    if si_range[0] <= val <= si_range[1]:
        converted = val * 18
        if us_range[0] <= converted <= us_range[1]:
            return converted
    return val  # Unknown or pathological
```

**Immunosuppressants (Tacrolimus, Cyclosporine)**: These are always in ng/mL. Do NOT apply metabolic conversions.

**CRP**: Always in mg/L. The column name `CRP_mg_L_or_mg_dL` is misleading — mg/dL CRP would be implausibly low (0.1–5).

**Blood gas specific** (pCO2/pO2): Values < 20 (pCO2) or < 30 (pO2) are almost certainly kPa. But verify: 10 kPa × 7.5 = 75 mmHg (normal), not 10 mmHg (incompatible with life).

**Neonatal Hemoglobin**: Input is typically g/L, not mmol/L. Divide by 10, not 1.613.

**Plausible ranges for common ICU/metabolic panel values (US conventional):**
| Analyte | Plausible US Range | SI → US Conversion |
|---------|-------------------|-------------------|
| Sodium | 120–160 mEq/L | None (1:1) |
| Potassium | 2.5–7.0 mEq/L | None (1:1) |
| Chloride | 80–130 mEq/L | None (1:1) |
| Bicarbonate | 5–45 mEq/L | None (1:1) |
| Glucose | 20–600 mg/dL | mmol/L × 18 |
| Calcium | 5–15 mg/dL | mmol/L × 4 |
| Magnesium | 1.0–5.0 mg/dL | mmol/L × 2.43 |
| Phosphorus | 1.0–12.0 mg/dL | mmol/L × 3.1 |
| Creatinine | 0.3–20.0 mg/dL | μmol/L ÷ 88.42 |
| BUN | 3–150 mg/dL | mmol/L × 2.8 |
| **pCO2** | **10–150 mmHg** | **kPa × 7.5** |
| **pO2** | **20–600 mmHg** | **kPa × 7.5** |
| **Tacrolimus** | **3–30 ng/mL** | **None** |
| **CRP** | **0–500 mg/L** | **None (already mg/L)** |
| **Lactate** | **5–100 mg/dL** | **mmol/L × 9.008** |
| **Hemoglobin (neonatal)** | **10–25 g/dL** | **g/L ÷ 10** |

**Common pitfall — Already converted data**: Input values like `126.13` for Sodium, `7.56` for Calcium, `164.73` for Glucose are ALREADY in US conventional units. Converting again produces impossible values.

**Correct verification pattern from failed runs**:
- Ferritin: pmol/L ÷ 2.247 = μg/L (not multiply)
- PTH: pmol/L ÷ 9.43 = pg/mL (not multiply)  
- Free T4: pmol/L ÷ 12.87 = ng/dL (not multiply)
- Hemoglobin (adult): mmol/L ÷ 1.613 = g/dL (not multiply)
- Hemoglobin (neonatal): g/L ÷ 10 = g/dL (not mmol/L conversion)
- BNP: pmol/L × 0.289 = pg/mL (not divide)
- Troponin I/T: ng/L ÷ 1000 = ng/mL (not multiply)
- Uric Acid: μmol/L ÷ 59.48 = mg/dL (not other factors)
- **pCO2/pO2: kPa × 7.5 = mmHg (not divide, and detect by low value)**
- **Tacrolimus: NO conversion** — already ng/mL
- **CRP: NO conversion** — already mg/L
- **Lactate: mmol/L × 9.008 = mg/dL (not ×9)**

## Multi-File Join Pattern

When data is split across multiple CSVs:

```python
import pandas as pd

# Read as strings to preserve formatting
df_main = pd.read_csv('main.csv', dtype=str)
df_add = pd.read_csv('additional.csv', dtype=str)

# Verify join key exists
join_key = 'record_id'
assert join_key in df_main.columns and join_key in df_add.columns

# Merge (inner join - keep only records present in both)
df_merged = df_main.merge(df_add, on=join_key, how='inner')

# Verify completeness in BOTH files before finalizing
df_merged = df_merged.dropna()  # Drop any row with missing in either source

# Drop join key from output
df_output = df_merged.drop(columns=[join_key])
```

## JSON/Nested Data Pattern

For JSON with nested measurements (common in respiratory panels):

```python
import json

def flatten_panel(panel):
    """Flatten nested acid_base/metabolic structure."""
    flat = {}
    for category in panel.get('measurements', {}).values():
        flat.update(category)
    return flat

with open('data.json') as f:
    data = json.load(f)

records = [flatten_panel(p) for p in data['panels'] 
           if p.get('status') == 'final']  # Filter status
```

## Deduplication Pattern

When data has multiple rows per subject:

```python
def harmonize_with_dedup(df, id_col='case_id', order_col='draw_order', 
                         measurement_cols=None):
    """
    Select highest complete draw_order per case.
    Complete = no NaN in measurement columns.
    """
    if measurement_cols is None:
        measurement_cols = [c for c in df.columns 
                          if c not in [id_col, order_col]]
    
    # Sort by case_id asc, draw_order desc
    df = df.sort_values([id_col, order_col], 
                       ascending=[True, False])
    
    # Keep only rows with complete measurements
    df = df.dropna(subset=measurement_cols)
    
    # Take first per group (highest draw_order due to sort)
    result = df.groupby(id_col, sort=False).first()
    
    # Drop identifier columns from output
    result = result[measurement_cols]
    
    return result
```

## Anti-patterns

- **Don't trust pandas auto-parsing** for decimal commas — it interprets `142,0205` as string or two fields, not `142.0205`
- **Don't convert without checking if already in target units** — Verify value is in SI range, not just outside US "normal" range
- **Don't use "normal range" for detection in pathological data** — Hepatic panels often have abnormal values; use absolute thresholds
- **Don't assume all columns need same conversion** — Calcium and Glucose have different conversion factors; BNP and troponins have opposite direction conventions
- **Don't convert immunosuppressant drug levels** — Tacrolimus, Cyclosporine, Sirolimus are already in ng/mL
- **Don't convert CRP** — Already in mg/L in both SI and US
- **Don't use approximate factors** — Lactate needs ×9.008, not ×9
- **Don't use float formatting alone** — `round(val, 2)` then `to_csv()` loses trailing zeros; format as strings
- **Don't drop columns early** — Preserve column order; only drop identifier columns explicitly specified
- **Don't multiply when you should divide** — **Always verify converted values are physiologically plausible immediately after conversion**
- **Don't trust conversion factors without units** — "× 12.87" means nothing without knowing which unit is larger
- **Don't ignore template files** — If a template is provided, read it first to preserve exact column order and headers
- **Don't select first row per subject** — Select highest complete draw_order, not just any row
- **Don't drop NaN before sorting** — Missing values in lower draw_orders are OK if higher draw_order is complete
- **Don't assume merge succeeded** — Verify row count after join matches expectation
- **Don't confuse pCO2/pO2 units** — 10 kPa → 75 mmHg (normal); 10 mmHg → incompatible with life. Detect by magnitude.
- **Don't include incomplete patients from multi-file joins** — Patient must have complete data in ALL source files
- **Don't use adult ranges for neonatal panels** — CRP 300+ is sepsis (correct), not "already converted"; hemoglobin 14–24 g/dL normal
- **Don't apply mmol/L→g/dL conversion to neonatal hemoglobin** — Use g/L→g/dL ÷10

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Output has `125.3` not `125.30` | Float formatting, not string | Use `f"{val:.2f}"` and write as strings |
| Scientific notation in output | Large values not formatted | Force string format before write |
| Values 10× too small/large | Wrong unit assumption | Check detection thresholds; trace specific values |
| Values 100× too large after conversion | Multiplied instead of divided | Apply plausibility check; invert operation |
| Values 1000× too small (troponins) | Forgot  1000 for ng/L→ng/mL | See `references/cardiology-panel-conversions.md` |
| Wrong row count after join | Missing keys or outer join | Use inner join; verify keys exist in all files |
| Duplicate columns (_x, _y suffixes) | Key collision in merge | Pre-drop duplicate columns before merge |
| Converted values exceed physiologic limits | Wrong conversion direction OR already converted | Verify division vs multiplication; check if already in US units |
| Implausible hormone values (e.g., Free T4 > 10) | Forgot thyroid hormones use division | See `references/thyroid-panel-conversions.md` |
| Implausible cardiac markers (e.g., BNP < 1) | Forgot cardiac markers use multiplication | See `references/cardiology-panel-conversions.md` |
| **pCO2/pO2 < 15 after conversion** | Treated kPa as mmHg or wrong factor | Multiply by 7.5; verify 75-100 mmHg normal |
| **pCO2/pO2 > 600** | Converted mmHg as if kPa | Check detection: values >30 pO2, >20 pCO2 are likely mmHg already |
| **Tacrolimus values 100× too small** | Applied metabolic conversion to drug level | Do NOT convert — Tacrolimus is already ng/mL |
| **CRP values not matching reference** | Tried to convert mg/L | CRP is already mg/L — no conversion needed |
| **Lactate slightly off** | Used ×9 instead of ×9.008 | Use exact molecular weight factor |
| **Hemoglobin impossibly high (60+ g/dL)** | Treated g/L as mmol/L | Neonatal: g/L ÷ 10 = g/dL |
| Column order doesn't match requirements | Ignored template file or wrong merge order | Read template first, preserve exact header order |
| Missing patients after multi-file join | Dropped incomplete patients too late | Check completeness BEFORE merge, exclude incomplete |
| Duplicate subjects in output | Wrong dedup logic | Use highest complete draw_order, not first() only |
| Missing subjects | NaN dropped before dedup | Drop NaN after selecting complete rows, not before |
| Uric Acid ~3× too small/large | Used wrong factor | Use 59.48, not ÷16.81 or other | See `references/oncology-panel-conversions.md` |
| Glucose/Ca already in mg/dL but converted | Detection threshold too high | Check plausible US range first; values 100-400 mg/dL are normal |
| Draft records in output | Forgot status filter | Keep only `status == "final"` for JSON panels |
| Neonatal values flagged as errors | Used adult plausibility ranges | See `references/neonatal-panel-conversions.md` |

## Fallback if verification fails

If strict formatting fails:
1. Write intermediate to string buffer: `df.to_csv(buf, index=False)`
2. Post-process with regex: `re.sub(r'(\\d+\\.\\d)(?![0-9])', r'\\1\\0', line)` for single decimal
3. Or use `csv` module with explicit string conversion

## References

- `references/unit-conversion-reference.md` — Standard conversions for common analytes
- `references/hepatic-panel-conversions.md` — Extended reference for liver function tests with pathological value handling
- `references/thyroid-panel-conversions.md` — Extended reference for thyroid hormones including TSH, Free/Total T4/T3, anti-TPO, thyroglobulin with correct conversion direction and plausibility ranges
- `references/cardiology-panel-conversions.md` — Extended reference for cardiac biomarkers (BNP, NT-proBNP, troponins), electrolytes in cardiology context, and template-based output workflows
- `references/respiratory-panel-conversions.md` — **Extended reference for blood gases (pCO2, pO2) with critical kPa↔mmHg detection, JSON nested data handling, and status filtering**
- `references/oncology-panel-conversions.md` — Extended reference for oncology panels including Uric Acid conversion (critical: ÷59.48), deduplication patterns, and tumor lysis syndrome value handling
- `references/transplant-panel-conversions.md` — Extended reference for transplant monitoring panels including Tacrolimus levels (no conversion), combined chemistry + organ function markers, and column ordering requirements
- `references/neonatal-panel-conversions.md` — **Extended reference for neonatal sepsis panels including CRP (no conversion), hemoglobin (g/L→g/dL), lactate (×9.008), and neonatal-specific plausibility ranges**

## Example Pattern

```python
import pandas as pd
import re
import json

# JSON with nested measurements example
with open(input_path) as f:
    data = json.load(f)

# Flatten and filter status
records = []
for panel in data['panels']:
    if panel.get('status') != 'final':
        continue
    flat = {'sample_id': panel['sample_id']}
    for category in panel.get('measurements', {}).values():
        flat.update(category)
    records.append(flat)

df = pd.DataFrame(records)

def parse_european(val):
    if pd.isna(val) or val in ('', 'nan', 'NaN', None):
        return None
    cleaned = str(val).replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return None

# Apply parsing
for col in numeric_cols:
    df[col] = df[col].apply(parse_european)

# Deduplication: highest complete draw_order per case_id
df = df.sort_values(['case_id', 'draw_order'], ascending=[True, False])
measurement_cols = [c for c in df.columns if c not in ['case_id', 'draw_order']]
df = df.dropna(subset=measurement_cols)
df = df.groupby('case_id', sort=False).first()
df = df[measurement_cols]  # Drop identifiers from output

# Convert SI to US with plausibility verification (example: pCO2)
def convert_pco2(val):
    if val is None:
        return None
    # kPa detection: < 20
    if val < 20:
        converted = val * 7.50062
        if 10 <= converted <= 150:
            return converted
    # Already mmHg?
    if 10 <= val <= 150:
        return val
    return val

df['pCO2_Arterial'] = df['pCO2_Arterial'].apply(convert_pco2)

# Format to exactly 2 decimals as strings
output_lines = [','.join(df.columns)]
for _, row in df.iterrows():
    output_lines.append(','.join(f"{v:.2f}" for v in row))

with open(output_path, 'w') as f:
    f.write('\\n'.join(output_lines))
```
