---
name: clinical-data-harmonization
description: Harmonize clinical/lab data files by parsing mixed number formats (scientific notation, comma decimals), converting SI units to US conventional units, handling missing values, and formatting output. Use when processing CSV or JSON files with electrolyte panels, hepatic panels, thyroid panels, cardiac markers, respiratory/blood gas panels, oncology panels, lab results, or other clinical measurements that need standardization.
---

# Clinical Data Harmonization

## ⚠️ CRITICAL: Run Tests Before Completion

**FAILURE TO RUN TESTS IS THE #1 CAUSE OF FAILED TASKS.**

**MANDATORY STEPS BEFORE CLAIMING SUCCESS:**
1. Run `pytest test_output.py -v` or `python3 -m pytest test_output.py -v`
2. If test file not found, try: `pytest /root/environment/test_output.py -v` or `pytest -v` (auto-discovery)
3. Verify ALL tests pass with zero failures
4. If tests fail, read error messages, fix issues, and re-run
5. ONLY after tests pass may you claim completion

**WHAT DOES NOT COUNT AS VERIFICATION:**
- Reading the output file and manually checking values ❌
- "The output looks correct" ❌
- Spot-checking a few conversions ❌
- Assuming the script worked because it ran without errors ❌
- Glob search finding no test files (tests may still exist) ❌

**NEVER DELETE PROCESSING SCRIPTS UNTIL TESTS PASS.** If tests fail, you need the script to debug and fix issues.

## Workflow

1. **Read and inspect input structure**
   - Identify ALL columns including identifier columns (e.g., patient_id, encounter_id, subject_id, record_id, sample_id, patient_code)
   - Store identifier column names before any processing
   - Note which columns must be preserved vs transformed
   - Check for output template file - use its header order for output
   - For JSON input: identify nested structure, status fields, and record filtering requirements

2. **Preserve identifier columns (CRITICAL)**
   - Identifier columns (patient_id, encounter_id, subject_id, record_id, sample_id, patient_code, etc.) MUST appear in output unless template explicitly excludes them
   - Write identifier columns to output unchanged before processing measurement columns
   - After writing output, verify all identifier columns are present
   - This is a common cause of test failures - never omit identifier columns unless explicitly excluded

3. **Filter records by status (JSON input)**
   - JSON data may contain status fields (e.g., "draft", "final", "preliminary")
   - Filter to keep only records with appropriate status (typically "final")
   - Check notes/comments fields for filtering instructions

4. **Parse mixed number formats**
   - Scientific notation: `5.6949e+00` → parse with `float()`
   - Comma decimals: `"142,0205"` → replace comma with dot, then parse
   - Quoted values: strip quotes before parsing
   - Handle `nan`, empty strings, and null values explicitly

5. **Detect and convert SI units**
   - Use value thresholds to infer unit (SI vs US conventional)
   - Common thresholds (see `references/unit-conversions.md` for full list):
     - Magnesium: > 2.5 suggests mmol/L → multiply by 0.411 for mg/dL (NOT >1.5)
     - Calcium: > 15.0 suggests mmol/L → multiply by 4.0 for mg/dL
     - Glucose: < 30.0 suggests mmol/L → multiply by 18.0 for mg/dL
     - Creatinine: > 20.0 suggests μmol/L → divide by 88.4 for mg/dL
     - Bilirubin: > 20.0 suggests μmol/L → divide by 17.1 for mg/dL
     - Albumin/Protein/Hemoglobin: > 20.0 suggests g/L → divide by 10 for g/dL
     - Free T4: > 5.0 suggests pmol/L → divide by 12.87 for ng/dL
     - PTH: > 500 suggests pmol/L → multiply by 0.106 for pg/mL
     - WBC_Count: < 100 suggests x10^9/L → multiply by 1000 for cells/µL
     - pO2/pCO2: < 20 suggests kPa → multiply by 7.5 for mmHg
     - Lactate: < 5 suggests mmol/L → multiply by 9.0 for mg/dL

6. **Handle missing values**
   - Decide per-task: drop rows, impute, or leave blank
   - Document which rows were dropped and why

7. **Format output**
   - Round to specified decimal places (commonly 2)
   - Use format specifier like `f"{value:.2f}"` to ensure exactly N decimal places
   - Use standard decimal format (no scientific notation, no commas in decimals)
   - If template provided, match template header order exactly

8. **Validate before claiming completion (MANDATORY)**
   - Run `pytest test_output.py -v` or equivalent test command
   - If tests not found, try `pytest -v` for auto-discovery or check `/root/environment/` directory
   - If tests fail, read error messages and fix issues before retry
   - Verify output has expected columns (especially identifiers)
   - Check row counts match expectations
   - **Do NOT claim success until tests pass**

## Common Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| Claiming success without running tests | Tests catch schema mismatches, missing columns, format errors | Run `pytest test_output.py -v` and verify all pass |
| Manual output verification | Human inspection misses structural errors | Trust the test suite, not your eyes |
| Glob search for test files then giving up | Test files may exist but not be found by glob | Run pytest directly; it auto-discovers tests |
| Dropping identifier columns | Tests expect patient_id, encounter_id, etc. | Preserve all identifier columns unless explicitly excluded |
| Deleting scripts before tests pass | Cannot debug when tests fail | Keep scripts until tests pass |
| Assuming uniform format | Clinical data mixes formats in same column | Handle all format variants explicitly |
| Wrong decimal places | `round()` produces `5.6` instead of `5.60` | Use `f"{value:.2f}"` format |
| Incorrect thresholds | Magnesium threshold is >2.5, not >1.5 | Check `references/unit-conversions.md` for correct thresholds |

## Troubleshooting

| Issue | Check |
|-------|-------|
| Test file not found by glob | Run `pytest -v` directly; check `/root/environment/` directory |
| Test failures | Run tests and read error output; compare output columns to expected schema |
| Missing identifier column | Re-read input to get column names; ensure all (patient_id, encounter_id, record_id, sample_id, patient_code, etc.) are written to output |
| Wrong conversions | Verify threshold logic; check if value is already in target unit; verify multiply vs divide direction |
| Parse errors | Inspect raw values for unexpected formats (currency symbols, text) |
| Row count mismatch | Review missing value handling logic; check for empty rows; verify status filtering for JSON input |
| Decimal place issues | Use `f"{value:.2f}"` instead of `round(value, 2)` |
| Values absurdly high/low | Re-check conversion direction; SI values may be larger OR smaller than US depending on analyte |
| Magnesium still wrong | Threshold should be >2.5, not >1.5; SI values (mmol/L) are numerically smaller than US (mg/dL) |
| Tests pass locally but fail in verifier | Ensure output file is in correct location; check for extra/missing rows; verify all identifier columns present |
| Need to debug but script deleted | Re-create script; in future, keep scripts until tests pass |

## Reference

See `references/unit-conversions.md` for detailed conversion factors and thresholds for common lab analytes including electrolytes, hepatic panel, thyroid panel, cardiac markers, respiratory/blood gas panel, oncology markers, and renal/metabolic values.