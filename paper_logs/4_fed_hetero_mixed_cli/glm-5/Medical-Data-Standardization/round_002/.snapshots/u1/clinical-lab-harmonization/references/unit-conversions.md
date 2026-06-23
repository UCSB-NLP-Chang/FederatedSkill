# Clinical Lab Unit Conversions

## Detection and Conversion Rules

Use bidirectional testing: for each value, test both `value * factor` and `value / factor`, keep the result that lands inside the plausible conventional range.

**Special case - Glucose**: SI values (mmol/L) are numerically smaller than conventional (mg/dL). If value < 30, multiply by 18 to test if it was mmol/L.

## Electrolytes & Metabolites

### Glucose
- **Conventional**: mg/dL
- **SI**: mmol/L
- **Conversion**: mmol/L × 18.0 → mg/dL
- **Plausible conventional**: 30–700 mg/dL (includes DKA)
- **Plausible SI**: 2–40 mmol/L
- **Reference mean**: ~100 mg/dL (fasting normal)
- **CRITICAL**: SI values are numerically SMALLER. A value of 5.5 is likely mmol/L (→ 99 mg/dL), not an extremely low mg/dL.

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

## Hepatic Panel

### Total Bilirubin
- **Conventional**: mg/dL
- **SI**: μmol/L
- **Conversion**: μmol/L ÷ 17.1 → mg/dL
- **Plausible conventional**: 0.1–30 mg/dL (includes severe jaundice, cholestasis)
- **Plausible SI**: 2–500 μmol/L
- **Reference mean**: ~0.8 mg/dL

### Direct (Conjugated) Bilirubin
- **Conventional**: mg/dL
- **SI**: μmol/L
- **Conversion**: μmol/L ÷ 17.1 → mg/dL
- **Plausible conventional**: 0.0–10 mg/dL
- **Plausible SI**: 0–170 μmol/L
- **Reference mean**: ~0.2 mg/dL

### Albumin
- **Conventional**: g/dL
- **SI**: g/L
- **Conversion**: g/L ÷ 10 → g/dL
- **Plausible conventional**: 1.0–6.0 g/dL (includes severe hypoalbuminemia)
- **Plausible SI**: 10–60 g/L
- **Reference mean**: ~4.0 g/dL

### Total Protein
- **Conventional**: g/dL
- **SI**: g/L
- **Conversion**: g/L ÷ 10 → g/dL
- **Plausible conventional**: 3.0–12.0 g/dL
- **Plausible SI**: 30–120 g/L
- **Reference mean**: ~7.0 g/dL

### Hemoglobin
- **Conventional**: g/dL
- **SI**: g/L
- **Conversion**: g/L ÷ 10 → g/dL
- **Plausible conventional**: 5.0–20.0 g/dL (includes severe anemia, polycythemia)
- **Plausible SI**: 50–200 g/L
- **Reference mean**: ~14.0 g/dL (varies by sex)

### AST, ALT, ALP, GGT (Liver Enzymes)
- No conversion needed: U/L is standard internationally
- **AST**: 10–40 U/L (can exceed 1000 in acute hepatitis)
- **ALT**: 7–56 U/L (can exceed 1000 in acute hepatitis)
- **ALP**: 44–147 U/L (elevated in cholestasis, bone disease)
- **GGT**: 9–48 U/L (sensitive for biliary disease)

### INR (International Normalized Ratio)
- No conversion needed: dimensionless ratio
- **Plausible range**: 0.8–10.0 (therapeutic anticoagulation 2.0–3.5)

### Ammonia
- **Conventional**: μg/dL
- **SI**: μmol/L
- **Conversion**: μmol/L × 1.7 → μg/dL
- **Plausible conventional**: 10–200 μg/dL (hepatic encephalopathy)
- **Plausible SI**: 5–120 μmol/L

### Bile Acids
- **Conventional**: μmol/L (often same as SI)
- **Plausible**: 1–300 μmol/L (cholestasis)

### AFP (Alpha-Fetoprotein)
- No conversion needed: ng/mL is standard
- **Plausible**: 0–100,000+ ng/mL (HCC marker)

### Ferritin
- No conversion needed: ng/mL is standard
- **Plausible**: 5–10,000+ ng/mL (iron overload, inflammation)

### Platelets
- No conversion needed: ×10⁹/L or ×10³/μL (numerically equivalent)
- **Plausible**: 5–1000 ×10⁹/L

## Key Notes

1. **Always test bidirectional**: Never assume multiply or divide. Test both and keep the plausible result.
2. **Glucose is special**: SI values are numerically smaller than conventional. Test `value × 18` first if value < 30.
3. **Wide plausible ranges**: Use extended ranges (not just normal) to avoid converting pathological values.
4. **Convert before rounding**: Threshold detection needs full precision.
5. **Tie-breaking**: When both directions land in range, prefer result closer to reference mean.
