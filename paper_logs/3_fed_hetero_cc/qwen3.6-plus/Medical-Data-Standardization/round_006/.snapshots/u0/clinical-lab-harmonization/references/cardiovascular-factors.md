# Cardiovascular Panel Conversion Factors

## Critical: NT-proBNP Non-Conversion Policy

**Do NOT attempt automatic NT-proBNP conversion.**

Unlike most lab values, NT-proBNP is reported in BOTH pmol/L AND pg/mL by different major laboratories and assay manufacturers, with no standardized convention. The same numerical value (e.g., 1000) could be:
- 1000 pmol/L = 11,800 pg/mL (elevated, concerning for heart failure)
- 1000 pg/mL = 85 pmol/L (normal range)

**Detection is unreliable** because reference ranges vary by assay and clinical context:
- Acute heart failure cutoff: ~300 pg/mL (Roche) or ~900 pg/mL (Siemens)
- Normal range: <125 pg/mL (age <75) or <450 pg/mL (age >75)
- pmol/L cutoffs: ~26 pmol/L or ~106 pmol/L depending on conversion factor used

**Decision**: Keep NT-proBNP values as-is. If unit metadata is explicitly present in source data, document but do not convert unless specifically instructed.

## BNP Conversion

### Molecular Basis
- BNP (B-type Natriuretic Peptide) MW: ~3464 g/mol
- 1 pmol/L × 3464 g/mol ÷ 1000 mL/L ÷ 1000 pg/ng = **0.143 pg/mL**

### Conversion Table
| From | To | Factor | Operation |
|------|-----|--------|-----------|
| pmol/L | pg/mL | 0.143 | × |
| pg/mL | pmol/L | 6.99 | ÷ |

### Detection Threshold
- Convert if > 5000 (likely pmol/L, would give ~715 pg/mL after conversion)
- Normal range: 0-100 pg/mL (US conventional)
- Heart failure: >400 pg/mL

**Common error**: Using NT-proBNP factor (0.118) gives 20% error. These are different molecules with different MW.

## Troponin Conversion

### Troponin I
| From | To | Factor | Detection Threshold |
|------|-----|--------|---------------------|
| μg/L | ng/mL | 1000 (×) | < 0.05 |

**Critical**: Values >1000 are certainly already ng/mL. A value like 16392 with ×1000 conversion would give 16,392,000 ng/mL, which exceeds blood volume (impossible).

Contemporary assays report:
- URL (99th percentile): 0.04 ng/mL (SI: 0.04 μg/L)
- STEMI threshold: >0.5 ng/mL
- Massive MI: 10-100 ng/mL
- Extreme cases: up to 1000 ng/mL

### Troponin T
| From | To | Factor | Detection Threshold |
|------|-----|--------|---------------------|
| μg/L | ng/mL | 1000 (×) | < 0.1 |

High-sensitivity Troponin T (hs-cTnT):
- URL: 0.014 ng/mL (14 ng/L)
- Ruled out MI: <5 ng/L

## Electrolyte Conversions (Cardiology Panels)

### Magnesium
**Previous error in trace**: Using >4 as threshold and ×0.411 factor.

Correct approach:
- SI: mmol/L (small numbers: 0.75-1.0 normal)
- US: mg/dL (larger numbers: 1.8-2.4 normal)
- Factor: 1 mmol/L = 2.43 mg/dL (NOT 0.411)
- Detection: < 1.0 mmol/L suggests SI unit (converts to 2.43 mg/dL, normal US)

### Sodium, Potassium
**NO CONVERSION NEEDED.** mmol/L = mEq/L (1:1 identical units).

### Creatinine
Standard conversion: >20 μmol/L detection, ÷88.4 to mg/dL.

## Python Implementation Pattern

```python
# Cardiovascular panel conversion factors
CARDIO_FACTORS = {
    'BNP': (0.143, 'multiply', 5000, '>'),  # factor, op, threshold, direction
    'Troponin_I': (1000, 'multiply', 0.05, '<'),
    'Troponin_T': (1000, 'multiply', 0.1, '<'),
    'Creatinine': (88.4, 'divide', 20, '>'),
    'Magnesium': (2.43, 'multiply', 1.0, '<'),
}

def convert_cardio_value(col_name, value):
    """Apply cardiovascular panel conversions."""
    if col_name not in CARDIO_FACTORS:
        return value  # No conversion (NT_proBNP, Sodium, Potassium)
    
    factor, operation, threshold, direction = CARDIO_FACTORS[col_name]
    
    # Check if conversion needed
    should_convert = (value > threshold) if direction == '>' else (value < threshold)
    
    if not should_convert:
        return value
    
    if operation == 'multiply':
        result = value * factor
    else:
        result = value / factor
    
    # Plausibility check
    PLAUSIBLE_MAX = {
        'BNP': 10000,      # pg/mL
        'Troponin_I': 50000,  # ng/mL
        'Troponin_T': 10000,  # ng/mL
        'Creatinine': 25,  # mg/dL
        'Magnesium': 10,   # mg/dL
    }
    
    if result > PLAUSIBLE_MAX.get(col_name, float('inf')) * 10:
        # Likely false conversion - revert
        return value
    
    return result
```

## Common Cardiovascular Panel Errors

| Error | Manifestation | Fix |
|-------|--------------|-----|
| BNP factor swapped | 1694 pmol/L → 489 pg/mL (should be 242) | Use 0.143, not 0.289 |
| NT-proBNP auto-converted | 25814 → 3046 (assuming pmol/L) | NO CONVERSION for NT-proBNP |
| Troponin over-conversion | 16392 → 16392000 | Values >1000 already ng/mL |
| Magnesium wrong factor | 4.6 mmol/L → 1.9 mg/dL (should be 11.2) | Use ×2.43, not ×0.411 |
| Magnesium wrong threshold | Converting values 1.5-4 | Only convert <1.0 (SI is small) |
| Rounding | Output 489.69 instead of 489.690281 | NEVER round - full precision |