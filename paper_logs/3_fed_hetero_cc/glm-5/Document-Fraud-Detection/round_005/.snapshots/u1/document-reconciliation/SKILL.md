---
name: document-reconciliation
description: Cross-validate records across multiple data sources (PDF, Excel, CSV, JSON) to identify discrepancies, validate claims, and flag anomalies. Handles fuzzy matching for typos, exact ID/account validation, multi-hop reference lookups via crosswalk tables, alias name matching, work order status checks, revision/amendment amount resolution, and structured discrepancy reporting. Use for expense screening, claim validation, audit tasks, speaker honorarium reviews, vendor payments, field service billing, healthcare shift claims, fleet maintenance chargebacks, or any multi-source data reconciliation.
---

# Document Reconciliation & Validation

Cross-validate records across heterogeneous data sources with fuzzy matching for common data entry errors.

## When to Use

- Validating expense claims against employee directories and approval records
- Matching entities across PDF forms, Excel databases, CSV exports, and JSON files
- Detecting specific violation types: unknown entities, mismatched accounts, invalid references, entity-reference mismatches
- Tasks where source data may contain typos (names, IDs) that should be matched fuzzily
- Multi-hop reference validation (external code → crosswalk → internal reference → approval)
- Work order or approval-based billing validation with status checks and revisions/amendments
- Fleet maintenance chargebacks, vendor payments, contractor billing audits
- Any multi-source data reconciliation requiring cross-reference validation

## Workflow

1. **Load all reference data first**
   - CSV: `pd.read_csv()` or direct text parsing
   - Excel: `pd.read_excel()` via Python/Bash (Read tool cannot read binary .xlsx files)
   - Excel with multiple sheets: `pd.ExcelFile(path)` then `parse(sheet_name)` for each sheet
   - PDF: Use `Read` tool, manually extract fields per page/record
   - JSON: `json.load()`; flatten nested structures (e.g., orders under depots) into lookup dicts

2. **Build lookup indexes**
   - Entity directory: `{id: {name, account, ...}}`
   - Alias table: `{alias_name: entity_id}` for alternate name matching
   - Approvals/references: `{ref_id: {amount, owner_id, status, ...}}`
   - Crosswalk (if present): `{external_code: internal_code}` for multi-hop lookups
   - Name-to-ID index for fuzzy matching: `{normalized_name: id}`

3. **Handle nested JSON structures**
   - If reference data has nested structure (e.g., orders under depots, items under categories):
     1. Iterate through parent containers
     2. Extract and flatten child records into a single lookup dict
     3. Preserve parent context if needed (depot, region, etc.)
   - Example: `for depot in data['depots']: for order in depot['orders']: orders[order['id']] = order`

4. **Handle multi-hop reference lookups**
   - If records use external codes (e.g., SHIFT-A1) but approvals use internal codes (e.g., INT-5101):
     1. Look up external code in crosswalk → get internal code
     2. Look up internal code in approvals → get approved amount and assigned entity
   - If external code not in crosswalk: flag as "Invalid Reference Code"

5. **Handle revision/amendment amounts**
   - If reference data includes revisions or amendments with approval states:
     1. Filter to approved/accepted entries only
     2. Use the highest revision/amendment number's amount as the expected amount
   - Revisions: `revision` number, `approval_state` field
   - Amendments: `amendment_no`, `decision` field (approved/rejected)
   - Example: MO-9003 has amendment 1 ($1175, approved) → use $1175, not original $1150

6. **Normalize for fuzzy matching**
   - Lowercase, strip extra spaces
   - Allow single-character differences (insertion/deletion/substitution)
   - Match if edit distance ≤ 1 for names with length > 5
   - Check alias table before fuzzy matching

7. **Validate each record sequentially**
   | Check | Failure Condition |
   |-------|-------------------|
   | Unknown Entity | Name doesn't match any entity (exact, alias, or fuzzy) |
   | Account Mismatch | Record account ≠ entity's registered account |
   | Invalid Reference Code | External code not in crosswalk |
   | Invalid Reference ID | Internal code not in approvals |
   | Invalid Reference Status | Reference exists but status/lifecycle is not valid (e.g., closed, inactive) |
   | Entity-Reference Mismatch | Reference's assigned entity ≠ record's entity (aliases: Provider Mismatch, Owner Mismatch) |
   | Amount Mismatch | abs(claimed_amount - approved_amount) > $0.01 |

8. **Output structured results**
   - JSON array of flagged records with: `record_id`, `entity_name`, `amount`, `account`, `ref_id`, `reason`
   - Include valid records summary for verification

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns

- **Don't require exact string matches** on names; typos are expected
- **Don't validate amount equality**; use tolerance (>$0.01 difference)
- **Don't assume single data format**; expect PDF + Excel + CSV + JSON combination
- **Don't assume direct reference lookup**; check for crosswalk tables
- **Don't stop at first violation**; check all conditions, report most specific reason
- **Don't ignore reference status**; closed/inactive references are invalid
- **Don't use original amount if revisions/amendments exist**; use highest approved revision
- **Don't assume flat JSON**; check for nested structures and flatten as needed

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Read tool fails on Excel | Binary .xlsx files cannot be read by Read tool. Use `python3 -c "import pandas as pd; df = pd.read_excel('file.xlsx'); print(df.to_csv(index=False))"` via Bash |
| Excel has multiple sheets | Use `pd.ExcelFile(path)` then check `xl.sheet_names` and parse each: `pd.read_excel(path, sheet_name='aliases')` |
| PDF not parseable | Use `Read` tool, manually extract; if base64 only, look for embedded text patterns |
| JSON has nested structure | Iterate parent containers, flatten children into single lookup dict |
| Excel read fails | Ensure `pandas` + `openpyxl` available: `python3 -c "import pandas; pd.read_excel('path')"` |
| Fuzzy matches too permissive | Restrict to edit distance ≤ 1, length > 5; verify against known good records |
| Missing violations | Double-check entity-reference mismatch: compare reference's assigned entity to record's entity_id |
| Crosswalk not found | Look for files named *crosswalk*, *mapping*, *lookup* - they bridge external codes to internal references |
| Alias not matched | Build alias lookup table from separate sheet/file; check aliases before fuzzy matching |
| Wrong amount used | Check for revision/amendment tables; use highest approved revision, not original amount |
| Valid reference flagged | Check reference status/lifecycle field; closed/inactive references should be flagged as invalid |
| Provider Mismatch missed | Same as Entity-Reference Mismatch: order's provider_id ≠ packet's provider_id |

## References

- `references/violation-types.md` — Detailed validation rules and priority order
- `scripts/reconcile_claims.py` — Reusable Python template for claim validation
