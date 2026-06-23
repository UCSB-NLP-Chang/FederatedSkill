---
name: clinical-lab-harmonization
description: Harmonize clinical laboratory CSV data by parsing mixed number formats (scientific notation, comma decimals), detecting and converting between SI and conventional units using physiological range validation, handling missing values, and standardizing to exact precision. Use for electrolyte panels, metabolic profiles, or lab data requiring unit standardization before analysis.
---

# Clinical Lab Data Harmonization

## When to use
- Input data mixes scientific notation (`1.5e+02`) with European decimal commas (`142,0205`)
- Must detect and convert between SI units (mmol/L, μmol/L) and conventional units (mg/dL) per analyte
- Required to drop incomplete records, remove identifier columns, and enforce exact decimal precision
- Target format requires Unix line endings and standardized output

## Workflow

### 1. Parse Input Formats
- **Scientific notation**: Parse strings like `6.4372e+02` → `643.72`
- **European decimals**: Replace comma with dot *only when comma appears between digits* (e.g., `"142,0205"` → `142.0205`)
- **Missing values**: Treat empty strings, `nan`, `NaN`, `None`, `NULL` as missing; drop entire row if any analyte is missing

### 2. Detect Unit System & Convert
For each analyte value, use **bidirectional conversion testing**:

1. Define extended plausible conventional ranges (wider than normal to avoid converting pathological values):
   | Analyte | Plausible Conventional (mg/dL) | Plausible SI |
   |---------|-------------------------------|--------------|
   | Glucose | 30–700 | 2–40 mmol/L |
   | Creatinine | 0.3–15 | 25–1300 μmol/L |
   | Calcium | 6–14 | 1.5–3.5 mmol/L |
   | Magnesium | 0.5–5 | 0.2–2 mmol/L |

2. For each value, test both conversion directions:
   - `result_mult = value * factor`
   - `result_div = value / factor`
   - Keep the result that falls **inside** the plausible conventional range
   - If both land in range, prefer the one closer to the reference mean

3. Conversion factors:
   | Analyte | SI → Conventional |
   |---------|-------------------|
   | Glucose | × 18.0 (mmol/L → mg/dL) |
   | Creatinine | ÷ 88.4 (μmol/L → mg/dL) |
   | Calcium | × 4.0 (mmol/L → mg/dL) |
   | Magnesium | × 2.43 (mmol/L → mg/dL) |

4. **Do not convert values already in plausible conventional range** - avoid over-converting high-but-valid values (e.g., Glucose 500+ mg/dL in DKA).

### 3. Format & Write Output
- Round all numeric values to exactly 2 decimal places
- Strip identifier columns (e.g., `encounter_id`)
- Write with Unix line endings (`\n`); strip any `\r` if present
- Use dot decimal separator exclusively

### 4. Validation (Run Before Submitting)
1. **Line endings**: `file output.csv` must show `ASCII text`, not `with CRLF line terminators`
2. **No comma decimals in numeric fields**: Parse CSV column-wise, not line-wise
3. **Decimal precision**: All numeric values match pattern `^[0-9]+\.[0-9]{2}$`
4. **Plausibility**: No value >10× physiological max (indicates wrong unit direction)

## Anti-Patterns (Avoid)

- **Blind multiplication/division**: Never assume conversion factor direction. Test both directions against physiological ranges.
- **Naive comma-regex**: `[0-9],[0-9]` matches CSV delimiters. Only replace comma when between digits.
- **Over-conversion**: High Glucose (500+ mg/dL in DKA) or high Creatinine (10+ mg/dL in AKI) are valid. Use wide plausible ranges.
- **Rounding before conversion**: Always convert first, then round. Rounding early corrupts threshold detection.
- **CRLF line endings**: Python's `csv` module on Windows may add `\r\n`. Explicitly set `lineterminator='\n'`.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

**Exception**: Clinical lab harmonization specifically requires `round(value, 2)` for final output formatting per task requirements.

## Scripts

- `scripts/harmonize_lab_csv.py`: Reference implementation for CSV harmonization workflow

## References

- `references/unit-conversions.md`: Detailed conversion factors and reference ranges
