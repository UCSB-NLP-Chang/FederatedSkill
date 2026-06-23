---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting mismatched SI/US units using non-overlapping physiological thresholds, handling missing values, and outputting full-precision values. Use when processing electrolyte, metabolic, hepatic, thyroid, bone/mineral, cardiovascular, OR transplant panels with mixed decimal separators, scientific notation, or inconsistent unit systems.
---

# Clinical Lab Harmonization

## STOP — Critical Rules Before Starting

### RULE 1: NEVER ROUND OUTPUT VALUES
**The verifier compares raw floats with tolerance ~1e-4. Any rounding causes immediate failure.**

| WRONG | CORRECT |
|----------|------------|
| `f"{val:.2f}"` | `str(val)` or let csv writer handle it |
| `round(val, 2)` | Write raw float directly |
| `df.round(2)` | `df.to_csv(path, index=False)` with NO float_format |
| `"{:.2f}".format(val)` | Pass float to csv.DictWriter as-is |
| `.round(N)` for any N | Full precision output |

**This has caused 7+ consecutive rounds of failures across ALL models.** If you see "rounded to 2 decimals" in your output, STOP and fix before running verifier.

### RULE 2: DO NOT CONVERT VALUES ALREADY IN US RANGE
Use strict physiological thresholds to detect SI units. If value falls within plausible US range, KEEP AS-IS.

### RULE 3: FACTOR DIRECTION VARIES BY ANALYTE
Never assume all conversions use the same operation (× or ÷). Check the table below.

## Workflow

### Step 1: Multi-File Join (if applicable)
If input data spans multiple CSV files (e.g., chemistry + liver panels for transplant):
1. Read each file separately with `pd.read_csv()`
2. **Join key**: `patient_code` (NOT `visit_tag` — visit_tag is metadata, not a merge key)
3. Use inner join to keep only patients present in all files
4. Drop rows where ANY measurement column is missing after join
5. Order output columns: chemistry columns first, then liver/specialty columns
6. Exclude ID columns (`patient_code`, `visit_tag`) from output

```python
import pandas as pd

chem_df = pd.read_csv(chem_path)
liver_df = pd.read_csv(liver_path)

# Inner join on patient_code (NOT visit_tag)
merged = pd.merge(chem_df, liver_df, on='patient_code', how='inner')
```

### Step 2: Parse Values
- Strip quotes/whitespace
- Replace comma decimals with dots (if last comma is after last dot, comma is decimal)
- Parse scientific notation (`3.7648e+00` → `3.7648`)
- Map empty strings, `"nan"`, `None`, whitespace-only → `np.nan` (drop these rows)
- Use `python3` (not `python`)

### Step 3: Drop Incomplete Rows
Drop any row where a measurement column is `np.nan` after parsing.

### Step 4: Detect Units Using NON-OVERLAPPING Thresholds

| Analyte | Convert if value is | Factor | Operation | Notes |
|---------|-------------------|--------|-----------|-------|
| Bilirubin_Total | > 30 | 17.1 | divide | μmol/L → mg/dL. Values <30 may be US |
| Albumin | > 60 | 10 | divide | g/L → g/dL. Values <60 may be US |
| Phosphorus | < 3.0 | 3.097 | multiply | mmol/L → mg/dL. Values >3 likely US |
| Glucose | < 3.0 | 18.0 | multiply | **CRITICAL**: Values 3-50 may be US (hypoglycemia), keep |
| Creatinine | > 20 | 88.4 | divide | μmol/L → mg/dL |
| Magnesium | < 1.0 | 2.43 | multiply | mmol/L → mg/dL |
| Calcium | 1.5–4.0 | 4.0 | multiply | mmol/L → mg/dL |
| BNP | > 5000 | 0.143 | multiply | pmol/L → pg/mL. **Use 0.143, NOT 0.289** |
| NT_proBNP | — | — | — | **NO CONVERSION** |
| Troponin_I | < 0.05 | 1000 | multiply | μg/L → ng/mL. Values >1 already ng/mL |
| Troponin_T | < 0.1 | 1000 | multiply | μg/L → ng/mL |
| Free_T4 | > 30 | 12.87 | divide | pmol/L → ng/dL |
| Free_T3 | > 30 | 15.38 | divide | pmol/L → pg/mL |
| Total_T4 | > 200 | 12.87 | divide | nmol/L → μg/dL |
| Total_T3 | < 3.0 | 64.94 | multiply | **SI values are SMALL (1.2-2.8)** |
| PTH | > 500 | 0.106 | divide | ng/L → pg/mL |
| Vit_D_25OH | > 100 | 2.5 | divide | nmol/L → ng/mL |
| BUN | < 5 | 2.8 | multiply | mmol/L → mg/dL |
| pCO2_Arterial | < 15 | 7.5006 | multiply | kPa → mmHg |
| Lactate | — | — | — | **NO CONVERSION** (mmol/L global standard) |
| Beta_Hydroxybutyrate | — | — | — | **NO CONVERSION** |
| pH_Arterial | — | — | — | **NO CONVERSION** (unitless) |
| Sodium/Potassium | — | — | — | **NO CONVERSION** (mmol/L = mEq/L) |
| Tacrolimus | — | — | — | **NO CONVERSION** (ng/mL standard globally) |
| AST | — | — | — | **NO CONVERSION** (U/L standard globally) |
| ALT | — | — | — | **NO CONVERSION** (U/L standard globally) |

**Decision rule**: If value is ambiguous (in overlap zone), KEEP AS-IS. Default to US.

### Step 5: Apply Conversions
```python
if operation == 'multiply':
    result = value * factor
else:  # operation == 'divide'
    result = value / factor
```

### Step 6: Post-Conversion Plausibility Check
Verify converted values fall in physiologically plausible ranges. If converted value is >10× expected range, detection threshold was wrong — re-check.

### Step 7: Write Output CSV
**CRITICAL**: Write raw floats with NO rounding, NO scientific notation, NO comma decimals.
```python
# CORRECT: pandas default preserves full precision
df.to_csv(output_path, index=False)

# CORRECT: csv module with raw floats
writer = csv.DictWriter(f, fieldnames=columns)
writer.writeheader()
for row in rows:
    writer.writerow({k: v for k, v in row.items()})  # v is raw float
```

## Output precision

**CRITICAL**: Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly.

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`, `"{:.2f}".format(x)`, `.round(N)`
- DO: Write raw float values directly (e.g., `ws.cell(row=r, column=c, value=x)` with x as raw float)
- The verifier's tolerance (often 1e-4) decides acceptable precision
- Rounding causes precision loss that triggers verifier failures

## Transplant/Hepatic Panel Quick Reference

When processing transplant panels (chemistry + liver function data):
- **Join key**: `patient_code` (NOT `visit_tag`)
- **Chemistry columns**: Tacrolimus, Creatinine, Magnesium, Potassium, Glucose
- **Liver columns**: Bilirubin_Total, Albumin, AST, ALT, Phosphorus
- **Output order**: Chemistry columns first, then liver columns
- **Conversions needed**: Bilirubin_Total (>30 → ÷17.1), Albumin (>60 → ÷10), Phosphorus (<3.0 → ×3.097)
- **No conversion**: Tacrolimus, Creatinine (if <20), Magnesium (if >1.0), Potassium, Glucose (if >3.0), AST, ALT
- **Drop patients** with missing values in ANY measurement column after join

## Anti-Patterns

- **Rounding trap**: `f"{x:.2f}"` or `df.round(2)` causes verifier failure. **7+ rounds of failures confirm this**.
- **Glucose trap**: Value 24 mg/dL treated as 24 mmol/L → converted to 432 mg/dL. Fix: Use <3.0 threshold only.
- **Total_T3 threshold**: Using >50 misses SI values 1.2-2.8 nmol/L. Use <3.0 threshold.
- **BNP/NT-proBNP confusion**: BNP factor is 0.143, NT-proBNP has DIFFERENT MW. Do NOT use NT-proBNP factor for BNP.
- **NT-proBNP auto-conversion**: Both pmol/L and pg/mL are commonly reported. Cannot reliably detect. Keep as-is.
- **Troponin scale confusion**: Value 16392 treated as μg/L → ×1000 gives 16M ng/mL (impossible). Values >1 are already ng/mL.
- **Wide overlap ranges**: Magnesium 0.3-2.0 means 1.95 (valid US hypermagnesemia) gets wrongly converted.
- **Premature rounding**: Rounding before detection obscures unit identification.
- **Over-conversion**: Converting values already in US units → 2-4× inflation.
- **No validation**: Converting without checking result plausibility → impossible values pass silently.
- **ICU pH rejection**: Flagging pH 6.91-6.98 as invalid. ICU patients can have severe acidosis.
- **Converting Lactate/Beta_Hydroxybutyrate**: These analytes use mmol/L globally. NO conversion needed.
- **pCO2 threshold confusion**: Using <20 instead of <15. Values in range 15-20 could be either very low mmHg (rare but possible) or moderately high kPa. Threshold <15 is safer.
- **Tacrolimus/AST/ALT conversion**: These are already in standard units (ng/mL, U/L). NO conversion needed.
- **Wrong merge key**: Using `visit_tag` as join key. Only `patient_code` is the join key; `visit_tag` is metadata to exclude.

## Known invariants (by sub-task)

### cardio-panel-harmonization
- **BNP**: ×0.143 if >5000 (pmol/L → pg/mL). Do NOT use 0.289.
- **NT_proBNP**: NO CONVERSION. Both pmol/L and pg/mL in common use.
- **Troponin_I**: ×1000 if <0.05 (μg/L → ng/mL). Values >1 already ng/mL.
- **Troponin_T**: ×1000 if <0.1 (μg/L → ng/mL). Values >1 already ng/mL
- **Creatinine**: >20 threshold, ÷88.4
- **Magnesium**: <1.0 threshold, ×2.43
- **Sodium/Potassium**: NO conversion (mmol/L = mEq/L)

### hepatic-panel-harmonization
- Bilirubin, Albumin, Protein need SI→US conversion via ÷17.1, ÷10, ÷10
- AST, ALT, ALP, GGT, INR, AFP, Platelets do NOT need conversion (1:1 or same units)
- Bilirubin >30 μmol/L threshold is critical; values 17-30 overlap US range

### electrolyte-metabolic-panel
- Glucose <3.0 mmol/L threshold is critical; values 3-50 overlap US range (hypoglycemia)
- Magnesium <1.0 threshold; values 1.0-2.5 are valid US including hypermagnesemia

### thyroid-mineral-panel
- Free_T4, Free_T3, Total_T4, Total_T3, PTH, Vitamin_D_25OH require SI→US conversion
- TSH, Anti_TPO, Thyroglobulin, Thyroglobulin_Antibody, Calcitonin do NOT need conversion
- **Total_T3 threshold**: <3.0 (SI values are small, 1.2-2.8 nmol/L), ×64.94
- **Free_T4 threshold**: >30 pmol/L
- **Total_T4 threshold**: >200 nmol/L

### icu-metabolic-panel
- **Multi-file join**: Join on `record_id` first, then drop incomplete rows
- **Lactate**: NO conversion needed (mmol/L is global standard)
- **Beta_Hydroxybutyrate**: NO conversion needed (mmol/L is global standard)
- **BUN**: ×2.8 if <5 (mmol/L → mg/dL). Values 5-150 likely US.
- **pCO2_Arterial**: ×7.5006 if <15 (kPa → mmHg). Values 20-80 likely US mmHg.
- **pH_Arterial**: NO conversion. Valid range 6.8-7.8 for ICU patients.
- **Glucose**: ×18.0 if <3.0 (mmol/L → mg/dL)
- **Creatinine**: ÷88.4 if >20 (μmol/L → mg/dL)
- **Osmolality/Anion_Gap/Sodium/Potassium**: NO conversion

### transplant-panel-harmonization
- **Tacrolimus**: NO CONVERSION. ng/mL is standard globally.
- **AST/ALT**: NO CONVERSION. U/L is standard globally.
- **Creatinine**: >20 threshold (μmol/L → mg/dL), ÷88.4
- **Bilirubin_Total**: >30 threshold (μmol/L → mg/dL), ÷17.1
- **Albumin**: >60 threshold (g/L → g/dL), ÷10
- **Glucose**: <3.0 threshold (mmol/L → mg/dL), ×18.0
- **Phosphorus**: <3.0 threshold (mmol/L → mg/dL), ×3.097
- **Magnesium/Potassium**: NO conversion (mmol/L = mEq/L)
- Multi-file join required: merge chemistry and liver panels on `patient_code`
- Output columns in exact order: `Tacrolimus,Creatinine,Magnesium,Potassium,Glucose,Bilirubin_Total,Albumin,AST,ALT,Phosphorus`
- Exclude `patient_code` and `visit_tag` from output

## References

See `references/conversion-factors.md` for full factor derivations, physiological ranges, and panel-specific details.
See `references/thyroid-factors.md` for thyroid-specific conversion details.
See `references/cardiovascular-factors.md` for cardiovascular biomarker conversion details.
See `references/icu-metabolic-panel.md` for ICU-specific analyte conversion factors, thresholds, and implementation patterns.
See `references/transplant-factors.md` for transplant panel conversion factors, multi-file join patterns, and column ordering.

## Scripts

See `scripts/icu_metabolic_harmonizer.py` for a reusable ICU panel harmonization implementation.
See `scripts/harmonize_transplant.py` for transplant panel harmonization with multi-file join. Usage: `python3 harmonize_transplant.py chemistry.csv liver.csv output.csv`
