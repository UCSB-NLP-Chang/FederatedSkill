---
name: multi-source-reconciliation
description: Cross-validate records across multiple data sources (PDF claims/requests, Excel directories/registries, CSV approvals) with fuzzy matching for typos. Use for expense screening, honorarium validation, claim verification, clinic shift validation, field service audits, or any task requiring matching entities across structured and semi-structured sources. Handles direct lookups, crosswalk/indirection patterns, alias resolution, and stateful validation (status checks on references).
---

# Multi-Source Reconciliation & Validation

Cross-validate records across heterogeneous data sources with fuzzy matching for common data entry errors.

## When to Use

- Validating expense claims against employee directories and approval records
- Screening honorarium requests against speaker registries and session approvals
- Validating clinic shift claims with external→internal code crosswalks
- Field service audits: contractor billing packets against work order registries with status checks
- Matching entities across PDF forms, Excel databases, and CSV exports
- Tasks where entities have registered aliases (DBA names, abbreviated forms)

## Workflow

1. **Load all reference data first**
   - CSV: `pd.read_csv()` or direct text parsing
   - Excel: `pd.read_excel()` via Python (Read tool cannot read binary .xlsx files)
   - Excel with multiple sheets: use `pd.ExcelFile(path).sheet_names` to discover alias tables
   - PDF: Use `Read` tool, manually extract fields per page/record

2. **Build lookup indexes**
   - Entity directory: `{id: {name, account, ...}}`
   - Alias table: `{alias_name: entity_id}` for alternate name matching
   - Approvals/references: `{ref_id: {amount, owner_id, status, ...}}`
   - Crosswalk (if present): `{external_code: internal_code}` for multi-hop lookups
   - Name-to-ID index for fuzzy matching: `{normalized_name: id}`

3. **Handle alias resolution**
   - Check alias table first for exact match
   - Then exact match on primary/legal names
   - Then fuzzy match (edit distance ≤ 1, length > 5)
   - Only flag "Unknown Entity" if all three fail

4. **Handle multi-hop reference lookups (crosswalk)**
   - If records use external codes that map to internal codes:
     1. Look up external code in crosswalk → get internal code
     2. Look up internal code in approvals → get approved amount and assigned entity
   - If external code not in crosswalk: flag as "Invalid Reference Code"

5. **Handle revisions (if present)**
   - Filter to revisions with approval_state='approved'
   - Use the highest revision number's amount as expected amount
   - Example: WO-8807 has revisions 1 ($6400) and 2 ($6550), both approved → use $6550

6. **Validate each record sequentially (priority order)**
   - **Unknown Entity**: Name doesn't match entity (exact, alias, or fuzzy)
   - **Account Mismatch**: Record account ≠ entity's registered account
   - **Invalid Reference Code**: External code not in crosswalk
   - **Invalid Reference ID**: Internal code not in approvals
   - **Invalid Reference Status**: Reference exists but status is not valid (closed, inactive)
   - **Entity-Reference Mismatch**: Reference's assigned entity ≠ record's entity
   - **Amount Mismatch**: abs(claimed - approved) > $0.01

7. **Output structured results**
   - JSON array of flagged records with: record_id, entity_name, amount, account, ref_id, reason
   - Include valid records summary for verification

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs.
Pass raw float values directly. DO NOT: `round(x, N)`, `format(x, ".2f")`.
DO: write raw float values to Excel/JSON/CSV cells.

## Anti-Patterns

- Don't require exact string matches on names; typos and aliases are expected
- Don't forget alias tables — check for secondary sheets or alias columns
- Don't skip state checks — "exists" ≠ "valid"; verify status fields (active, closed)
- Don't use original amount if revisions exist — use highest approved revision
- Don't compare names for ownership — compare entity_ids from matched records
- Don't stop at first violation — check all conditions, report most specific reason
- Don't use Read tool for Excel files — use Python pandas instead

## Known invariants (by sub-task)

- **expense-claim-validation**: Standard cross-reference with fuzzy name matching
- **speaker-honorarium-review**: Validate speaker names, payment accounts, approval codes
- **clinic-shift-claim-review**: Crosswalk lookup (external→internal), check shift code validity
- **field-service-workorder-audit**: Alias resolution, WO status must be 'active', use highest approved revision amount, contractor ownership check

## Troubleshooting

- **Excel read fails**: Use `python3 -c "import pandas as pd; print(pd.read_excel('file.xlsx').to_csv())"`
- **Multiple Excel sheets**: Check `pd.ExcelFile(path).sheet_names` for aliases
- **Alias not matched**: Build alias lookup table from separate sheet/file
- **Wrong amount used**: Check for revision tables; use highest approved revision
- **Valid reference flagged**: Check reference status field; closed/inactive refs are invalid

## References

- `references/violation-types.md` — Detailed validation rules and priority order
- `references/alias-patterns.md` — Alias resolution strategies and patterns
- `scripts/reconcile_claims.py` — Reusable Python template