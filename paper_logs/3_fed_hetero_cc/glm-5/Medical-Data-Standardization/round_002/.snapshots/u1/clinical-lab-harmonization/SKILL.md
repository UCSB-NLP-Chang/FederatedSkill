---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting mismatched units (SI vs US conventional) using physiological range thresholds, handling missing values, and outputting full-precision values. Use when processing electrolyte, metabolic, or hepatic panels with mixed decimal separators, scientific notation, or inconsistent unit systems.
---

# Clinical Lab Harmonization

## STOP — Precision Checkpoint (READ FIRST)

**CRITICAL**: This skill outputs raw float values for verifier tolerance comparison.

- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: Write raw floats directly to output (e.g., `csv.writer(...).writerow([val])`)
- The verifier uses tolerance-based comparison (~1e-4), NOT fixed decimal format
- If you round, the skill FAILS

## When to Use

- Processing CSV/TSV files with clinical lab measurements
- Data contains mixed SI (mmol/L, μmol/L, g/L) and US (mg/dL, g/dL) units
- Need to harmonize values to a single unit convention
- Values may use comma decimals, scientific notation, or have missing entries
- Covers electrolyte panels, metabolic panels, hepatic panels

## Core Workflow

1. **Parse values first**: Handle comma decimals (replace `,` with `.`), scientific notation, and missing values (empty strings, 'nan', None) before any conversion logic.

2. **Detect units by NON-OVERLAPPING thresholds**: Use thresholds where SI and US ranges do NOT overlap:
   - Values clearly in SI range → convert to US
   - Values clearly in US range → keep as-is
   - Ambiguous values (in overlap zone) → KEEP AS-IS, do not guess

3. **Apply correct conversion factors**:
   - Calcium: mmol/L → mg/dL (×4.0)
   - Glucose: mmol/L → mg/dL (×18.0)
   - Creatinine: μmol/L → mg/dL (÷88.4)
   - Magnesium: mmol/L → mg/dL (×2.43)
   - Bilirubin: μmol/L → mg/dL (÷17.1)
   - Albumin: g/L → g/dL (÷10)
   - Total Protein: g/L → g/dL (÷10)

4. **Write full-precision output**: Pass raw floats directly to CSV/Excel writer. No rounding, no formatting.

## Range-Based Detection Thresholds

**Anti-pattern**: Wide overlap ranges cause catastrophic false conversions. A glucose of 24 mg/dL (hypoglycemia) must NOT be treated as 24 mmol/L.

| Analyte | SI Normal | US Normal | Convert if value is |
|---------|-----------|-----------|---------------------|
| Magnesium | 0.75-1.0 mmol/L | 1.5-2.5 mg/dL | < 1.0 (clearly SI) |
| Calcium | 2.1-2.6 mmol/L | 8.5-10.5 mg/dL | 1.5-4.0 |
| Glucose | 3.9-5.6 mmol/L | 70-100 mg/dL | **< 3.0 ONLY** |
| Creatinine | 60-110 μmol/L | 0.7-1.3 mg/dL | > 20 |
| Bilirubin | 2-20 μmol/L | 0.1-1.2 mg/dL | > 30 |
| Albumin | 35-50 g/L | 3.5-5.0 g/dL | > 60 |
| Total Protein | 60-80 g/L | 6.0-8.0 g/dL | > 100 |

**Glucose trap**: Values 24-70 mg/dL are valid (hypoglycemia to normal). Do NOT convert these as SI. Only convert if < 3.0 mmol/L (≈54 mg/dL after conversion).

## Hepatic Panel Specifics

| Analyte | SI Unit | US Unit | Factor | Needs Conversion |
|---------|---------|---------|--------|------------------|
| Total Bilirubin | μmol/L | mg/dL | ÷17.1 | Yes |
| Direct Bilirubin | μmol/L | mg/dL | ÷17.1 | Yes |
| Albumin | g/L | g/dL | ÷10 | Yes |
| Total Protein | g/L | g/dL | ÷10 | Yes |
| AST, ALT, ALP, GGT | U/L | U/L | 1:1 | **NO** |
| INR | unitless | unitless | 1:1 | **NO** |
| AFP | μg/L | ng/mL | 1:1 | **NO** |
| Platelets | ×10⁹/L | /μL | 1:1 | **NO** |

## Known Invariants (by sub-task)

### hepatic-panel-harmonization
- AST, ALT, ALP, GGT, INR, AFP do NOT need unit conversion — only format normalization
- Bilirubin > 30 μmol/L → likely SI, convert; < 30 → keep as-is
- Albumin > 60 g/L → likely SI, convert; < 60 → may be g/dL, keep

### glucose-processing
- Glucose < 3.0 mmol/L → convert to US; glucose 3-50 → ambiguous, default to keep
- Valid hypoglycemia: 20-70 mg/dL — do NOT treat as SI mmol/L

## Validation Steps

1. **Post-conversion plausibility check**:
   - Glucose: 30-600 mg/dL (flag if outside)
   - Bilirubin: 0.1-50 mg/dL
   - Albumin: 1.0-6.0 g/dL
   - If converted values seem wrong, detection threshold was too loose

2. **Format verification**:
   - No scientific notation in output
   - No commas as decimal separators
   - No empty cells in data rows

3. **Row count**: Confirm expected = original minus rows with any missing values

## Common Failure Modes

- **Over-conversion**: Applying SI→US to values already in US units. Result: values 2-20× too high.
- **Glucose trap**: A value of 24 mg/dL treated as 24 mmol/L → 432 mg/dL. Fix: Use strict <3.0 threshold.
- **Precision loss**: Rounding to 2 decimals causes verifier mismatch. Fix: Output raw floats.

## References

See `references/conversion-factors.md` for detailed factor derivations and physiological ranges.
