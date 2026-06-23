---
name: document-reconciliation
description: Cross-validate records across multiple data sources (PDF, Excel, CSV) to identify discrepancies, validate claims, and flag anomalies. Handles fuzzy matching for typos, exact ID/account validation, multi-hop reference lookups via crosswalk tables, and structured discrepancy reporting. Use for expense screening, claim validation, audit tasks, speaker honorarium reviews, vendor payments, healthcare shift claims, or any multi-source data reconciliation.
---

# Document Reconciliation & Validation

Cross-validate records across heterogeneous data sources with fuzzy matching for common data entry errors.

## When to Use

- Validating expense claims against employee directories and approval records
- Matching entities across PDF forms, Excel databases, and CSV exports
- Detecting specific violation types: unknown entities, mismatched accounts, invalid references, entity-reference mismatches
- Tasks where source data may contain typos (names, IDs) that should be matched fuzzily
- Multi-hop reference validation (external code → crosswalk → internal reference → approval)
- Any multi-source data reconciliation requiring cross-reference validation

## Workflow

1. **Load all reference data first**
   - CSV: `pd.read_csv()` or direct text parsing
   - Excel: `pd.read_excel()` via Python/Bash (Read tool cannot read binary .xlsx files)
   - PDF: Use `Read` tool, manually extract fields per page/record

2. **Build lookup indexes**
   - Entity directory: `{id: {name, account, ...}}`
   - Approvals/references: `{ref_id: {amount, owner_id, ...}}`
   - Crosswalk (if present): `{external_code: internal_code}` for multi-hop lookups
   - Name-to-ID index for fuzzy matching: `{normalized_name: id}`

3. **Handle multi-hop reference lookups**
   - If records use external codes (e.g., SHIFT-A1) but approvals use internal codes (e.g., INT-5101):
     1. Look up external code in crosswalk → get internal code
     2. Look up internal code in approvals → get approved amount and assigned entity
   - If external code not in crosswalk: flag as "Invalid Reference Code"

4. **Normalize for fuzzy matching**
   - Lowercase, strip extra spaces
   - Allow single-character differences (insertion/deletion/substitution)
   - Match if edit distance ≤ 1 for names with length > 5

5. **Validate each record sequentially**
   | Check | Failure Condition |
   |-------|-------------------|
   | Unknown Entity | Name doesn't match any entity (fuzzy) |
   | Account Mismatch | Record account ≠ entity's registered account |
   | Invalid Reference Code | External code not in crosswalk |
   | Invalid Reference ID | Internal code not in approvals |
   | Entity-Reference Mismatch | Reference's assigned entity ≠ record's entity |
   | Amount Mismatch | abs(claimed_amount - approved_amount) > $0.01 |

6. **Output structured results**
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
- **Don't assume single data format**; expect PDF + Excel + CSV combination
- **Don't assume direct reference lookup**; check for crosswalk tables
- **Don't stop at first violation**; check all conditions, report most specific reason

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Read tool fails on Excel | Binary .xlsx files cannot be read by Read tool. Use `python3 -c "import pandas as pd; df = pd.read_excel('file.xlsx'); print(df.to_csv(index=False))"` via Bash |
| PDF not parseable | Use `Read` tool, manually extract; if base64 only, look for embedded text patterns |
| Excel read fails | Ensure `pandas` + `openpyxl` available: `python3 -c "import pandas; pd.read_excel('path')"` |
| Fuzzy matches too permissive | Restrict to edit distance ≤ 1, length > 5; verify against known good records |
| Missing violations | Double-check entity-reference mismatch: compare reference's assigned entity to record's entity_id |
| Crosswalk not found | Look for files named *crosswalk*, *mapping*, *lookup* - they bridge external codes to internal references |

## References

- `references/violation-types.md` — Detailed validation rules and priority order
- `scripts/reconcile_claims.py` — Reusable Python template for claim validation
