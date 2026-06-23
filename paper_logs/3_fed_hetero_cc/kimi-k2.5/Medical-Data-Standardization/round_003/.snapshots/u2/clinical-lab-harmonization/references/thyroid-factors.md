# Thyroid Panel Conversion Factors

## Conversion Factor Reference

All thyroid hormone conversions follow a specific pattern. **Pay attention to the operation (× or ÷)** — not all conversions use the same operation.

| Analyte | SI Unit | Conv Unit | Factor | Operation | Formula |
|---------|---------|-----------|--------|-----------|---------|
| Free_T4 | pmol/L | ng/dL | 12.87 | ÷ (divide) | SI / 12.87 = conv |
| Free_T3 | pmol/L | pg/mL | 15.38 | ÷ (divide) | SI / 15.38 = conv |
| Total_T4 | nmol/L | μg/dL | 12.87 | ÷ (divide) | SI / 12.87 = conv |
| Total_T3 | nmol/L | ng/dL | 64.94 | × (multiply) | SI × 64.94 = conv |
| PTH | ng/L | pg/mL | 0.106 | × (multiply) | SI × 0.106 = conv |
| Vitamin_D_25OH | nmol/L | ng/mL | 2.5 | ÷ (divide) | SI / 2.5 = conv |

## Why Total_T3 is Different

Total_T3 is unique because **SI values are SMALL numbers (1.2-2.8 nmol/L) while conventional values are LARGE numbers (80-200 ng/dL)**.

- 1 nmol/L T3 = 64.94 ng/dL (approximately)
- Molecular weight of T3 ≈ 651 g/mol
- Conversion: nmol/L × (651 ng/nmol) × (1 dL/100 mL) = ng/dL
- Result: 1 nmol/L ≈ 64.94 ng/dL

**CRITICAL**: 
- To convert nmol/L → ng/dL: MULTIPLY by 64.94
- The factor 0.0154 is for ng/dL → nmol/L, NOT nmol/L → ng/dL
- Using ÷0.0154 gives the same result as ×64.94, but ×64.94 is clearer and less error-prone

### Common Total_T3 Errors

| Input | Wrong Operation | Wrong Result | Correct Operation | Correct Result |
|-------|-----------------|--------------|-------------------|----------------|
| 2.0 nmol/L | ÷ 64.94 | 0.0308 ng/dL | × 64.94 | 129.9 ng/dL |
| 2.0 nmol/L | × 0.0154 | 0.0308 ng/dL | × 64.94 | 129.9 ng/dL |
| 2.0 nmol/L | ÷ 0.0154 | 129.9 ng/dL | — | (this works!) |

**Safe approach**: Always use × 64.94 for Total_T3 SI→US conversion.

## Physiological Reference Ranges

### TSH (Thyroid Stimulating Hormone)
- Normal: 0.4-4.0 mIU/L
- Subclinical hypothyroidism: 4.0-10 mIU/L
- Overt hypothyroidism: >10 mIU/L
- Severe hypothyroidism: >100 mIU/L (rare)
- **No unit conversion needed** (same units SI and US)

### Free T4 (Thyroxine)
- SI normal: 10-25 pmol/L
- US normal: 0.8-2.0 ng/dL
- Severe hyperthyroidism: up to 5-10 ng/dL
- **Safe conversion threshold**: >30 pmol/L (clearly SI)
- **Overlap zone**: 10-30 pmol/L could be normal SI or elevated US

### Total T4 (Thyroxine)
- SI normal: 60-160 nmol/L
- US normal: 5-12 μg/dL
- Pregnancy/estrogen effect: up to 200 nmol/L
- **Safe conversion threshold**: >200 nmol/L (SI and US ranges overlap significantly)
- **Overlap zone**: 60-200 nmol/L ambiguous

### Free T3 (Triiodothyronine)
- SI normal: 3.5-6.5 pmol/L
- US normal: 230-420 pg/dL
- Severe hyperthyroidism: up to 10-20 pg/dL
- **Safe conversion threshold**: >30 pmol/L

### Total T3 (Triiodothyronine)
- SI normal: 1.2-2.8 nmol/L
- US normal: 80-200 ng/dL
- Severe hyperthyroidism: up to 400-500 ng/dL
- **Safe conversion threshold**: <3.0 nmol/L (SI values are SMALL)
- **CRITICAL**: SI values (1.2-2.8) are small; US values (80-200) are large

### Anti-TPO (Thyroid Peroxidase Antibodies)
- Normal: <35 IU/mL
- Elevated: >35 IU/mL
- **No unit conversion needed**

### Thyroglobulin
- Normal (with thyroid): varies widely
- Post-thyroidectomy: should be undetectable
- **No unit conversion needed**

## Detection Thresholds by Analyte

| Analyte | SI Normal Range | US Normal Range | SI Detection Threshold | Decision |
|---------|-----------------|-----------------|------------------------|----------|
| TSH | 0.4-4.0 mIU/L | same | N/A | No conversion |
| Free_T4 | 10-25 pmol/L | 0.8-2.0 ng/dL | >30 pmol/L | Convert if >30 |
| Free_T3 | 3.5-6.5 pmol/L | 230-420 pg/dL | >30 pmol/L | Convert if >30 |
| Total_T4 | 60-160 nmol/L | 5-12 μg/dL | >200 nmol/L | Convert if >200 |
| Total_T3 | 1.2-2.8 nmol/L | 80-200 ng/dL | <3.0 nmol/L | Convert if <3.0 |
| PTH | varies | 10-65 pg/mL | >500 ng/L | Convert if >500 |
| Vitamin_D_25OH | 75-250 nmol/L | 30-100 ng/mL | >100 nmol/L | Convert if >100 |

## Python Implementation Pattern

```python
# Conversion factors: (factor, operation) where operation is 'multiply' or 'divide'
CONVERSION_FACTORS = {
    'Free_T4': (12.87, 'divide'),
    'Free_T3': (15.38, 'divide'),
    'Total_T4': (12.87, 'divide'),
    'Total_T3': (64.94, 'multiply'),  # CRITICAL: multiply, not divide
    'PTH': (0.106, 'multiply'),
    'Vitamin_D_25OH': (2.5, 'divide'),
}

# Detection thresholds: value must EXCEED threshold to be SI
SI_THRESHOLDS = {
    'Free_T4': 30,      # pmol/L
    'Free_T3': 30,      # pmol/L
    'Total_T4': 200,    # nmol/L
    'Total_T3': 3.0,    # nmol/L - but for Total_T3, SI values are BELOW this!
}

# For Total_T3, SI values are SMALL (< 3.0), so detection logic is inverted
def should_convert_si(col_name, value):
    if col_name == 'Total_T3':
        return value < 3.0  # SI values are small (1.2-2.8)
    elif col_name in SI_THRESHOLDS:
        return value > SI_THRESHOLDS[col_name]
    return False

def convert_value(col_name, value):
    if col_name not in CONVERSION_FACTORS:
        return value
    factor, operation = CONVERSION_FACTORS[col_name]
    if operation == 'multiply':
        return value * factor
    else:
        return value / factor

# Maximum plausible values in US units (for plausibility check)
MAX_US_VALUES = {
    'Free_T4': 10.0,    # ng/dL
    'Free_T3': 20.0,    # pg/mL
    'Total_T4': 25.0,   # μg/dL
    'Total_T3': 500.0,  # ng/dL (severe hyperthyroidism)
    'TSH': 100.0,       # mIU/L
}
```

## Common Errors to Avoid

1. **Total_T3 factor direction**: Using ÷ 64.94 or × 0.0154 produces values like 0.03 ng/dL instead of 129 ng/dL
2. **Total_T3 threshold direction**: Values >50 are US, not SI. SI values are 1.2-2.8, which are < 3.0
3. **Converting TSH**: TSH is the same in SI and US units — no conversion needed
4. **Wrong Free_T3 units**: US Free_T3 is pg/mL, not ng/dL
5. **Over-converting thyroid hormones**: Use conservative thresholds (Free_T4 >30, Total_T4 >200) to avoid converting high US values
