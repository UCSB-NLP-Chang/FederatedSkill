---
name: multi-source-reconciliation
description: Cross-validate records across multiple data sources (PDF claims/requests, Excel directories/registries, CSV approvals, JSON order databases) with fuzzy matching for typos. Use for expense screening, honorarium validation, claim verification, clinic shift validation, field service audits, fleet maintenance chargebacks, research stipend reconciliation, or any task requiring matching entities across structured and semi-structured sources. Handles direct lookups, crosswalk/indirection patterns, alias resolution, stateful validation (status/lifecycle checks), amendments/revision hierarchies, and multi-field validation (account, campus, amount).
---

# Multi-Source Reconciliation & Validation

Cross-validate records across heterogeneous data sources with fuzzy matching for common data entry errors.

## When to Use
- Validating expense claims against employee directories and approval records
- Screening honorarium requests against speaker registries and session approvals
- Validating clinic shift claims with external→internal code crosswalks
- Field service audits: contractor billing packets against work order registries with status checks
- Fleet maintenance chargebacks: provider packets against order databases with lifecycle validation
- **Research stipend reconciliation**: recipient packets against award authorizations with campus validation and revision handling
- Matching entities across PDF forms, Excel databases, CSV/JSON exports
- Tasks where entities have registered aliases (DBA names, abbreviated forms, initials)
- Tasks where reference records have lifecycle states (approved, active, open, archived)
- Tasks where amendments/revisions override base amounts or other fields (campus, dates)
- Tasks requiring multi-field validation beyond just amount (account + campus + status)

## Workflow
1. **Check Environment & Extract Data Safely**
   - Do NOT use generic `Read` tools on binary files (`.xlsx`, `.pdf`). They will fail.
   - **PDF Extraction**: Prefer `pdfplumber` for structured packet/form extraction. Fallback to `pdftotext`, `PyMuPDF` (`fitz`), or `pdfminer.high_level`. Use `Read` tool only as last resort for text extraction.
   - **Excel/CSV**: Use `pandas` (`pd.read_excel()`, `pd.read_csv()`). Check for multiple sheets (`pd.ExcelFile(path).sheet_names`) and merge alias tables.
   - **JSON**: `json.load()` for hierarchical structures; flatten nested arrays before indexing.
2. **Build lookup indexes**
   - Entity directory: `{id: {name, account, campus, ...}}`
   - Alias table: `{alias_name: entity_id}` for alternate name matching (including initial variants like "Amara S.")
   - Approvals/references: `{ref_id: {amount, owner_id, status, lifecycle, campus, ...}}`
   - Crosswalk (if present): `{external_code: internal_code}` for multi-hop lookups
   - Name-to-ID index for fuzzy matching: `{normalized_name: id}`
3. **Handle alias resolution**
   - Check alias table first for exact match
   - Then exact match on primary/legal names
   - Then fuzzy match (`difflib.SequenceMatcher` ratio ≥ 0.85 or edit distance ≤ 1 for length > 5)
   - Handle initial variants: "First L." → "First Last" by expanding initials
   - Only flag "Unknown Entity" if all approaches fail
4. **Handle hierarchical JSON data**
   - Flatten nested structures into lookup tables
   - Example: `{"depots": [{"orders": [...]}]}` → `{order_id: {provider_id, approved_charge, lifecycle, depot_code}}`
   - Iterate parent containers, flatten children, preserve context if needed
5. **Handle lifecycle/state validation**
   - Check `lifecycle`, `status`, `state`, or `approval_state` field on reference records
   - Valid states vary by domain: `approved`, `active`, `open`
   - Invalid states: `closed`, `cancelled`, `pending`, `inactive`, `archived`
   - **Rule**: "exists" ≠ "valid"; always verify state before using reference
6. **Handle amendments/revisions**
   - Filter to `decision='approved'` or `approval_state='approved'` only
   - For multiple approved amendments/revisions: use **highest revision number**
   - Amount override: use highest approved revision's amount
   - Field override: other fields (campus, dates) may also change across revisions
   - Build final lookup: `{ref_id: {highest_approved_amount, effective_campus, ...}}`
7. **Handle multi-hop reference lookups (crosswalk)**
   - If records use external codes that map to internal codes:
     1. Look up external code in crosswalk → get internal code
     2. Look up internal code in approvals → get approved amount and assigned entity
   - If external code not in crosswalk: flag as "Invalid Reference Code"
8. **Validate each record sequentially (priority order)**
   - **Unknown Entity**: Name doesn't match entity (exact, alias, fuzzy, or initial expansion)
   - **Account Mismatch**: Record account ≠ entity's registered account
   - **Invalid Reference Code**: External code not in crosswalk
   - **Invalid Reference ID**: Internal code not in approvals
   - **Invalid Reference Status**: Reference exists but lifecycle/status is invalid (archived, closed, etc.)
   - **Entity-Reference Mismatch**: Reference's assigned entity ≠ record's entity (aliases: Provider Mismatch, Owner Mismatch, Clinician Mismatch, Traveler Mismatch, Recipient Mismatch)
   - **Field Mismatch**: Other fields differ (campus, dates) — check against effective revision values
   - **Amount Mismatch**: `abs(claimed - approved) > $0.01`
9. **Output structured results**
   - JSON array of flagged records with: `record_id`, `entity_name`, `amount`, `account`, `ref_id`, `reason`
   - Include valid records summary for verification

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs.
Pass raw float values directly. DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`.
DO: write raw float values to Excel/JSON/CSV cells. The verifier's tolerance decides acceptable precision.

## Anti-Patterns
- Don't require exact string matches on names; typos, aliases, and initials are expected
- Don't forget alias tables — check for secondary sheets or alias columns
- Don't skip state checks — "exists" ≠ "valid"; verify lifecycle/status fields (archived is invalid)
- Don't use original amount if amendments/revisions exist — use highest approved
- Don't ignore field changes in revisions — campus, dates may change across revisions
- Don't compare names for ownership — compare entity_ids from matched records
- Don't stop at first violation — check all conditions, report most specific reason
- Don't use Read tool for Excel files — use Python pandas instead
- Don't assume flat JSON structures — flatten hierarchies before indexing
- Avoid hardcoding extracted data in prompts; use Python scripts for deterministic processing

## Known invariants (by sub-task)
- **expense-claim-validation**: Standard cross-reference with fuzzy name matching
- **speaker-honorarium-review**: Validate speaker names, payment accounts, approval codes, requested fees against registry
- **clinic-shift-claim-review**: Crosswalk lookup, check shift code validity and clinician-shift authorization
- **field-service-workorder-audit**: Alias resolution, WO status must be 'active', use highest approved revision amount, contractor ownership check
- **fleet-maintenance-chargeback**: Provider alias resolution, order lifecycle must be 'approved' (not 'closed'), use highest approved amendment amount, provider-order ownership check
- **research-stipend-reconciliation**: Recipient name matching with initial variants, bank token validation, award-level state check (archived=invalid), revision handling for amount AND campus changes, recipient-award ownership check

## Troubleshooting
- **Excel read fails**: Use `python3 -c "import pandas as pd; print(pd.read_excel('file.xlsx').to_csv())"`
- **Multiple Excel sheets**: Check `pd.ExcelFile(path).sheet_names` for aliases
- **Alias not matched**: Build alias lookup table from separate sheet/file; consider initial variants
- **Wrong amount used**: Check for amendment/revision tables; use highest approved
- **Wrong campus flagged**: Check if campus changed in approved revision
- **Valid reference flagged**: Check lifecycle/status field; archived/closed refs are invalid
- **JSON nested structures**: Flatten before building lookups; extract from parent arrays
- **Lifecycle field names vary**: Check for `lifecycle`, `status`, `state`, `approval_state` — validate semantics
- **Missing PDF libraries**: Fallback chain: `pdfplumber` → `pdftotext` → `PyMuPDF` → `pdfminer`
- **Rigid script usage**: Adapt reusable scripts to match input schemas and inject domain-specific checks (crosswalks, ownership, revisions, multi-field) before execution

## References
- `references/violation-types.md` — Detailed validation rules and priority order
- `references/alias-patterns.md` — Alias resolution strategies and patterns
- `references/amendment-handling.md` — Amendment/revision processing patterns
- `references/lifecycle-validation.md` — State checking across domains
- `references/multi-field-validation.md` — Campus and cross-field validation patterns
- `scripts/reconcile_claims.py` — Reusable Python template