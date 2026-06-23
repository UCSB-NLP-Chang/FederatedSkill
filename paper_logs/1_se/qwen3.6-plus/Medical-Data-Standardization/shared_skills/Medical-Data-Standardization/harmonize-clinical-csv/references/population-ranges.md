# Population-Specific Plausible Ranges

Use these widened ranges for `ANALYTE_RULES` in `scripts/harmonize.py` when processing data from neonatal, ICU, or sepsis populations. Standard adult ranges will cause false negatives (values kept in SI instead of converting).

## Neonatal / Sepsis / ICU Adjustments
Replace the default `si_range` and `conv_range` tuples in `harmonize.py` with these values before running:

| Analyte | SI Range (Widened) | Conventional Range (Widened) | Notes |
|---|---|---|---|
| Glucose | (1.0, 45.0) | (18, 800) | Neonatal hypoglycemia & stress hyperglycemia |
| Total Bilirubin | (1.0, 450.0) | (0.05, 26.0) | Neonatal jaundice often exceeds 20 mg/dL |
| Direct Bilirubin | (1.0, 150.0) | (0.05, 9.0) | Cholestasis in sepsis |
| pCO2 | (2.0, 12.0) | (15, 90) | Respiratory distress / ventilation |
| Lactate | (0.2, 15.0) | (1.8, 135.0) | Severe sepsis / shock |
| Creatinine | (20, 250) | (0.2, 15.0) | Neonatal renal immaturity / AKI |
| Hemoglobin | (40, 220) | (4.0, 22.0) | Anemia of prematurity / transfusion |
| Potassium | (2.0, 8.0) | (2.0, 8.0) | Electrolyte shifts in sepsis |

## Application Rule
1. Open `scripts/harmonize.py`.
2. Locate `ANALYTE_RULES`.
3. Update the `si_range` and `conv_range` tuples for the relevant analytes.
4. Run the script. Do not iteratively tweak ranges during execution; apply all known population adjustments upfront.