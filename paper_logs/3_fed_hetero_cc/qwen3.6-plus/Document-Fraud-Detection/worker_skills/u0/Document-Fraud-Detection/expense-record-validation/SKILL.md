---
name: expense-record-validation
description: Cross-reference and validate expense claims or records against employee directories and approval lists. Handles multi-format inputs (PDF, XLSX, CSV, JSON), fuzzy name matching for typos, and structured discrepancy reporting.
---

# Expense & Record Validation

## When to Use
- Task requires validating claims/expenses against a directory and approval list.
- Input files span multiple formats (e.g., PDF claims, XLSX directory, CSV approvals, nested JSON catalogs).
- Output must be a structured list of flagged discrepancies with explicit reasons.
- Includes variants like shift/role authorization checks, crosswalk/mapping validations, honorarium reviews, field service work order audits, fleet maintenance chargeback audits, research stipend/award reconciliations, or clinical trial participant release audits.

## Workflow
1. **Check Environment & Extract Data Safely**
   - Do NOT use generic `Read` tools on binary files (`.xlsx`, `.pdf`). They will fail.
   - **PDF Extraction**: First, try `import pdfplumber` in Python. It is the most reliable for structured text. If unavailable, fall back to `pdftotext` (CLI) or `PyMuPDF` (`fitz`).
   - **Filter Non-Data Pages**: PDFs often contain cover pages, appendices, or blank pages. Identify and skip these during extraction. Only process pages containing actual claim/request data.
   - **XLSX/CSV Extraction**: Use `pandas` (`pd.read_excel()`, `pd.read_csv()`) or `openpyxl` if `pandas` is unavailable. Check for multiple sheets (e.g., `providers`, `aliases`) and merge them into a single lookup before validation.
   - **JSON Extraction**: Parse nested structures (e.g., `sponsors -> programs -> awards`) into a flat lookup table keyed by reference ID.
2. **Define Validation Rules**
   - **Entity Match**: Use fuzzy string matching (`difflib.SequenceMatcher` ratio ≥ 0.85 or Levenshtein ≤ 1) OR exact alias lookup. Flag if no match.
   - **Account/ID Match**: Exact string match against directory/approvals.
   - **Amount/Fee Match**: Exact or tolerance-based (e.g., ±$0.01). Resolve revisions/amendments if applicable.
   - **Cross-Reference & Authorization**: Verify claimant matches the approved entity for the given ID/code. If a crosswalk/mapping table exists, resolve external codes to internal IDs before validation.
   - **Ownership/Role/Location Check**: Ensure the claimed resource (shift, trip, code, work order, maintenance order, campus, award) is explicitly authorized for or owned by the matched entity. Flag if the order/ID belongs to a different provider/employee or location.
   - **Snapshot/Revision Resolution**: When a revision log or snapshot sequence exists, resolve the effective value by taking the **highest sequence/revision number with `state == 'approved'`**. Ignore `draft`, `rejected`, or empty-value revisions. If no approved revision exists, fall back to the base value.
   - **Duplicate Packet/Request Handling**: If multiple pages reference the same packet/request ID, retain only the latest occurrence (highest page number) for validation.
3. **Cross-Reference & Flag**
   - Iterate through each claim. Apply rules sequentially.
   - Record: `page_number`, `entity_name`, `claimed_amount`, `account`, `approval_code`, `reason`.
   - Stop at first failure per claim, or collect all if required.
4. **Output**
   - Write flagged records to a JSON file.
   - Include a summary table of clean vs flagged pages.

## Anti-Patterns & Troubleshooting
- **Binary Read Failure**: If `Read` tool fails on `.xlsx`/`.pdf`, immediately switch to Python scripts.
- **Missing PDF Libraries**: If `pdftotext` or `fitz` fails, fall back to `pdfplumber` or `pdfminer`. Prefer checking Python imports first to avoid CLI overhead.
- **Name Typos & Aliases**: Do not flag minor typos or known aliases as unknown. Use fuzzy matching (≥ 0.85) or explicit alias table lookups. Merge alias sheets/tables into the main directory before matching.
- **Hardcoding Data**: Avoid hardcoding extracted data in prompts. Use a Python script to load, process, and output JSON deterministically.
- **Missing Fields**: If a PDF lacks a field, flag it as `Missing Data` rather than assuming a default.
- **Rigid Script Usage**: `scripts/audit_helper.py` is a structural template. Always adapt column names and inject domain-specific checks (e.g., crosswalk lookups, authorization matrices, revision resolution, ownership/location checks, nested JSON flattening) into the validation loop before execution.

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
- **field-service-workorder-audit**: Validate contractor names (including aliases), payment accounts, billed amounts, and work order IDs against a directory, WO list, and revision log. Check WO status (`active` only), resolve latest `approved` revision amount (ignore `draft`), and verify WO contractor ownership.
- **fleet-maintenance-chargeback-audit**: Validate provider names (including aliases from separate sheets), payment accounts, chargeback totals, and order IDs against a provider directory and order list. Check for invalid order IDs, amount mismatches (accounting for amendments), and provider-order ownership mismatches (packet provider must own the referenced order).
- **research-stipend-reconciliation**: Validate recipient names (with aliases), bank tokens, requested amounts, and award refs against a roster, authorization list, and adjustment log. Resolve adjustments by taking the highest `revision_no` with `state == 'approved'` to override base values/codes. Check award `state` (reject `archived`/`inactive`). Verify campus/location codes match the effective award record.
- **clinical-trial-participant-release-audit**: Validate participant names (with aliases from separate XLSX sheets), payment tokens, requested amounts, and award refs against a registry, nested JSON award catalog, and version override CSV. Check award `status` (reject `archived`/`inactive`). Resolve version overrides by taking the highest `version_no` with `approval_state == 'approved'` to override base amounts/participant codes. Verify participant-award ownership. Handle duplicate packet IDs by retaining the latest page occurrence.

## Reusable Script
Run `scripts/audit_helper.py` when you have extracted claim data into a DataFrame or CSV. It handles pandas loading, fuzzy matching, sequential rule validation, and JSON export. 
**Important**: Adapt column names in the script to match your input schemas. If the task involves crosswalks, mapping tables, authorization checks, ownership/location verification, nested JSON flattening, or revision resolution, modify the validation loop to resolve codes, verify ownership, and compute expected amounts before applying standard checks.