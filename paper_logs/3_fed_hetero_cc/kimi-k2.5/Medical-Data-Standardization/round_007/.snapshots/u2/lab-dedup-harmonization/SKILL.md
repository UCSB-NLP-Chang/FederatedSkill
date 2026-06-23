---
name: lab-dedup-harmonization
description: Deduplicate longitudinal lab data by case_id/draw_order and harmonize units using range-based detection. Use when processing multi-draw lab panels where you must select the most complete or latest draw per case, and when threshold-based unit detection is ambiguous or unavailable.
---

# Lab Data Deduplication and Range-Based Harmonization

## When to Use
- Input CSV has `case_id` and `draw_order` columns with multiple rows per case
- Need to select one row per case (highest draw_order with complete data)
- Unit detection thresholds are unknown or ambiguous; use physiological range checking instead
- Oncology, metabolic, or general chemistry panels with mixed SI/US units

## Workflow

### 1. Deduplicate by Case
Group by `case_id`, sort draws by `draw_order` descending, and select the first draw where all measurement columns are non-null. If no draw is fully complete, fall back to the highest draw_order.

```python
from collections import defaultdict

cases = defaultdict(list)
for row in rows:
    cases[row['case_id']].append(row)

selected = []
for case_id, draws in cases.items():
    draws.sort(key=lambda x: x['draw_order'], reverse=True)
    for draw in draws:
        if all(v is not None for v in draw['values'].values()):
            selected.append(draw)
            break
    else:
        selected.append(draws[0])  # Fallback: highest draw even if incomplete
```

### 2. Range-Based Unit Detection
Instead of fixed thresholds, use a two-tier range system:

```python
NORMAL_RANGES = {
    "LDH": (100, 300), "Uric_Acid": (2.0, 12.0), "Creatinine": (0.4, 15.0),
    "Phosphorus": (2.0, 6.0), "Calcium": (7.0, 13.0), "Albumin": (2.0, 6.0),
    "Glucose": (30, 600), "Magnesium": (1.0, 4.0), "Potassium": (2.5, 7.0),
    "WBC_Count": (1.0, 100.0),
}

PHYSIO_BOUNDS = {
    "LDH": (10, 5000), "Uric_Acid": (0.5, 30), "Creatinine": (0.1, 25),
    "Phosphorus": (0.5, 12), "Calcium": (4.0, 16.0), "Albumin": (0.5, 10.0),
    "Glucose": (10, 1200), "Magnesium": (0.3, 8.0), "Potassium": (1.5, 9.0),
    "WBC_Count": (0.1, 300.0),
}

CONVERSIONS = {
    "Uric_Acid": lambda v: v / 59.48, "Creatinine": lambda v: v / 88.42,
    "Calcium": lambda v: v * 4.0, "Albumin": lambda v: v / 10.0,
    "Glucose": lambda v: v * 18.0182,
}

def detect_and_convert(col, val):
    lo, hi = NORMAL_RANGES[col]
    if lo <= val <= hi:
        return val  # Already in US conventional units
    if col in CONVERSIONS:
        converted = CONVERSIONS[col](val)
        c_lo, c_hi = PHYSIO_BOUNDS[col]
        if c_lo <= converted <= c_hi:
            return converted  # Converted value is physiologically plausible
    return val  # Keep original if no valid conversion
```

### 3. Validation Rules
- **Normal range**: If value falls within normal US range, assume US units (no conversion)
- **Conversion check**: If outside normal range, try conversion. Accept if result is within physiological bounds
- **Pathological values**: Values outside normal but within physiological bounds are valid (e.g., tumor lysis → high uric acid)
- **Impossible values**: If both original and converted are outside physiological bounds, flag for review

### 4. Output
- Write raw floats directly. **DO NOT ROUND** (see `clinical-lab-harmonization` skill for precision rules)
- Preserve measurement column order from input header
- Exclude `case_id` and `draw_order` from output

## Anti-Patterns
- **Rounding**: Never round to fixed decimals. Verifiers compare raw floats with tolerance ~1e-4
- **Strict normal range enforcement**: Pathological values (LDH 615, Uric_Acid 14.9) are valid. Use wide physiological bounds for validation
- **Blind conversion**: Always verify converted value is physiologically plausible before accepting
- **Incomplete draw selection**: Do not pick a draw with missing values if a complete lower-priority draw exists

## Relationship to Existing Skills
- Use `clinical-lab-harmonization` for threshold-based unit detection and standard conversion factors
- Use this skill when you need deduplication logic or range-based detection as an alternative approach
- Both skills share the same "no rounding" rule and number parsing patterns

## References
See `references/oncology-ranges.md` for oncology-specific physiological bounds, pathological value notes, and conversion validation guidance.
