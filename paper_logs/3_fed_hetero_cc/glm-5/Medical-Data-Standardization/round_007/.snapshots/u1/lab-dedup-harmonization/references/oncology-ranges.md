# Oncology Panel Ranges and Factors

## Analytes Specific to Oncology Follow-up

| Analyte | Normal US Range | Physiological Bounds | SI Unit | Conversion Factor |
|---------|----------------|---------------------|---------|-------------------|
| LDH | 100-300 U/L | 10-5000 U/L | U/L | None (1:1) |
| Uric_Acid | 2.0-12.0 mg/dL | 0.5-30 mg/dL | μmol/L | ÷ 59.48 |
| Phosphorus | 2.0-6.0 mg/dL | 0.5-12 mg/dL | mmol/L | × 3.097 |
| WBC_Count | 1.0-100.0 ×10³/μL | 0.1-300.0 ×10³/μL | ×10⁹/L | None (1:1) |

## Pathological Value Notes
- **LDH**: Tumor lysis, hemolysis, or tissue damage can push LDH to 500-2000+ U/L. Values >300 are common in oncology.
- **Uric_Acid**: Tumor lysis syndrome can cause levels >12 mg/dL. Values up to 25-30 mg/dL are physiologically possible.
- **WBC_Count**: Chemotherapy can cause neutropenia (<1.0), while infection or leukemia can cause >50.0.
- **Phosphorus**: Tumor lysis causes hyperphosphatemia (>6.0 mg/dL). Values up to 10-12 mg/dL are possible.

## Conversion Validation
When using range-based detection for oncology panels:
1. Check if value is in normal range → assume US units
2. If outside normal, try conversion → check if result is within physiological bounds
3. Accept converted value if within physiological bounds (even if outside normal range)
4. Flag if both original and converted are outside physiological bounds

## Common Pitfalls
- **Rejecting pathological values**: Do not reject converted values just because they exceed normal ranges. Oncology patients frequently have abnormal labs.
- **Using narrow bounds**: Physiological bounds must be wide enough to accommodate extreme but possible values (e.g., LDH up to 5000 in severe tumor lysis).
- **Confusing SI/US for WBC**: WBC count uses identical units in SI and US (×10⁹/L = ×10³/μL). No conversion needed.