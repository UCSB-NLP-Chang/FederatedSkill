# Clinical Unit Conversions & Plausible Ranges

## Common Conversion Factors (SI → Conventional)
| Analyte | SI Unit | Conventional Unit | Factor | Operation |
|---|---|---|---|---|
| Calcium | mmol/L | mg/dL | 0.25 | ÷ |
| Glucose | mmol/L | mg/dL | 0.0555 | ÷ |
| Creatinine | μmol/L | mg/dL | 88.4 | ÷ |
| Total/Direct Bilirubin | μmol/L | mg/dL | 17.1 | ÷ |
| Albumin | g/L | g/dL | 10.0 | ÷ |
| Total Protein | g/L | g/dL | 10.0 | ÷ |
| Hemoglobin | g/L | g/dL | 10.0 | ÷ |
| Ferritin | pmol/L | μg/L (ng/mL) | 2.247 | ÷ |
| Urea/BUN | mmol/L | mg/dL | 0.357 | ÷ (or × 2.8) |
| Cholesterol | mmol/L | mg/dL | 0.02586 | ÷ (or × 38.67) |
| Free_T4 | pmol/L | ng/dL | 12.87 | ÷ |
| Free_T3 | pg/mL | pg/dL | 15.38 | ÷ |
| Total_T4 | nmol/L | μg/dL | 12.87 | ÷ |
| Total_T3 | pmol/L | ng/dL | 64.87 | × |
| PTH | pmol/L | pg/mL | 0.106 | × |
| Vitamin_D_25OH | nmol/L | ng/mL | 2.5 | ÷ |
| Magnesium | mmol/L | mg/dL | 2.43 | × |
| Phosphorus | mmol/L | mg/dL | 3.097 | × |
| Troponin_I / Troponin_T | ng/L | ng/mL | 1000 | ÷ |
| BNP / NT-proBNP | ng/L | pg/mL | 1.0 | None |

## Typical Plausible Ranges
Use these to detect unit mismatches. Ranges are intentionally widened (~20%) to handle boundary cases and clinical/diseased populations.

### Standard Metabolic
- Calcium: 7.0 – 12.0 mg/dL (Conventional) / 0.8 – 3.5 mmol/L (SI)
- Glucose: 27 – 324 mg/dL / 1.5 – 18.0 mmol/L
- Creatinine: 0.3 – 12.0 mg/dL / 40 – 180 μmol/L
- Total Bilirubin: 0.06 – 20.0 mg/dL / 1.0 – 350.0 μmol/L
- Albumin: 2.0 – 6.0 g/dL / 20.0 – 60.0 g/L
- Hemoglobin: 5.0 – 20.0 g/dL / 50.0 – 200.0 g/L
- Ferritin: 45 – 6660 ng/mL / 100.0 – 15000.0 pmol/L
- Phosphorus: 1.5 – 6.0 mg/dL / 0.48 – 1.94 mmol/L

### Thyroid & Endocrine
- Free_T4: 0.5 – 2.5 ng/dL / 6.0 – 30.0 pmol/L
- Free_T3: 1.0 – 8.0 pg/dL / 15.0 – 120.0 pg/mL
- Total_T4: 5.0 – 15.0 μg/dL / 60 – 200 nmol/L
- Total_T3: 50 – 300 ng/dL / 0.8 – 4.5 pmol/L
- PTH: 10 – 150 pg/mL / 1.0 – 15.0 pmol/L
- Vitamin_D_25OH: 20 – 100 ng/mL / 50 – 250 nmol/L
- Magnesium: 1.5 – 3.0 mg/dL / 0.7 – 1.1 mmol/L
- Ionized_Calcium: 3.2 – 8.0 mg/dL / 0.8 – 2.0 mmol/L

### Cardiology
- Troponin_I: 0.01 – 50.0 ng/mL (Conventional) / 10 – 50000 ng/L (SI)
- Troponin_T: 0.01 – 50.0 ng/mL (Conventional) / 10 – 50000 ng/L (SI)
- BNP: 1 – 1000 pg/mL (Conventional & SI equivalent)
- NT-proBNP: 1 – 30000 pg/mL (Conventional & SI equivalent)