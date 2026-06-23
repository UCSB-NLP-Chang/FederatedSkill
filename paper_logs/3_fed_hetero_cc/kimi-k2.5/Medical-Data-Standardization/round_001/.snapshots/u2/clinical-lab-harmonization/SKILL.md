---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by normalizing number formats, detecting and converting SI/US units using physiological ranges, handling missing values, and rounding. Use when processing lab panels with mixed decimal separators, scientific notation, or inconsistent units.
---

# Clinical Lab Harmonization

## When to Use
- Processing CSV/TSV files with clinical lab measurements (electrolytes, metabolic markers)
- Data contains mixed SI (mmol/L, μmol/L) and US conventional (mg/dL) units
- Values may use comma decimals, scientific notation, or have missing entries
- Need to harmonize values to a single unit convention (typically US mg/dL)

## Core Workflow

1. **Parse values first**: Handle comma decimals (replace `,` with `.`), scientific notation, and missing values (empty strings, 'nan', None) before any conversion logic.

2. **Detect units by plausible ranges**: Do NOT assume all values need conversion. Use physiological ranges to infer whether a value is SI or US:
   - If value falls in SI range → convert to US
   - If value falls in US range → keep as-is

3. **Apply correct conversion factors**:
   - Calcium: mmol/L → mg/dL (×4.0 or ÷0.25)
   - Glucose: mmol/L → mg/dL (×18.0 or ÷0.0555)
   - Creatinine: μmol/L → mg/dL (÷88.4)
   - Magnesium: mmol/L → mg/dL (×2.43 or ÷0.411)

4. **Round to 2 decimal places** for standard clinical reporting.

## Range-Based Detection Thresholds

Key insight: Overlapping ranges cause false conversions. Use conservative thresholds:

| Analyte | Normal US (mg/dL) | Normal SI | Convert if value is |
|---------|-------------------|-----------|---------------------|
| Magnesium | 1.5-2.5 | 0.75-1.0 mmol/L | < 1.0 (clearly SI) |
| Calcium | 8.5-10.5 | 2.1-2.6 mmol/L | 1.5-4.0 |
| Glucose | 70-100 | 3.9-5.6 mmol/L | 1-50 |
| Creatinine | 0.7-1.3 | 60-110 μmol/L | > 20 |

**Anti-pattern**: Do NOT use wide overlap ranges like 0.3-2.0 for magnesium. Values like 1.95 are valid mg/dL (hypermagnesemia), not mmol/L.

## Validation Steps

1. After conversion, spot-check that values fall in plausible clinical ranges
2. Verify no impossible values (e.g., glucose > 1000 mg/dL without context)
3. Count rows dropped for missing values and confirm expected

## Common Failure Modes

- **Over-conversion**: Applying SI→US conversion to values already in mg/dL. Result: values 2-4× too high.
- **Under-conversion**: Leaving SI values unconverted. Result: values 10-20× too low.
- **Threshold collision**: When SI and US ranges overlap, prefer narrower SI detection threshold.

## Decision Rule

If an analyte's SI and US ranges overlap significantly:
- Use the lower bound of the SI normal range as the conversion threshold
- Values below this threshold are almost certainly SI
- Values above may be either; default to keeping as-is (assume US)

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### electrolyte-panel
- Output CSV must preserve original column order (minus excluded ID columns)
- All numeric values rounded to exactly 2 decimal places
- No empty/blank cells in data rows after harmonization
- Row count = original minus rows dropped for missing values

## References

See `references/conversion-factors.md` for detailed factor derivations and alternative rounding rules.
