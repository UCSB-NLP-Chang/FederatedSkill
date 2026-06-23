---
name: expense-audit
description: Cross-references claims, work orders, or requests in multi-page PDFs against structured reference data (Excel/CSV/JSON) to detect discrepancies. Use for auditing travel expenses, contractor work orders, fleet chargebacks, speaker honorariums, shift claims, clinical trial participant releases, or similar document-vs-dataset validation tasks involving revisions, status checks, alias resolution, and fuzzy entity matching.
---

# Claim & Document Audit

## When to Use
- Task requires validating claims/requests in a PDF against a registry/directory (Excel/CSV/JSON) and approval/authorization/revision records.
- Need to flag mismatches in accounts, amounts, approval codes, entity identities, work order status, or crosswalk mappings.
- Claims may contain minor name typos or use aliases that should be treated as valid matches.
- PDFs may contain multiple pages for the same claim with different revision numbers.

## Recommended Execution Pattern
For multi-source validation, prefer writing a single Python script to handle ingestion, matching, validation, and JSON output. This avoids tool-switching overhead and preserves state across steps.
- Use `scripts/audit_template.py` as a starting point. Copy it, adapt the field extraction regex and validation rules to the specific task, and run it via `Bash`.
- If the template is insufficient, follow the workflow below.

## Workflow
1. **Ingest Reference Data**
   - Load the registry/directory (map `entity_id` → `name`, `department`, `account`).
   - Load approval/authorization records and **revision/snapshot logs**. 
     - For JSON/CSV revisions, select the highest revision/sequence number where `state == 'approved'` (or equivalent) as the ground truth amount.
     - *CSV Snapshots*: Filter rows by `state == 'approved'`, then group by ID and pick `max(seq)`. **Handle empty/null override amounts**: if the override amount field is blank, fall back to the base approved amount.
     - *JSON Data*: Flatten nested JSON structures (e.g., `sponsors[].programs[].awards[]` or `depots[].orders[]`) into a flat dictionary keyed by ID before validation. Use recursive traversal or explicit path extraction.
   - Load any crosswalk/mapping files (map external codes → internal IDs).
   - *Fallback*: If the `Read` tool fails on `.xlsx` files, use Python (`openpyxl` or `pandas`) via `Bash`. Check all sheet names; directories often split legal names and aliases across sheets.
2. **Parse & Deduplicate Claims**
   - Extract each claim/request from the PDF (usually one per page).
   - **Filter non-claim pages**: Skip cover sheets, appendices, or summary pages by checking for a consistent claim header or required fields before extraction.
   - **Deduplicate by Revision**: If claims include revision/version numbers, group extracted claims by claim/packet ID and retain only the page with the highest revision number. Discard older revisions before validation.
   - Identify: `entity_name`, `claimed_amount`, `approval_code`/`work_order_id`, `account`, `revision_number`, and any domain-specific fields.
   - *Warning*: Do not use Python's built-in `open()` on PDF files. They are binary and will raise `UnicodeDecodeError`. Use `pdftotext`, `pdfplumber`, or `PyPDF2`.
3. **Normalize & Match Names**
   - Apply fuzzy matching for names: allow 1-2 character differences, common typos, or missing suffixes.
   - Use `difflib.SequenceMatcher` (standard library) with a threshold of `> 0.80`. Avoid `Levenshtein`/`fuzzywuzzy` unless pre-installed.
   - If a name matches multiple entities, cross-check with department or approval history before flagging.
4. **Run Validation Rules**
   - Apply checks in order. Stop at the first failure unless instructed to collect all.
   - **Status Check**: Verify work order/claim status is `active`/`open`. Flag `closed`/`cancelled`/`archived` as `Invalid Work Order` or similar.
   - **Adapt Rule Names**: Use domain-appropriate reason strings (e.g., `Carrier Mismatch`, `Invalid Shipment Ref`, `Unknown Provider`, `Invalid Award Ref`) while preserving the logical validation order.
   - Insert domain-specific checks into the chain as needed.
   - Record the failing rule and relevant details per claim.
5. **Output Results**
   - Generate a JSON array of flagged claims.
   - **Crucial**: Verify the exact JSON schema expected by the verifier/tests (key names, types, ordering) before writing. Mismatched keys (e.g., `packet_page_number` vs `request_page_number`, `chargeback_total` vs `requested_amount`) are common causes of test failures.
   - Exclude clean claims unless explicitly requested.

## Validation Rules
Apply these checks in order. Stop at the first failure unless instructed to collect all.
1. **Entity Existence**: Claimed name must match a record in the registry (allow minor typos/aliases). → `Unknown Entity` / `Unknown Provider`
2. **Account/Token Match**: Claimed account/payment token must exactly match the registry record. → `Account Mismatch` / `Token Mismatch`
3. **Status Validity**: Work order/claim must be in an active/approved state. → `Invalid Work Order` / `Closed Status` / `Invalid Award Ref`
4. **Approval/Code Validity**: Claimed code must exist in the approvals/crosswalk list. → `Invalid Code` / `Invalid Order ID`
5. **Ownership Match**: The approved record must belong to the matched entity. → `Entity Mismatch` / `Provider Mismatch` / `Participant Mismatch`
6. **Amount Match**: Claimed amount must exactly match the approved/revised amount. → `Amount Mismatch`

## Anti-Patterns
- Do not reject claims for minor name typos or known aliases. Use fuzzy matching and cross-sheet alias resolution.
- Do not assume approval codes or work orders are globally unique without checking ownership. A valid code may belong to a different entity.
- Do not hardcode currency formats. Compare numeric values after stripping symbols.
- Do not rely on the `Read` tool for `.xlsx` files; it often fails on binary Excel formats. Use `Bash` with `python3` and `openpyxl`/`pandas`.
- Do not use Python's `open()` to read PDFs directly. Use dedicated PDF parsing tools.
- Avoid chaining multiple separate tool calls for data ingestion and validation; state loss and formatting drift cause brittle pipelines.
- Do not ignore revision/snapshot logs. Always resolve to the latest approved revision amount before comparing.
- Do not assume all PDF pages are claims. Cover sheets, appendices, and summary pages often lack required fields and will cause parsing errors if not filtered.
- Do not validate outdated revisions. Always deduplicate by claim ID and keep the highest revision number before running checks.

## Troubleshooting
- **PDF parsing fails**: Use `pdftotext` or `pdfplumber` to extract raw text if the `Read` tool returns garbled output or binary data.
- **Restricted environments**: `pip install` may fail with `--break-system-packages`. Prefer `pdftotext` (CLI) or check if `pdfplumber`/`PyPDF2` is pre-installed before attempting pip installs.
- **Ambiguous matches**: If registry contains similar names, cross-check with department or approval history before flagging.
- **Missing reference data**: Verify file paths and sheet names. Excel files may have multiple sheets; check the active or named sheet.
- **Crosswalk/Revision mismatches**: Ensure external codes are mapped to internal IDs before validation. Unmapped codes should trigger an `Invalid Code` flag, not a silent skip.
- **Verifier/Test failures**: If the test suite fails despite logical correctness, inspect the expected JSON schema. Mismatched keys or missing fields are common causes. Align output keys exactly with test expectations.