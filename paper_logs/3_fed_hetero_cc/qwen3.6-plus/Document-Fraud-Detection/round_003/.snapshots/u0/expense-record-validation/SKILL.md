---
name: expense-record-validation
description: Cross-reference and validate expense claims or records against employee directories and approval lists. Handles multi-format inputs (PDF, XLSX, CSV), fuzzy name matching for typos, and structured discrepancy reporting.
---

# Expense & Record Validation

## When to Use
- Task requires validating claims/expenses against an employee directory and approval list.
- Input files span multiple formats (e.g., PDF claims, XLSX directory, CSV approvals).
- Output must be a structured list of flagged discrepancies with explicit reasons.
- Includes variants like shift/role authorization checks, crosswalk/mapping validations, or honorarium reviews.

## Workflow
1. **Check Environment & Extract Data Safely**
   - Do NOT use generic `Read` tools on binary files (`.xlsx`, `.pdf`). They will fail.
   - **PDF Extraction**: `pdftotext` and `PyMuPDF` (`fitz`) are frequently missing in sandboxed environments. Verify availability first. If missing, fall back to `pdfminer.high_level` or `pdfplumber`.
   - **XLSX/CSV Extraction**: Use `pandas` (`pd.read_excel()`, `pd.read_csv()`) or `openpyxl` if `pandas` is unavailable.
2. **Define Validation Rules**
   - **Entity Match**: Use fuzzy string matching (`difflib.SequenceMatcher` ratio ≥ 0.85 or Levenshtein ≤ 1). Flag if no match.
   - **Account/ID Match**: Exact string match against directory/approvals.
   - **Amount/Fee Match**: Exact or tolerance-based (e.g., ±$0.01).
   - **Cross-Reference & Authorization**: Verify claimant matches the approved entity for the given ID/code. If a crosswalk/mapping table exists, resolve external codes to internal IDs before validation.
   - **Ownership/Role Check**: Ensure the claimed resource (shift, trip, code) is explicitly authorized for the matched entity.
3. **Cross-Reference & Flag**
   - Iterate through each claim. Apply rules sequentially.
   - Record: `page_number`, `entity_name`, `claimed_amount`, `account`, `approval_code`, `reason`.
   - Stop at first failure per claim, or collect all if required.
4. **Output**
   - Write flagged records to a JSON file.
   - Include a summary table of clean vs flagged pages.

## Anti-Patterns & Troubleshooting
- **Binary Read Failure**: If `Read` tool fails on `.xlsx`/`.pdf`, immediately switch to Python scripts.
- **Missing PDF Libraries**: If `pdftotext` or `fitz` fails with `FileNotFoundError` or `ModuleNotFoundError`, fall back to `pdfminer` or `PyPDF2`.
- **Name Typos**: Do not flag minor typos (e.g., "Reys" vs "Reyes") as unknown. Use fuzzy matching with a threshold ≥ 0.85.
- **Hardcoding Data**: Avoid hardcoding extracted data in prompts. Use a Python script to load, process, and output JSON deterministically.
- **Missing Fields**: If a PDF lacks a field, flag it as `Missing Data` rather than assuming a default.
- **Rigid Script Usage**: `scripts/audit_helper.py` is a structural template. Always adapt column names and inject domain-specific checks (e.g., crosswalk lookups, authorization matrices) into the validation loop before execution.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)
- **expense-claim-validation**: Standard cross-reference.
- **speaker-honorarium-review**: Validate speaker names, payment accounts, approval codes, and requested fees against a registry. Fuzzy match speaker names. Check approval code ownership.
- **clinic-shift-claim-review**: Validate clinician names, payout accounts, requested pay, and shift codes against a directory, authorization list, and crosswalk. Check shift code validity and clinician-shift authorization.

## Reusable Script
Run `scripts/audit_helper.py` when you have extracted claim data into a DataFrame or CSV. It handles pandas loading, fuzzy matching, sequential rule validation, and JSON export. 
**Important**: Adapt column names in the script to match your input schemas. If the task involves crosswalks, mapping tables, or authorization checks, modify the validation loop to resolve codes and verify ownership before applying standard amount/account checks.