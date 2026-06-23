# Thyroid Panel Unit Conversions

Extended conversion reference for thyroid function tests and related antibodies/markers.

## Critical Principle: Verify Direction with Plausibility

Thyroid hormones commonly fail with wrong-direction conversions because US conventional values are often **smaller** than SI values (unlike glucose where US > SI).

| Analyte | SI Unit | US Unit | Factor | Direction | Detection Rule | Plausible US Range |
|---------|---------|---------|--------|-----------|--------------|-------------------|
| TSH | mIU/L | μIU/mL (same) | 1 | No conversion | — | 0.4–4.0 |
| Free_T4 | pmol/L | ng/dL | 12.87 | **SI ÷ 12.87 = US** | > 5 → assume SI | 0.8–2.0 ng/dL |
| Free_T3 | pmol/L | pg/dL | 15.38 | **SI ÷ 15.38 = US** | > 5 → assume SI | 200–400 pg/dL |
| Total_T4 | nmol/L | μg/dL | 12.87 | **SI ÷ 12.87 = US** | > 10 → assume SI | 4–12 μg/dL |
| Total_T3 | nmol/L | ng/dL | 0.0154 | **SI × 65.1 ≈ US** or **nmol/L ÷ 0.0154 = ng/dL** | < 10 → assume SI | 80–200 ng/dL |
| Anti_TPO | IU/mL | IU/mL (same) | 1 | No conversion | — | 0–34 typical |
| Thyroglobulin | μg/L | ng/mL | 1 | Same scale | — | 3–40 ng/mL (with thyroid) |
| Thyroglobulin_Antibody | IU/mL | IU/mL (same) | 1 | No conversion | — | 0–4 typical |
| Calcitonin | pmol/L | pg/mL | 3.67 | **SI × 3.67 = US** | > 10 → assume SI | 0–10 pg/mL typical |

## Critical Corrections from Failed Run

**Free_T4**: The agent repeatedly multiplied by 12.87 instead of dividing. Correct: pmol/L ÷ 12.87 = ng/dL.

**PTH (parathyroid hormone)**: Often in same panels. pmol/L ÷ 9.43 = pg/mL. The agent produced values >1000 pg/mL by multiplying.

**Total_T3**: Factor confusion. 1 nmol/L = 65.1 ng/dL (not 0.0154). The factor 0.0154 is ng/dL → nmol/L.

## Verification Ranges (US Conventional)

After conversion, check values are physiologically plausible:

| Analyte | Implausible US Low | Implausible US High | Notes |
|---------|-------------------|---------------------|-------|
| TSH | < 0.01 | > 100 | Can be >100 in severe hypothyroidism |
| Free_T4 | < 0.3 | > 5.0 | >5 suggests Graves' disease |
| Free_T3 | < 50 | > 800 | Hyperthyroidism can reach 600+ |
| Total_T4 | < 2 | > 20 | Pregnancy can elevate |
| Total_T3 | < 30 | > 400 | T3 toxicosis pattern |
| Calcitonin | 0 | > 100 | >50 suggests medullary carcinoma |

## Common Pitfalls

### Pitfall 1: Inverting the factor
```python
# WRONG - produces ~150 ng/dL for normal SI value
free_t4_us = free_t4_si * 12.87  # 20 pmol/L × 12.87 = 257 ng/dL (impossible!)

# CORRECT - produces ~1.6 ng/dL for normal SI value  
free_t4_us = free_t4_si / 12.87  # 20 pmol/L ÷ 12.87 = 1.6 ng/dL (correct!)
```

### Pitfall 2: Confusing pmol/L vs nmol/L
- Free T4, Free T3: **pmol/L** (picomolar, 10⁻¹²)
- Total T4, Total T3: **nmol/L** (nanomolar, 10⁻⁹)
- 1 nmol/L = 1000 pmol/L — check your units!

### Pitfall 3: Pathological values break "normal range" detection
In thyroid monitoring panels, values may be:
- **Severely hypothyroid**: TSH > 50, Free T4 < 0.5
- **Thyrotoxicosis**: Free T3 > 600, Free T4 > 5
- **Thyroid cancer follow-up**: Thyroglobulin suppressed < 0.1

Use **absolute cutoffs** for detection, not "is this normal?"

## Auto-Detection Algorithm

```python
def convert_thyroid_hormone(val, factor, us_min, us_max):
    """Convert with automatic direction detection via plausibility."""
    # Try division first (correct for most hormones)
    div_result = val / factor
    if us_min <= div_result <= us_max:
        return div_result
    
    # Try multiplication
    mul_result = val * factor
    if us_min <= mul_result <= us_max:
        return mul_result
    
    # Neither worked — already in target units or extreme pathology
    # Check if already in plausible US range
    if us_min <= val <= us_max:
        return val
    
    # Pathological value or unknown unit — return as-is with logging
    return val

# Usage
free_t4_converted = df['Free_T4'].apply(
    lambda x: convert_thyroid_hormone(x, 12.87, 0.3, 5.0)
)
```

## Reference Values Summary

| Analyte | SI Reference | US Reference |
|---------|-------------|--------------|
| TSH | 0.4–4.0 mIU/L | 0.4–4.0 μIU/mL |
| Free T4 | 10–25 pmol/L | 0.8–2.0 ng/dL |
| Free T3 | 3–8 pmol/L | 200–400 pg/dL |
| Total T4 | 60–160 nmol/L | 4.5–12.5 μg/dL |
| Total T3 | 1.2–3.0 nmol/L | 80–200 ng/dL |
| Calcitonin | < 10 pmol/L | < 40 pg/mL |