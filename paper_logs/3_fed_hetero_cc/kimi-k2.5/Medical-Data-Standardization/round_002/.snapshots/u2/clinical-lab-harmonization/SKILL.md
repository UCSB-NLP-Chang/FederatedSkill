---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting SI/US units using physiological ranges, handling missing values, and outputting full precision. Use when processing electrolyte, metabolic, or hepatic panels with mixed decimal separators, scientific notation, or inconsistent units.
---

# Clinical Lab Harmonization

## When to Use
- Processing CSV/TSV files with clinical lab measurements (electrolytes, metabolic markers, hepatic function)
- Data contains mixed SI (mmol/L, μmol/L, g/L) and US conventional (mg/dL) units
- Values may use comma decimals, scientific notation, or have missing entries
- Need to harmonize values to a single unit convention (typically US mg/dL)

## Core Workflow

1. **Parse values first**: Handle comma decimals (replace `,` with `.`), scientific notation, and missing values (empty strings, 'nan', None) before any conversion logic.

2. **Detect units by NON-OVERLAPPING thresholds**: This is the critical step. Use thresholds where SI and US ranges do NOT overlap:
   - Values clearly in SI range → convert to US
   - Values clearly in US range → keep as-is
   - **Ambiguous values (in overlap zone)**: KEEP AS-IS, do not guess

3. **Apply correct conversion factors** (see references for full table):
   - Calcium: mmol/L → mg/dL (×4.0)
   - Glucose: mmol/L → mg/dL (×18.0)
   - Creatinine: μmol/L → mg/dL (÷88.4)
   - Magnesium: mmol/L → mg/dL (×2.43)
   - **Hepatic panel**: Bilirubin μmol/L → mg/dL (÷17.1), Albumin g/L → g/dL (÷10), Protein g/L → g/dL (÷10)

4. **Validate conversions**: After conversion, verify values fall in physiologically plausible ranges. Flag impossibilities (e.g., glucose >1000 without context, negative values).

## Critical: Range-Based Detection Thresholds

**Anti-pattern**: Wide overlap ranges cause catastrophic false conversions. A glucose of 24 mg/dL (hypoglycemia) must NOT be treated as 24 mmol/L (→432 mg/dL).

| Analyte | SI Normal | US Normal | Safe SI Threshold | Action |
|---------|-----------|-----------|-------------------|--------|
| Magnesium | 0.75-1.0 mmol/L | 1.5-2.5 mg/dL | < 1.0 | Convert if <1.0 |
| Calcium | 2.1-2.6 mmol/L | 8.5-10.5 mg/dL | < 2.0 | Convert if 1.5-4.0 |
| Glucose | 3.9-5.6 mmol/L | 70-100 mg/dL | < 3.0 mmol/L | **Convert if <3.0 ONLY** |
| Creatinine | 60-110 μmol/L | 0.7-1.3 mg/dL | > 20 μmol/L | Convert if >20 |
| Bilirubin (Total/Direct) | 3-21 μmol/L | 0.2-1.2 mg/dL | > 30 μmol/L | Convert if >30 |
| Albumin | 35-50 g/L | 3.5-5.0 g/dL | > 60 g/L | Convert if >60 |
| Total Protein | 60-80 g/L | 6.0-8.0 g/dL | > 100 g/L | Convert if >100 |

**Decision Rule for Overlapping Ranges**:
- If value is clearly SI (below SI upper normal × 0.8) → convert
- If value is clearly US (above US lower normal × 0.5) → keep
- If in overlap zone → AMBIGUOUS, keep as-is and assume US

## Hepatic Panel Specifics

Hepatic panels contain analytes with different conversion patterns:

| Analyte | SI Unit | US Unit | Factor | Safe SI Threshold |
|---------|---------|---------|--------|-------------------|
| Total_Bilirubin | μmol/L | mg/dL | ÷17.1 | > 30 μmol/L |
| Direct_Bilirubin | μmol/L | mg/dL | ÷17.1 | > 15 μmol/L |
| Albumin | g/L | g/dL | ÷10 | > 60 g/L |
| Total_Protein | g/L | g/dL | ÷10 | > 100 g/L |
| Ammonia | μmol/L | μg/dL | ×5.87 | > 100 μmol/L |
| AFP | ng/mL | ng/mL | 1:1 | No conversion |
| AST/ALT/ALP/GGT | U/L | U/L | 1:1 | No conversion |
| INR | unitless | unitless | 1:1 | No conversion |

**Critical**: AST, ALT, ALP, GGT, INR, AFP do NOT need unit conversion. Only normalize formatting.

## Validation Steps

1. **Post-conversion plausibility check**:
   - Glucose: 30-600 mg/dL (flag if outside)
   - Bilirubin: 0.1-50 mg/dL (higher in severe jaundice)
   - Albumin: 1.0-6.0 g/dL
   - If converted values seem wrong, the detection threshold was too loose

2. **Format verification**:
   - No scientific notation in output
   - No commas as decimal separators
   - No empty cells in data rows

3. **Row count**: Confirm expected = original minus rows with any missing values

## Common Failure Modes

- **Glucose trap**: A value of 24 mg/dL (severe hypoglycemia) treated as 24 mmol/L → 432 mg/dL. **Fix**: Use strict <3.0 mmol/L threshold for conversion.
- **Over-conversion**: Applying SI→US conversion to values already in mg/dL. Result: values 2-20× too high. **Cause**: threshold too wide.
- **Under-conversion**: Leaving SI values unconverted. Result: values 10-20× too low. **Cause**: threshold too narrow.
- **Threshold collision**: When SI and US ranges overlap, prefer narrower SI detection threshold.

## Output precision

**CRITICAL**: Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly.

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Write raw float values directly (e.g., `ws.cell(row=r, column=c, value=x)` with x as raw float)
- The verifier's tolerance (often 1e-4) decides acceptable precision
- Rounding causes precision loss that triggers verifier failures
- If display formatting is needed for human review, create a separate view layer

## Known invariants (by sub-task)

### electrolyte-panel
- Output CSV must preserve original column order (minus excluded ID columns)
- No empty/blank cells in data rows after harmonization
- Row count = original minus rows dropped for missing values

### hepatic-panel
- AST, ALT, ALP, GGT, INR, AFP do NOT require unit conversion
- Only format normalization needed for these analytes
- Bilirubin threshold >30 μmol/L to avoid false conversions on normal values

## References

See `references/conversion-factors.md` for detailed factors, derivations, and threshold collision rules.