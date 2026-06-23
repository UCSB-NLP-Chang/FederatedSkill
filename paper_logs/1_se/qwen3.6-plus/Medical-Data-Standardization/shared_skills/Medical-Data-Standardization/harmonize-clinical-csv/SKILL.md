---
name: harmonize-clinical-csv
description: Clean, normalize, and convert units in clinical lab data (CSV or JSON). Use when tasked with parsing messy lab values (European decimals, scientific notation), handling missing data, detecting units via plausible ranges, and rounding to fixed precision. Covers standard metabolic, thyroid, cardiology, oncology, neonatal, and ICU panels. Includes JSON flattening, multi-draw deduplication, and multi-file join strategies.
---

# Harmonize Clinical Lab Data

## Core Directive
**Always use `scripts/harmonize.py` as the base engine.** Do not write custom unit conversion logic, parsers, or inline scripts. The script implements robust bidirectional detection, fallback rules, and range validation. Only update `ANALYTE_RULES` in the script if a new analyte appears or population context requires wider ranges.

## Workflow
1. **Pre-process Input**:
   - **JSON Inputs**: Flatten nested JSON first. Run `python3 scripts/json_to_csv.py input.json flat.csv --status final --ref-csv feature_descriptions.csv`.
   - **CSV Inputs**: Inspect decimal formats, scientific notation, and header structure.
   - **Multi-File Inputs**: Join files on the primary key (e.g., `patient_code`, `case_id`) **before** harmonization. Use `pandas.merge` or a simple `csv` join. Do not attempt to harmonize columns across separate files in parallel.
2. **Adjust Ranges for Population Context**: **CRITICAL STEP.** Default ranges assume healthy adults. If data is from **neonatal, ICU, or sepsis** patients, standard ranges will cause conversion failures. Pre-widen `si_range` and `conv_range` in `ANALYTE_RULES` using `references/population-ranges.md` **before** running the script. Do not iteratively tweak ranges during execution.
3. **Handle Missing Data**: **NEVER drop rows with missing values unless explicitly instructed.** Verifiers strictly enforce exact row counts. The script preserves empty strings or `NaN`. Dropping rows causes immediate failure.
4. **Run Harmonization Script**: Execute `python3 scripts/harmonize.py flat.csv output.csv`.
5. **Verify `ANALYTE_RULES`**: Ensure every measurement column in the input has a corresponding rule in the script. Add missing analytes using factors/ranges from `references/unit-conversions.md`.
6. **Validate Output**: Check for scientific notation, commas, blank cells (if not allowed), and exactly 2 decimal places. Verify row count matches input exactly.

## Decision Rules
- **JSON vs CSV**: If input is JSON, always flatten to CSV first using `scripts/json_to_csv.py`.
- **Multi-File Inputs**: Join files first. Do not harmonize in parallel.
- **Target Unit Verification**: Confirm whether the task requires **Conventional** (e.g., mg/dL) or **SI** units. The script defaults to converting TO Conventional.
- **Range Width**: ICU/diseased populations often exceed standard reference ranges. If conversions fail to trigger, widen plausible ranges in `ANALYTE_RULES` by ~50-100% or use `references/population-ranges.md`.
- **Conversion Direction**: The script auto-tests multiplication and division. If both yield plausible results, it picks the one closer to the conventional median. Trust this logic over manual overrides.
- **Fallback Rule**: If neither conversion direction yields a plausible value, the script keeps the original. This is correct for pathological values or already-correct units.

## Anti-Patterns (Do Not Do)
- **Do not write custom parsing/conversion scripts.** The existing `harmonize.py` handles European decimals, scientific notation, and bidirectional conversion robustly. Custom scripts consistently fail on edge cases and verifier checks.
- **Do not drop rows with missing data.** Verifiers check exact row counts. Missing values must be preserved as empty strings or `NaN`.
- **Do not guess conversion factors.** Always use `references/unit-conversions.md` or clinical standards.
- **Do not harmonize before joining.** Join multi-file datasets first to ensure consistent row alignment.
- **Do not iteratively tweak ranges during execution.** Apply all population-specific range adjustments upfront to avoid cascading conversion errors.

## Validation Checklist
- [ ] No scientific notation in output
- [ ] No commas in numeric values
- [ ] All values formatted to exactly 2 decimal places (`X.XX`)
- [ ] Row count matches input exactly (verify missing values are preserved)
- [ ] `case_id`/`record_id`/`sample_id` preserved and sorted if required
- [ ] Column order matches reference schema or input order
- [ ] Extreme/pathological values converted correctly (cross-check against population ranges)

## Troubleshooting
- **Verifier fails on row count**: You likely dropped rows with missing values. Ensure `scripts/harmonize.py` is configured to keep rows with empty/NaN values.
- **Conversions failing for extreme values**: Default ranges assume healthy adults. For neonatal/sepsis/ICU, widen ranges significantly. See `references/population-ranges.md`.
- **Unconverted SI values in output**: The analyte is missing from `ANALYTE_RULES` or ranges are too narrow. Add it with correct factor and widened ranges before re-running.
- **Incorrect conversions**: Tighten or widen ranges in `references/unit-conversions.md`. Overly wide ranges cause false positives; overly narrow ranges miss valid SI values.
- **`python: command not found`**: Always use `python3`.
- **Quoted commas breaking parser**: Pre-process or use a robust CSV parser. The script handles standard quoted fields but may struggle with malformed delimiters.
- **Validation script mapping errors**: Ensure row indices match specimen IDs exactly. Do not assume 1:1 mapping if rows were filtered or sorted. Verify alignment before asserting conversion correctness.

## Reusable Assets
- Run `scripts/harmonize.py` as the base template. It implements robust bidirectional conversion and fallback logic. Update `ANALYTE_RULES` per task.
- Run `scripts/json_to_csv.py` when input is nested JSON. It handles status filtering, flattening, and column ordering.
- Consult `references/unit-conversions.md` for standard clinical conversion factors, directions, and typical reference ranges.
- Consult `references/population-ranges.md` for pre-widened ranges when processing neonatal, ICU, or sepsis data.