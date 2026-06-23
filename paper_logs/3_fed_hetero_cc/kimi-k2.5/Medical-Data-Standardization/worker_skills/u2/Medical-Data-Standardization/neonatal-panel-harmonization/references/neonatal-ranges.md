# Neonatal Reference Ranges by Age

## Target Units & Plausible Ranges

Neonatal panels frequently use SI units as the standard reporting format.

| Analyte | Target Unit | Plausible Range | Critical Low | Critical High |
|---------|-------------|-----------------|--------------|---------------|
| CRP | mg/L | 0.1-200 | <0.1 | >200 |
| Creatinine | μmol/L | 20-200 | <10 | >300 |
| BUN | mmol/L | 2-50 | <1 | >80 |
| Glucose | mmol/L | 2-30 | <1 | >50 |
| Total_Bilirubin | μmol/L | 20-500 | <5 | >600 |
| Direct_Bilirubin | μmol/L | 0-100 | — | >150 |
| Lactate | mmol/L | 0.5-10 | <0.3 | >15 |
| Platelet_Count | 10⁹/L | 150-450 | <50 | >800 |
| WBC_Count | 10⁹/L | 5-30 | <2 | >50 |
| Hemoglobin | g/L | 50-250 | <30 | >300 |
| pCO2 | kPa | 3-10 | <2 | >15 |
| Sodium | mmol/L | 130-150 | <120 | >160 |
| Potassium | mmol/L | 3.5-5.5 | <2.5 | >7.0 |

## Creatinine (μmol/L)

| Age | Premature | Term | Notes |
|-----|-----------|------|-------|
| 0-7 days | 27-93 | 27-66 | Maternal contribution |
| 1-4 weeks | 18-52 | 18-35 | Rapid decline |
| 1-6 months | 15-40 | 15-35 | Adult levels approached |

**Conversion**: mg/dL × 88.4 = μmol/L

## BUN (mmol/L)

| Age | Range | Notes |
|-----|-------|-------|
| 0-7 days | 1.1-4.6 | Low protein intake |
| 1-4 weeks | 1.4-6.4 | Rising with feeds |
| 1-6 months | 1.8-6.4 | Near adult |

**Conversion**: mg/dL × 0.357 = mmol/L

## Bilirubin (μmol/L)

### Total Bilirubin

| Age/Status | Range | Critical |
|------------|-------|----------|
| Cord blood | < 34 | — |
| 24 hours | < 102 | > 120 (investigate) |
| 48 hours | < 154 | > 200 (treatment threshold) |
| 3-5 days (term) | < 205 | > 255 (phototherapy) |
| 3-5 days (preterm) | < 257 | > 340 (exchange transfusion) |

### Direct (Conjugated) Bilirubin

| Status | Range | Critical |
|--------|-------|----------|
| Normal | < 17 | — |
| Conjugated hyperbilirubinemia | > 34 | Suspect cholestasis |

**Conversion**: mg/dL × 17.1 = μmol/L

## Glucose (mmol/L)

| Status | Range | Action Threshold |
|--------|-------|------------------|
| Normal | 2.8-4.4 | — |
| Transitional hypoglycemia | 1.7-2.8 | Monitor, feed |
| Hypoglycemia | < 1.7 (< 30 mg/dL) | Treat immediately |
| Hyperglycemia | > 11.1 (> 200 mg/dL) | Common in stressed neonates |

**Conversion**: mg/dL × 0.0555 = mmol/L (or ÷ 18)

## Hemoglobin (g/L)

| Age | Range | Notes |
|-----|-------|-------|
| Cord blood | 140-200 | Higher than adult |
| 24 hours | 160-240 | Physiologic polycythemia |
| 1 week | 130-200 | Hemolysis of fetal Hb |
| 1 month | 100-140 | Physiologic anemia |

**Conversion**: g/dL × 10 = g/L

## Lactate (mmol/L)

| Status | mmol/L | mg/dL (×9) |
|--------|--------|------------|
| Normal | 0.5-2.0 | 4.5-18 |
| Mild elevation | 2.0-4.0 | 18-36 |
| Lactic acidosis | > 4.0 | > 36 |
| Severe shock | > 10.0 | > 90 |

**Conversion**: mg/dL ÷ 9.0 = mmol/L

**Key threshold**: Use >10 to detect mg/dL input. Values 3-10 are ambiguous (could be elevated mmol/L or moderate mg/dL). Values >10 are almost certainly mg/dL (10 mmol/L would be 90 mg/dL, which is severe lactic acidosis — rare but survivable; 10 mg/dL is only mild elevation).

## CRP (mg/L)

| Status | Range | Notes |
|--------|-------|-------|
| Normal | < 10 | — |
| Mild inflammation | 10-40 | — |
| Sepsis | 40-200 | Variable, not reliable early |
| Severe inflammation | > 200 | Late marker |

Note: 1 mg/dL = 10 mg/L. Some labs report CRP in mg/dL (0.1-20 range).

## WBC and Platelets

No conversion needed — SI (×10⁹/L) and US (×10³/μL) are numerically identical.

| Cell Type | Neonatal Range | Critical Low |
|-----------|----------------|---------------|
| WBC | 9.0-30.0 ×10⁹/L | < 5.0 (neutropenia) |
| Platelets | 150-400 ×10⁹/L | < 100 (thrombocytopenia) |

## pCO2 (kPa)

| Status | kPa | mmHg | Notes |
|--------|-----|------|-------|
| Normal | 4.7-6.0 | 35-45 | — |
| Hypocapnia | < 4.0 | < 30 | Hyperventilation |
| Hypercapnia | > 6.7 | > 50 | Respiratory distress |
| Severe | > 8.0 | > 60 | Ventilatory failure |

**Conversion**: mmHg ÷ 7.50062 = kPa; kPa × 7.50062 = mmHg

## Common Neonatal-Specific Pitfalls

- **Bilirubin phototherapy thresholds**: Neonatal jaundice treatment starts at ~200-300 μmol/L. Values in this range are pathological but valid.
- **Glucose hypoglycemia**: Neonatal glucose <40 mg/dL (<2.2 mmol/L) is common and valid. Do not flag as error.
- **Creatinine maternal transfer**: Newborns may have elevated creatinine (up to 1.5 mg/dL, ~130 μmol/L) from maternal transfer. Valid.
- **WBC/Platelet volatility**: Neonatal counts fluctuate rapidly. Wide ranges are normal.
