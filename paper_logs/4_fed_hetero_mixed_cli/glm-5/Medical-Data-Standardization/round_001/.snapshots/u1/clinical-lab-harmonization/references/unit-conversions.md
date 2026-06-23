# Clinical Lab Unit Conversions

## Detection and Conversion Rules

Use bidirectional testing: for each value, test both `value * factor` and `value / factor`, keep the result that lands inside the plausible conventional range.

## Electrolytes & Metabolites

### Glucose
- **Conventional**: mg/dL
- **SI**: mmol/L
- **Conversion**: mmol/L × 18.0 → mg/dL
- **Plausible conventional**: 30–700 mg/dL (includes DKA)
- **Plausible SI**: 2–40 mmol/L
- **Reference mean**: ~100 mg/dL (fasting normal)

### Creatinine
- **Conventional**: mg/dL
- **SI**: μmol/L
- **Conversion**: μmol/L ÷ 88.4 → mg/dL
- **Plausible conventional**: 0.3–15 mg/dL (includes AKI/CKD)
- **Plausible SI**: 25–1300 μmol/L
- **Reference mean**: ~1.0 mg/dL

### Calcium (Total)
- **Conventional**: mg/dL
- **SI**: mmol/L
- **Conversion**: mmol/L × 4.0 → mg/dL
- **Plausible conventional**: 6–14 mg/dL
- **Plausible SI**: 1.5–3.5 mmol/L
- **Reference mean**: ~9.5 mg/dL

### Magnesium
- **Conventional**: mg/dL
- **SI**: mmol/L
- **Conversion**: mmol/L × 2.43 → mg/dL
- **Plausible conventional**: 0.5–5 mg/dL
- **Plausible SI**: 0.2–2 mmol/L
- **Reference mean**: ~2.0 mg/dL

### Sodium, Potassium, Chloride, Bicarbonate
- No conversion needed: mmol/L = mEq/L (numerically identical)
- **Sodium**: 136–145 mEq/L
- **Potassium**: 3.5–5.0 mEq/L
- **Chloride**: 98–106 mEq/L
- **Bicarbonate**: 22–28 mEq/L

## Key Notes

1. **Always test bidirectional**: Never assume multiply or divide. Test both and keep the plausible result.
2. **Wide plausible ranges**: Use extended ranges (not just normal) to avoid converting pathological values.
3. **Convert before rounding**: Threshold detection needs full precision.
4. **Tie-breaking**: When both directions land in range, prefer result closer to reference mean.