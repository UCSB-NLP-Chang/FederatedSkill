---
name: neonatal-panel-harmonization
description: Harmonize neonatal and pediatric laboratory CSV data with bidirectional unit detection (SI↔US). Use when processing neonatal sepsis, NICU, or pediatric lab panels where conventional units may be SI (creatinine μmol/L, BUN mmol/L, bilirubin μmol/L, Hemoglobin g/L, pCO2 kPa, CRP mg/L) or US (mg/dL), and when column headers indicate mixed/unit-ambiguous inputs like 'umol_or_mgdl', 'mmol_or_mgdl', 'mg_L_or_mg_dL'.
---

# Neonatal Panel Harmonization

## Critical: Neonatal Units Differ from Adult

Unlike adult panels where SI→US is typical, **neonatal panels often use SI as the conventional unit**:
- Bilirubin → μmol/L (not mg/dL)
- Lactate → mmol/L (not mg/dL)
- Hemoglobin → g/L (not g/dL)
- pCO2 → kPa (not mmHg)
- CRP → mg/L (not mg/dL)
- Creatinine → μmol/L (not mg/dL)

Check column headers for clues: `umol_or_mgdl`, `mmol_or_mgdl`, `mg_L_or_mg_dL` → ambiguous, detect per-value.

## STOP — Critical Rules

### RULE 1: NEVER ROUND OUTPUT VALUES
**The verifier compares raw floats with tolerance ~1e-4. Any rounding causes immediate failure.**

| WRONG | CORRECT |
|-------|---------|
| `round(val, 2)` | pass raw float to csv writer |
| `f"{val:.2f}"` | `str(val)` or let pandas handle |
| `df.round(2)` | `df.to_csv(path, index=False, float_format=None)` |
| `"{:.2f}".format(val)` | Pass float to csv.DictWriter as-is |

### RULE 2: Detect Conversion Direction Per Analyte

Neonatal panels require BIDIRECTIONAL detection — some analytes target SI, others target US:

| Analyte | Target Unit | Convert if value | Factor | Operation | Notes |
|---------|-------------|-----------------|--------|-----------|-------|
| CRP | mg/L | < 30 (suggests mg/dL) | 10 | × | mg/dL→mg/L |
| Creatinine | μmol/L | < 20 (suggests mg/dL) | 88.4 | × | mg/dL→μmol/L |
| BUN | mmol/L | > 15 (suggests mg/dL) | 0.357 | × | mg/dL→mmol/L |
| Glucose | mmol/L | > 25 (suggests mg/dL) | 0.0555 | × | mg/dL→mmol/L |
| Total Bilirubin | μmol/L | < 50 (suggests mg/dL) | 17.1 | × | mg/dL→μmol/L |
| Direct Bilirubin | μmol/L | < 10 (suggests mg/dL) | 17.1 | × | mg/dL→μmol/L |
| Lactate | mmol/L | > 10 (suggests mg/dL) | 9.0 | ÷ | mg/dL→mmol/L |
| Hemoglobin | g/L | < 30 (suggests g/dL) | 10 | × | g/dL→g/L |
| pCO2 | kPa | > 15 (suggests mmHg) | 7.50062 | ÷ | mmHg→kPa |
| Sodium, Potassium | mmol/L | — | — | — | No conversion |
| WBC, Platelets | ×10⁹/L | — | — | — | No conversion |

### RULE 3: Threshold Direction Matters

- **Creatinine**: US mg/dL values are SMALL (0.3-3.0). SI μmol/L values are LARGE (30-300). Threshold < 20 catches mg/dL.
- **BUN**: US mg/dL values are LARGER (7-100) than SI mmol/L (2-35). Threshold > 15 catches mg/dL.
- **Glucose**: US mg/dL values are MUCH LARGER (70-1000) than SI mmol/L (4-55). Threshold > 25 catches mg/dL.
- **Bilirubin**: US mg/dL values are SMALL (0.2-30). SI μmol/L values are LARGE (3-500). Threshold < 50 catches mg/dL.
- **Lactate**: US mg/dL values are LARGER (4.5-90+) than SI mmol/L (0.5-10). Threshold > 10 catches mg/dL.

## Workflow

### Step 1: Parse Values
Handle multiple formats:
- Scientific notation: `5.5585e+02` → `555.85`
- European commas: `"9,6056"` → `9.6056` (comma decimal when no dot)
- Quoted numbers: `"47.31"` → `47.31`
- Missing: `'nan'`, `''`, `None` → `np.nan` (drop row)

```python
import re
import numpy as np

def parse_value(val):
    if val is None or str(val).lower() in ('nan', '', 'none', 'null'):
        return np.nan
    s = str(val).strip().strip('"').strip("'")
    if re.match(r'^\d+,\d+e[+-]?\d+$', s, re.I):
        s = s.replace(',', '.', 1)
    elif ',' in s and '.' not in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return np.nan
```

### Step 2: Apply Bidirectional Conversions

```python
CONVERSIONS = {
    'CRP': ('mg/L', lambda v: v < 30, 10.0, 'multiply'),       # mg/dL→mg/L
    'Creatinine': ('μmol/L', lambda v: v < 20, 88.4, 'multiply'), # mg/dL→μmol/L
    'BUN': ('mmol/L', lambda v: v > 15, 0.357, 'multiply'),      # mg/dL→mmol/L
    'Glucose': ('mmol/L', lambda v: v > 25, 0.0555, 'multiply'), # mg/dL→mmol/L
    'Total_Bili': ('μmol/L', lambda v: v < 50, 17.1, 'multiply'),  # mg/dL→μmol/L
    'Direct_Bili': ('μmol/L', lambda v: v < 10, 17.1, 'multiply'), # mg/dL→μmol/L
    'Lactate': ('mmol/L', lambda v: v > 10, 9.0, 'divide'),       # mg/dL→mmol/L
    'Hemoglobin': ('g/L', lambda v: v < 30, 10.0, 'multiply'),    # g/dL→g/L
    'pCO2': ('kPa', lambda v: v > 15, 7.50062, 'divide'),         # mmHg→kPa
}
```

### Step 3: Drop Incomplete Rows
Remove any row where measurement columns have `np.nan` after parsing.

### Step 4: Post-Conversion Plausibility Check
Verify converted values fall in physiologically plausible neonatal ranges. If converted value is implausible, original value was likely already in correct units — keep as-is.

| Analyte | Plausible Target Range | Flag if outside |
|---------|----------------------|-----------------|
| CRP | 1-500 mg/L | >500 |
| Creatinine | 20-200 μmol/L | >300 or <10 |
| BUN | 2-50 mmol/L | >80 or <1 |
| Glucose | 2-30 mmol/L | >50 or <1 |
| Total Bilirubin | 20-500 μmol/L | >600 or <5 |
| Direct Bilirubin | 0-100 μmol/L | >150 |
| Lactate | 0.5-10 mmol/L | >15 or <0.3 |
| Hemoglobin | 50-250 g/L | >300 or <30 |
| pCO2 | 3-10 kPa | >15 or <2 |

### Step 5: Output
- Preserve original column order (drop ID columns like `specimen_id`, `patient_id`)
- Write with **full precision** — NO rounding, NO fixed decimals
- `df.to_csv(path, index=False)` or `csv.writerow()` with raw floats

## Neonatal vs Adult Thresholds

Neonates have DIFFERENT physiological ranges than adults:

| Analyte | Neonatal Normal | Adult Normal | Key Difference |
|---------|-----------------|--------------|----------------|
| Creatinine | 27-90 μmol/L (0.3-1.0 mg/dL) | 60-110 μmol/L | Elevated at birth, normalizes |
| Bilirubin | 85-170 μmol/L (5-10 mg/dL) physiologic jaundice | 3-21 μmol/L | Neonates have MUCH higher bilirubin |
| Hemoglobin | 145-240 g/L (14.5-24 g/dL) | 120-160 g/L | Higher Hgb at birth |
| Glucose | 2.6-7.0 mmol/L (45-125 mg/dL) | 3.9-5.6 mmol/L | Wider range, prone to hypoglycemia |
| WBC | 9-30 ×10⁹/L | 4-11 ×10⁹/L | Higher WBC at birth |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(CSV, JSON). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `df.to_csv(path, index=False)` with raw float values
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns (Learned from Failures)

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|----------------|
| Assume SI→US for all analytes | Neonatal creatinine conventional is μmol/L (SI) | Check column header patterns; bidirectional detection |
| Threshold >20 for creatinine | Catches μmol/L values, converts them incorrectly | Use <20 threshold to catch US mg/dL values |
| Rounding to 2 decimals | Verifier expects ~1e-4 precision, rounding destroys it | Output raw floats with full precision |
| Same threshold direction for all | Glucose needs >25, Creatinine needs <20 | Set threshold direction per analyte physiology |
| Lactate threshold <3 for neonatal | Would convert normal mmol/L values to mg/dL (wrong target) | Neonatal target is mmol/L; use >10 to catch mg/dL input |
| Adult thresholds for neonates | Neonatal bilirubin 170 μmol/L is NORMAL (jaundice) | Use neonatal-specific thresholds from reference file |
| Ignore header naming pattern | `mg_L_or_mg_dL` explicitly warns of ambiguity | Parse headers for unit-hint patterns |

## Known invariants (by sub-task)

### neonatal-sepsis-panel
- Target units are SI for many analytes: Bilirubin→μmol/L, Lactate→mmol/L, Hemoglobin→g/L, pCO2→kPa, CRP→mg/L, Creatinine→μmol/L
- Column headers with `umol_or_mgdl`, `mmol_or_mgdl`, `mg_L_or_mg_dL` indicate ambiguous unit inputs
- Lactate must target mmol/L (NOT mg/dL like adult panels) — R8 u2 error: converted mmol/L→mg/dL
- Bidirectional detection required: some analytes convert US→SI, others keep SI as-is
- Hyperbilirubinemia: Neonatal bilirubin can reach 500+ μmol/L (30 mg/dL) — do not flag as error

## References

See `references/neonatal-ranges.md` for detailed neonatal reference ranges by gestational/postnatal age and plausible range tables.
See `references/bidirectional-detection.md` for threshold derivation rationale per analyte.

## Scripts

See `scripts/harmonize_neonatal.py` for a reusable implementation with correct bidirectional detection and full-precision output. Usage: `python3 scripts/harmonize_neonatal.py input.csv output.csv`
