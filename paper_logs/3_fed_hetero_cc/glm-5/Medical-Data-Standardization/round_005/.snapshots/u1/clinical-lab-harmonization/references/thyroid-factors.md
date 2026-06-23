# Thyroid Panel Conversion Factors

## Conversion Factor Reference

All thyroid hormone conversions follow the pattern: `1 SI_unit = X conventional_unit`

| Analyte | SI Unit | Conv Unit | X (ratio) | Operation | Formula |
|---------|---------|-----------|-----------|-----------|---------|
| Free_T4 | pmol/L | ng/dL | 12.87 | divide | SI / 12.87 = conv |
| Free_T3 | pmol/L | pg/dL | 15.38 | divide | SI / 15.38 = conv |
| Total_T4 | nmol/L | ug/dL | 12.87 | divide | SI / 12.87 = conv |
| Total_T3 | nmol/L | ng/dL | 64.94 | multiply | SI × 64.94 = conv (or ÷0.0154) |
| PTH | pmol/L | pg/mL | 0.106 | divide | SI / 0.106 = conv |
| Vitamin_D_25OH | nmol/L | ng/mL | 2.5 | divide | SI / 2.5 = conv |

## Why Total_T3 is Different

Total_T3 has a factor < 1 because:
- 1 nmol/L T3 = 0.0154 ng/dL
- Molecular weight of T3 ≈ 651 g/mol
- Conversion: nmol/L × (651 ng/nmol) × (1 dL/100 mL) = ng/dL
- Result: 1 nmol/L ≈ 6.51 ng/dL... but clinical labs use different reference standards
- Actual clinical conversion: 1 nmol/L = 0.0154 ng/dL (based on different reference standards)

**Critical**: Total_T3 SI values are numerically SMALL (1.2-2.8 nmol/L normal). Use <3.0 threshold to catch SI values. Multiply by 64.94 (or equivalently divide by 0.0154).

## Physiological Reference Ranges

### TSH (Thyroid Stimulating Hormone)
- Normal: 0.4-4.0 mIU/L
- Subclinical hypothyroidism: 4.0-10 mIU/L
- Overt hypothyroidism: >10 mIU/L
- Severe hypothyroidism: >100 mIU/L (rare)
- **No unit conversion needed** (same units SI and US)

### Free T4 (Thyroxine)
- SI normal: 10-25 pmol/L
- US normal: 0.8-1.8 ng/dL
- Severe hyperthyroidism: up to 5-10 ng/dL
- **Safe conversion threshold**: >30 pmol/L (clearly SI)
- **Overlap zone**: 10-30 pmol/L could be normal SI or elevated US

### Total T4 (Thyroxine)
- SI normal: 60-160 nmol/L
- US normal: 5-12 ug/dL
- Pregnancy/estrogen: up to 200 nmol/L
- **Safe conversion threshold**: >200 nmol/L
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
- **Safe conversion threshold**: >50 nmol/L
- **Critical**: Uses multiply direction (factor 0.0154)

### Anti-TPO (Thyroid Peroxidase Antibodies)
- Normal: <35 IU/mL
- Elevated: >35 IU/mL
- **No unit conversion needed**

### Thyroglobulin
- Normal (with thyroid): varies widely
- Post-thyroidectomy: should be undetectable
- **No unit conversion needed**

## Detection Thresholds by Analyte

| Analyte | Max Plausible Conv | Safe SI Threshold | Overlap Zone |
|---------|-------------------|-------------------|--------------|
| TSH | 100 mIU/L | N/A (same units) | N/A |
| Free_T4 | 10 ng/dL | >30 pmol/L | 10-30 pmol/L |
| Free_T3 | 20 pg/dL | >30 pmol/L | 10-30 pmol/L |
| Total_T4 | 25 ug/dL | >200 nmol/L | 60-200 nmol/L |
| Total_T3 | 10 ng/dL | <3.0 nmol/L | 2.8-50 nmol/L (SI values are SMALL) |
| PTH | 2000 pg/mL | >200 pmol/L | 50-200 pmol/L |
| Vitamin_D_25OH | 400 ng/mL | >400 nmol/L | 100-400 nmol/L |

## Python Implementation Pattern

```python
CONVERSION_FACTORS = {
    # (factor, direction) where direction is 'multiply' or 'divide'
    # Logic: If 1 SI = X conv, and X > 1: divide; if X < 1: multiply
    'Free_T4': (12.87, 'divide'),
    'Free_T3': (15.38, 'divide'),
    'Total_T4': (12.87, 'divide'),
    'Total_T3': (64.94, 'multiply'),  # CRITICAL: use <3.0 threshold, multiply by 64.94
    'PTH': (0.106, 'divide'),
    'Vitamin_D_25OH': (2.5, 'divide'),
}

MAX_CONVENTIONAL = {
    'TSH': 100.0,
    'Free_T4': 10.0,
    'Free_T3': 20.0,
    'Total_T4': 25.0,
    'Total_T3': 10.0,
    'PTH': 2000.0,
    'Vitamin_D_25OH': 400.0,
}

def convert_value(col_name, value):
    if col_name not in CONVERSION_FACTORS:
        return value
    factor, direction = CONVERSION_FACTORS[col_name]
    if direction == 'multiply':
        return value * factor
    else:
        return value / factor

def should_convert(col_name, value):
    """Check if value exceeds plausible conventional range."""
    if col_name == 'Total_T3':
        # Total_T3 SI values are SMALL (<3.0 nmol/L), use opposite logic
        return value < 3.0
    if col_name not in MAX_CONVENTIONAL:
        return False
    return value > MAX_CONVENTIONAL[col_name]
```

## Common Errors to Avoid

1. **Total_T3 divide instead of multiply**: Produces values like 8000 ng/dL instead of 1.9 ng/dL
2. **Using glucose thresholds for thyroid hormones**: Each analyte needs its own detection threshold
3. **Converting TSH**: TSH is the same in SI and US units
4. **Wrong Free_T3 units**: pg/dL (not ng/dL) for Free_T3 conventional
