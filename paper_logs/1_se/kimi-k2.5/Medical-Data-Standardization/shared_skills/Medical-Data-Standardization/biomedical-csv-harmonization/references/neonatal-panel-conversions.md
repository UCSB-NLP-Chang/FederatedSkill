# Neonatal Panel Unit Conversions

Extended reference for neonatal sepsis panels and NICU biomarkers. Neonates have different physiologic ranges than adults — do NOT use adult plausibility ranges for detection.

## Critical Differences from Adult Panels

| Analyte | Adult Normal | Neonate Normal | Impact on Detection |
|---------|-------------|----------------|---------------------|
| CRP | < 10 mg/L | < 20 mg/L, sepsis 100-500+ | High values are NORMAL in neonatal sepsis |
| Hemoglobin | 12-16 g/dL | 14-24 g/dL (cord blood) | SI g/L values 140-240 look "too high" |
| Bilirubin | < 1.2 mg/dL | < 15 mg/dL (physiologic jaundice) | Much higher "normal" |
| Glucose | 70-100 mg/dL | 40-100 mg/dL | Hypoglycemia threshold lower |
| BUN | 7-20 mg/dL | 5-25 mg/dL | Similar range |

## Conversion Factors (Neonatal-Specific)

| Analyte | SI Unit | US Unit | Conversion | Detection Rule | Plausible Neonatal Range |
|---------|---------|---------|------------|--------------|--------------------------|
| CRP | mg/L | mg/L | 1:1 (same unit) | — | 0–500 mg/L (sepsis can be 300+) |
| Creatinine | μmol/L | mg/dL | **÷ 88.42** | > 20 | 0.3–2.0 mg/dL (neonates lower) |
| BUN | mmol/L | mg/dL | **× 2.8** | < 10 likely SI, > 30 likely US | 5–50 mg/dL |
| Glucose | mmol/L | mg/dL | **× 18** | < 20 likely SI, > 30 likely US | 20–200 mg/dL |
| Total_Bilirubin | μmol/L | mg/dL | **÷ 17.1** | > 20 likely SI | 0.2–20 mg/dL |
| Direct_Bilirubin | μmol/L | mg/dL | **÷ 17.1** | > 5 likely SI | 0–5 mg/dL |
| Lactate | mmol/L | mg/dL | **× 9.008** | < 5 likely SI, > 20 likely US | 5–40 mg/dL (sepsis higher) |
| Hemoglobin | **g/L** | **g/dL** | **÷ 10** | > 50 likely g/L, 5–25 likely g/dL | 10–25 g/dL (neonatal) |
| Sodium | mmol/L | mEq/L | 1:1 | — | 120–160 mEq/L |
| Potassium | mmol/L | mEq/L | 1:1 | — | 3.5–7.0 mEq/L |
| Platelet_Count | ×10⁹/L | ×10³/μL | 1:1 (same) | — | 150–600 ×10³/μL |
| WBC_Count | ×10⁹/L | ×10³/μL | 1:1 (same) | — | 5–30 ×10³/μL |
| pCO2 | kPa | mmHg | **× 7.5** | < 20 likely kPa | 30–60 mmHg |

## Critical Corrections from Failed Run

### Lactate Conversion
**WRONG**: Using ×9 (approximate) or confusing mg/dL↔mmol/L direction.
**CORRECT**: MW lactate = 90.08 g/mol. mmol/L × 9.008 = mg/dL.

Example: 1.5 mmol/L × 9.008 = 13.51 mg/dL (not 13.5 or 135)

### Hemoglobin Unit Confusion
**WRONG**: Using mmol/L → g/dL conversion (÷1.613 or ×0.6206) — this is for molar hemoglobin in some countries.
**CORRECT**: Neonatal panels typically use **g/L → g/dL** (÷10). Input values like `137.635` or `94.383` are g/L, not mmol/L.

| If input is | Value example | Likely unit | Conversion |
|-------------|-------------|-------------|------------|
| 137.635 | 137.635 | g/L | ÷ 10 = 13.76 g/dL |
| 9.44 | 9.44 | g/dL | No conversion |
| 5.95 | 5.95 | mmol/L (rare) | × 1.613? No — likely already g/dL if this low |

**Detection**: Values 80–250 are almost certainly g/L. Values 10–25 could be either g/dL (correct) or pathologically low g/L (rare). Use ÷10 when in doubt for neonatal panels.

### CRP Detection (Critical Error in Trace)
**Problem**: Agent used adult detection threshold (CRP > 10 = assume mg/L, no conversion). But neonatal CRP of 300+ is SEPSIS, not "already in target units."
**CORRECT**: CRP is **ALREADY in mg/L** in both SI and US. The unit is the same. Do NOT apply conversion factors to CRP.

The column name `CRP_mg_L_or_mg_dL` is misleading — CRP is never in mg/dL clinically (would be 0.1–5 mg/dL, implausible).

## Detection Priority (Critical for Neonatal)

**ALWAYS check SI conversion BEFORE checking if already in US units** for these analytes:
- Creatinine: μmol/L values (20–1000) are much larger than mg/dL (0.3–2.0)
- Bilirubin: μmol/L values (20–400) are larger than mg/dL (0.5–20)
- Hemoglobin: g/L values (140–240) are larger than g/dL (14–24)

**Order matters**:
```python
# WRONG - catches 200 mg/dL glucose as "already US" when it's actually 200 mmol/L (impossible)
if 70 <= val <= 600:  # "Plausible US range"
    return val
return val * 18  # Never reached for 200 mmol/L

# CORRECT - check if SI first, validate converted
if val > 30:  # Likely SI mmol/L
    converted = val * 18
    if 20 <= converted <= 600:
        return converted
if 20 <= val <= 600:  # Already US
    return val
```

## Neonatal-Specific Plausibility Ranges

Use these for validation, NOT adult ranges:

| Analyte | Severe Hypo | Normal | Severe Hyper | Notes |
|---------|-------------|--------|--------------|-------|
| CRP | 0 | < 10 | 500+ | Sepsis workup panels |
| Creatinine | < 0.3 | 0.5–1.0 | > 2.0 | Neonates lower than adults |
| BUN | < 3 | 7–20 | > 50 | Renal failure |
| Glucose | < 20 | 50–90 | > 200 | Hypoglycemia common in NICU |
| Total Bilirubin | < 0.5 | 5–15 | > 20 | Phototherapy threshold |
| Lactate | < 5 | 10–20 | > 40 | Shock/sepsis indicator |
| Hemoglobin | < 10 | 15–22 | > 25 | Polycythemia vs anemia |
| Sodium | < 120 | 135–145 | > 160 | Common electrolyte issue |
| Potassium | < 3.0 | 4.0–6.0 | > 7.5 | Critical in NICU |
| Platelets | < 50 | 150–400 | > 800 | Thrombocytopenia common |

## Common Pitfalls

### Pitfall 1: Adult detection thresholds
```python
# WRONG - uses adult CRP range
if val > 10:  # Adult "elevated"
    return val  # Passes through 300 unconverted

# CORRECT - CRP is already mg/L, or if confused, check unit labels
# Neonatal CRP 300 = SEPSIS, not "already converted"
```

### Pitfall 2: Hemoglobin unit confusion
```python
# WRONG - treats 103.333 as mmol/L
hgb_gdl = 103.333 / 1.613  # = 64 g/dL (impossible!)

# CORRECT - recognizes as g/L
hgb_gdl = 103.333 / 10  # = 10.33 g/dL (plausible)
```

### Pitfall 3: Lactate factor approximation
```python
# WRONG - uses ×9 (close but not exact)
lactate_mgdl = 1.5 * 9  # = 13.5

# CORRECT - use molecular weight
lactate_mgdl = 1.5 * 9.008  # = 13.51
```

## Verification Checklist for Neonatal Panels

- [ ] CRP values 0–500+ accepted as mg/L (no conversion)
- [ ] Hemoglobin: g/L ÷ 10 = g/dL (not mmol/L conversion)
- [ ] Lactate: × 9.008 (not ×9 or ÷9)
- [ ] Creatinine: ÷ 88.42 for μmol/L → mg/dL
- [ ] Bilirubin: ÷ 17.1 for μmol/L → mg/dL  
- [ ] Glucose: × 18 for mmol/L → mg/dL (check < 20 threshold)
- [ ] All values plausible for neonates, not adults
- [ ] No row with ANY missing values kept
- [ ] specimen_id removed from output
- [ ] Exactly 2 decimal places in all values
