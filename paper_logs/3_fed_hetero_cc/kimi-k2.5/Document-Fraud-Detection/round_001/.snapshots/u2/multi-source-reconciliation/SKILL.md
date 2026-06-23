---
name: multi-source-reconciliation
description: Cross-validate records across multiple data sources (PDF claims, Excel directories, CSV approvals) with fuzzy matching for typos. Use for expense screening, claim validation, or any task requiring matching entities across structured and semi-structured sources.
---

# Multi-Source Reconciliation & Validation

Cross-validate records across heterogeneous data sources with fuzzy matching for common data entry errors.

## When to Use

- Validating expense claims against employee directories and approval records
- Matching entities across PDF forms, Excel databases, and CSV exports
- Detecting specific violation types: unknown entities, mismatched accounts, invalid references, traveler/owner mismatches
- Tasks where source data may contain typos (names, IDs) that should be matched fuzzily

## Workflow

1. **Load all reference data first**
   - CSV: `pd.read_csv()` or direct text parsing
   - Excel: `pd.read_excel()` (requires pandas)
   - PDF: Use `Read` tool, manually extract fields per page/record

2. **Build lookup indexes**
   - Employee directory: `{employee_id: {name, bank_account, ...}}`
   - Approvals/trips: `{trip_id: {amount, employee_id, ...}}`
   - Name-to-ID index for fuzzy matching: `{normalized_name: employee_id}`

3. **Normalize for fuzzy matching**
   - Lowercase, strip extra spaces
   - Allow single-character differences (insertion/deletion/substitution)
   - Match if edit distance ≤ 1 for names with length > 5

4. **Validate each claim sequentially**
   | Check | Failure Condition |
   |-------|-------------------|
   | Unknown Employee | Name doesn't match any employee (fuzzy) |
   | Account Mismatch | Claim bank_account ≠ employee's bank_account |
   | Invalid Trip ID | trip_id not in approvals |
   | Traveler Mismatch | trip's employee_id ≠ claim's employee_id |
   | Amount Mismatch | abs(claimed_amount - approved_amount) > $0.01 |

5. **Output structured results**
   - JSON array of flagged claims with: `claim_page_number`, `employee_name`, `claimed_amount`, `bank_account`, `trip_id`, `reason`
   - Include valid claims summary for verification

## Anti-Patterns

- **Don't require exact string matches** on names; typos are expected
- **Don't validate amount equality**; use tolerance (>$0.01 difference)
- **Don't assume single data format**; expect PDF + Excel + CSV combination
- **Don't stop at first violation**; check all conditions, report most specific reason

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| PDF not parseable | Use `Read` tool, manually extract; if base64 only, look for embedded text patterns |
| Excel read fails | Ensure `pandas` + `openpyxl` available: `python3 -c "import pandas; pd.read_excel('path')"` |
| Fuzzy matches too permissive | Restrict to edit distance ≤ 1, length > 5; verify against known good records |
| Missing violations | Double-check traveler mismatch: compare trip's owner to claim's employee_id |

## References

- `references/violation-types.md` — Detailed validation rules and priority order
- `scripts/reconcile_claims.py` — Reusable Python template for claim validation