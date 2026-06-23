# Lactate Unit Conversion

## Why Lactate Needs Conversion in Respiratory Panels

Unlike the ICU metabolic panel where lactate is reported in mmol/L consistently, respiratory panels often mix units and require explicit conversion to mg/dL.

## Conversion Factor

| From | To | Factor | Operation |
|------|-----|--------|-----------|
| mmol/L | mg/dL | 9.0 | multiply |

**Derivation**: Lactic acid (C₃H₆O₃) molecular weight = 90.08 g/mol
- 1 mmol/L × 90.08 mg/mmol ÷ 10 dL/L = 9.008 mg/dL ≈ 9.0 mg/dL

## Detection Threshold

| Analyte | SI Normal | US Normal | Safe Threshold |
|---------|-----------|-----------|----------------|
| Lactate | 0.5-2.5 mmol/L | 4.5-22.5 mg/dL | < 5.0 mmol/L |

**Rationale**: 
- Normal lactate in mmol/L: 0.5-2.5 (small numbers)
- Normal lactate in mg/dL: 4.5-22.5 (larger numbers)
- Values 5-30 are ambiguous (could be 5 mmol/L = 45 mg/dL, or 5 mg/dL = 0.56 mmol/L)
- Conservative threshold < 5.0 catches clear SI values while avoiding over-conversion

## Reference Ranges

| Condition | mmol/L | mg/dL |
|-----------|--------|-------|
| Normal | 0.5-2.0 | 4.5-18 |
| Mild elevation | 2.0-4.0 | 18-36 |
| Lactic acidosis | >4.0 | >36 |
| Severe shock | >10.0 | >90 |

## Common Errors

| Error | Wrong Result | Correct Result |
|-------|--------------|----------------|
| No conversion | 2.5 (mmol/L) | 22.5 (mg/dL) |
| Wrong factor (×18 like glucose) | 45 | 22.5 |
| Threshold too high (converting 8 mmol/L) | 72 mg/dL | keep 8 (likely already mg/dL, implausible as mmol/L) |
