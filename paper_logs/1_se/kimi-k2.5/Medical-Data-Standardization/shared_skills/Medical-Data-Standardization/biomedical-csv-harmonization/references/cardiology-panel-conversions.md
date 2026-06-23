# Cardiology Panel Unit Conversions

Extended conversion reference for cardiac biomarkers and electrolytes commonly found in cardiology panels.

## Cardiac Biomarker Conversions

| Analyte | SI Unit | US Unit | Conversion | Detection Rule | Plausible US Range |
|---------|---------|---------|------------|--------------|-------------------|
| BNP | pmol/L | pg/mL | SI × 0.289 = US | > 50 → assume SI | 5–5000 pg/mL |
| NT_proBNP | pmol/L | pg/mL | SI × 0.118 = US | > 500 → assume SI | 20–35000 pg/mL |
| Troponin_I | ng/L | ng/mL | SI ÷ 1000 = US | > 100 → assume SI | 0–50 ng/mL |
| Troponin_T | ng/L | ng/mL | SI ÷ 1000 = US | > 100 → assume SI | 0–1.0 ng/mL |

## Electrolyte Conversions (Cardiology Context)

| Analyte | SI Unit | US Unit | Conversion | Detection Rule | Plausible US Range |
|---------|---------|---------|------------|--------------|-------------------|
| Creatinine | μmol/L | mg/dL | SI ÷ 88.4 = US | > 20 → assume SI | 0.5–15 mg/dL |
| Magnesium | mmol/L | mg/dL | SI × 2.43 = US | < 1.5 → assume SI | 1.5–3.0 mg/dL |
| Sodium | mmol/L | mEq/L | 1:1 (no conversion) | — | 120–160 mEq/L |
| Potassium | mmol/L | mEq/L | 1:1 (no conversion) | — | 2.5–7.0 mEq/L |

## Critical Conversion Notes

### BNP (B-type Natriuretic Peptide)
- **Molecular weight**: 32 amino acids ≈ 4 kDa, factor 0.289
- **SI reference**: 0–100 pmol/L (normal < 35)
- **US reference**: 0–100 pg/mL
- **Pitfall**: Some labs report BNP in pg/mL directly; check if input values are already US conventional

### NT-proBNP
- **Molecular weight**: 76 amino acids, factor 0.118
- **SI reference**: 0–3000 pmol/L (varies by age/sex)
- **US reference**: 0–900 pg/mL
- **Detection**: NT-proBNP values in pmol/L are typically 3-10× larger than pg/mL equivalent

### Troponins (I and T)
- **Unit trap**: High-sensitivity assays report in ng/L; conventional in ng/mL
- **Conversion**: 1000 ng/L = 1 ng/mL = 1 μg/L
- **Detection**: Values > 100 almost certainly ng/L (SI); values < 1 likely ng/mL (US)
- **Critical thresholds**: Troponin I > 40 ng/L (0.04 ng/mL) suggests myocardial injury

## Pathological Value Handling

Cardiology panels often include acute pathology—do NOT use "normal range" for unit detection:

| Analyte | Typical Normal | Pathological Seen |
|---------|---------------|-------------------|
| BNP | < 100 pg/mL | 3000–5000 pg/mL (acute HF) |
| NT-proBNP | < 300 pg/mL | 20000–35000 pg/mL (severe HF) |
| Troponin I | < 0.04 ng/mL | 50–100 ng/mL (large MI) |
| Troponin T | < 0.01 ng/mL | 2–10 ng/mL (large MI) |
| Creatinine | 0.7–1.2 mg/dL | 10–15 mg/dL (cardiorenal syndrome) |

## Verification Ranges (US Conventional)

After conversion, check values are physiologically plausible:

| Analyte | Implausible Low | Implausible High | Notes |
|---------|-----------------|------------------|-------|
| BNP | < 1 pg/mL | > 10000 pg/mL | >5000 suggests severe decompensated HF |
| NT-proBNP | < 5 pg/mL | > 50000 pg/mL | Age-adjusted cutoffs used clinically |
| Troponin_I | < 0 | > 200 ng/mL | Massive MI may reach 100+ |
| Troponin_T | < 0 | > 25 ng/mL | Massive MI may reach 10+ |
| Creatinine | < 0.3 mg/dL | > 20 mg/dL | Cardiorenal syndrome common in HF |
| Magnesium | < 1.0 mg/dL | > 4.0 mg/dL | Hypomagnesemia common in diuretic use |

## Template-Based Output Workflow

When the task provides a template file:

1. **Read template first** — Preserve exact column order and header names
2. **Match by column name** — Map input columns to template columns (case-sensitive)
3. **Preserve header exactly** — Do not modify template header text
4. **Output row count** — May differ from template if input has missing values
5. **Replace placeholder rows** — Remove any PLACEHOLDER rows before writing data

## Common Pitfalls from Failed Runs

### Pitfall 1: Troponin unit confusion (ng/L vs ng/mL)
```python
# WRONG: Treats 16392 as ng/mL (impossibly high)
trop_i = 16392.0  # Actually ng/L, needs ÷ 1000

# CORRECT: Detects ng/L by magnitude, converts
trop_i = 16392.0 / 1000  # = 16.39 ng/mL (correct)
```

### Pitfall 2: BNP/NT-proBNP factor inversion
```python
# WRONG: Division instead of multiplication
bnp_us = bnp_si / 0.289  # Produces implausibly small value

# CORRECT: pmol/L is smaller unit than pg/mL
bnp_us = bnp_si * 0.289  # Correct: 35 pmol/L × 0.289 = 10.1 pg/mL
```

### Pitfall 3: European decimals in high-precision values
```python
# Input: "1694,4303" — European decimal comma
# Parsed as: 1694.4303 (correct after comma→dot replacement)
# Output: "1694.43" (2 decimal places, correct)
```

### Pitfall 4: Trailing zeros lost in float formatting
```python
# WRONG: round(2.5, 2) → 2.5 → "2.5" in output
# CORRECT: f"{2.5:.2f}" → "2.50" in output
```

## Auto-Detection Algorithm

```python
def convert_cardiac_biomarker(val, si_to_us_factor, us_range, si_indicator_threshold):
    """Convert with automatic detection via plausibility."""
    # Assume SI if value exceeds threshold
    if val > si_indicator_threshold:
        converted = val * si_to_us_factor  # Most cardiac: SI is smaller number
        if us_range[0] <= converted <= us_range[1]:
            return converted
    # Check if already in US range
    if us_range[0] <= val <= us_range[1]:
        return val
    # Pathological or unknown — return as-is with logging
    return val

# Usage examples
bnp_converted = df['BNP'].apply(lambda x: convert_cardiac_biomarker(x, 0.289, (5, 5000), 50))
ntprobnp_converted = df['NT_proBNP'].apply(lambda x: convert_cardiac_biomarker(x, 0.118, (20, 35000), 500))
trop_i_converted = df['Troponin_I'].apply(lambda x: convert_cardiac_biomarker(x, 0.001, (0, 50), 100))  # ng/L→ng/mL
```
