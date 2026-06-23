---
name: expense-record-validation
description: Cross-reference and validate expense claims or records against employee directories and approval lists. Handles multi-format inputs (PDF, XLSX, CSV), fuzzy name matching for typos, and structured discrepancy reporting.
---

# Expense & Record Validation

## When to Use
- Task requires validating claims/expenses against an employee directory and approval list.
- Input files span multiple formats (e.g., PDF claims, XLSX directory, CSV approvals).
- Output must be a structured list of flagged discrepancies with explicit reasons.

## Workflow
1. **Extract Data Safely**
   - Do NOT use generic `Read` tools on binary files (`.xlsx`, `.pdf`). They will fail.
   - Use `pandas` for `.xlsx` and `.csv`: `pd.read_excel()`, `pd.read_csv()`.
   - For `.pdf`, use `pdfplumber` or `PyPDF2` in a Python script to extract tables/text.
2. **Define Validation Rules**
   - **Employee Match**: Use fuzzy string matching (Levenshtein distance ≤ 1 or `difflib` ratio ≥ 0.85). Flag if no match.
   - **Account Match**: Exact string match against directory.
   - **Trip/ID Match**: Exact match against approvals list.
   - **Amount Match**: Exact or tolerance-based (e.g., ±$0.01).
   - **Traveler Match**: Verify trip ID's assigned employee matches claimant.
3. **Cross-Reference & Flag**
   - Iterate through each claim. Apply rules sequentially.
   - Record: `claim_page_number`, `employee_name`, `claimed_amount`, `bank_account`, `trip_id`, `reason`.
   - Stop at first failure per claim, or collect all if required.
4. **Output**
   - Write flagged records to a JSON file.
   - Include a summary table of clean vs flagged pages.

## Anti-Patterns & Troubleshooting
- **Binary Read Failure**: If `Read` tool fails on `.xlsx`, immediately switch to `python3 -c "import pandas as pd; ..."` or `scripts/audit_helper.py`.
- **Name Typos**: Do not flag minor typos (e.g., "Chenn" vs "Chen") as unknown. Use fuzzy matching with a threshold.
- **Hardcoding Data**: Avoid hardcoding extracted data in prompts. Use a Python script to load, process, and output JSON deterministically.
- **Missing Fields**: If a PDF lacks a field, flag it as `Missing Data` rather than assuming a default.

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### expense-claim-validation
- (Round 0: no verifier failures observed yet; add invariants as they surface.)

## Reusable Script
Run `scripts/audit_helper.py` when you have extracted claim data into a DataFrame or CSV. It handles pandas loading, fuzzy matching, sequential rule validation, and JSON export. Adapt column names in the script to match your input schemas.