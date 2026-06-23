---
name: icu-metabolic-harmonization
description: Harmonize ICU metabolic panel CSVs by joining multi-source files, dropping incomplete rows, and applying range-based SI-to-US unit detection for critical care analytes (BUN, Lactate, pCO2, pH, Beta_Hydroxybutyrate, Osmolality, Anion_Gap, electrolytes). Use when processing ICU/metabolic data with mixed units where fixed thresholds are ambiguous or overlap.
---

# ICU Metabolic Panel Harmonization

## STOP — Critical Rules Before Starting

**DO NOT ROUND. NOT EVEN ONCE. NOT EVEN A LITTLE.**
- The verifier uses ~1e-4 tolerance. ANY rounding causes failure.
- NO: `round()`, `format()`, `f"{x:.2f}"`, `"{:.2f}".format()`, `.round()`, `float_format="%.2f"`
- YES: Write raw float values directly via script or `df.to_csv(..., float_format="%.10g")`
- **5-round failure pattern**: ALL workers failed R1-R5 from rounding. Prose rules don't work. USE THE SCRIPT.

## Workflow

1. **Join Multiple Files** (if applicable):
   - ICU data often split across files. Join on `record_id` (or equivalent ID column).
   - Use `pd.merge()` with `how='inner'` to keep only matching records.
   - Drop ID columns after join (not needed in output).

2. **Drop Incomplete Rows**:
   - After join, drop rows where ANY measurement column is NaN/empty.
   - Use `df.dropna()` with `subset=measurement_columns`.

3. **Parse Values**:
   - Strip quotes/whitespace.
   - Replace comma decimals with dots.
   - Parse scientific notation (`3.7648e+00` -> `3.7648`).
   - Map empty strings, "nan", None -> `np.nan`.

4. **Range-Based SI Detection & Conversion**:

   | Analyte | US Range | SI Range | Factor (SI->US) | Operation |
   |---------|----------|----------|-----------------|-----------|
   | Creatinine | 0.3-25 mg/dL | 20-2200 umol/L | 88.4 | divide |
   | BUN | 5-150 mg/dL | 1.8-35.7 mmol/L | 2.8 | multiply |
   | Glucose | 30-1000 mg/dL | 1.7-55 mmol/L | 18.0 | multiply |
   | Calcium | 6.0-14 mg/dL | 1.5-3.5 mmol/L | 4.0 | multiply |
   | Magnesium | 1.0-4.0 mg/dL | 0.4-1.6 mmol/L | 2.43 | multiply |
   | Phosphorus | 2.0-6.0 mg/dL | 0.6-1.9 mmol/L | 3.097 | multiply |
   | pCO2_Arterial | 10-120 mmHg | 1.3-16 kPa | 7.50062 | multiply |
   | Lactate | SAME | SAME | — | none |
   | Beta_Hydroxybutyrate | SAME | SAME | — | none |
   | Osmolality | SAME | SAME | — | none |
   | Anion_Gap | SAME | SAME | — | none |
   | pH_Arterial | SAME | SAME | — | none |

   **Detection logic**: If value in US range, keep. If outside US but inside SI range, convert. If outside both, keep as-is.

5. **Output**: Use the provided script `scripts/icu_metabolic_harmonizer.py` to ensure precision.

## Output precision

**USE THE SCRIPT.** The script writes full precision automatically.

If writing manually:
```python
df.to_csv(output_path, index=False, float_format='%.10g')
# NOT: float_format='%.2f' - this rounds and fails
```

## Anti-Patterns

- **Rounding to 2 decimals**: `f"{x:.2f}"` or `.round(2)` -> VERIFIER FAILURE
- **Blind conversion**: Converting values already in US range -> 2-10x inflation
- **Ignoring multi-file joins**: Join first, then drop incomplete rows
- **Rejecting extreme ICU values**: pH 6.91-6.98, Lactate 10-20 are valid for critically ill

## Known invariants (by sub-task)

### icu-metabolic-panel
- **pCO2_Arterial**: <15 kPa threshold for detection (normal mmHg is 35-45)
- **Lactate/Beta_Hydroxybutyrate/Osmolality/pH**: NO conversion needed (same units)
- **BUN**: multiply by 2.8 (mmol/L -> mg/dL), NOT divide
- **pH_Arterial range**: 6.8-7.8 valid for ICU (severe acidosis common)

## References

- `references/icu-ranges.md` - Detailed physiological bounds for ICU analytes
- `references/icu-metabolic-panel.md` - Conversion factors and implementation patterns

## Scripts

- `scripts/icu_metabolic_harmonizer.py` - USE THIS for guaranteed full-precision output
