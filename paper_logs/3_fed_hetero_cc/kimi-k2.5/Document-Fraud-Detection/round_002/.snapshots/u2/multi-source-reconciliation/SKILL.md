---
name: multi-source-reconciliation
description: Cross-validate records across multiple data sources (PDF claims/requests, Excel directories/registries, CSV approvals) with fuzzy matching for typos. Use for expense screening, honorarium validation, claim verification, or any task requiring matching entities across structured and semi-structured sources where names may have minor spelling errors.
---

# Multi-Source Reconciliation & Validation

Cross-validate records across heterogeneous data sources with fuzzy matching for common data entry errors.

## When to Use

- Validating expense claims against employee directories and approval records
- Screening honorarium requests against speaker registries and session approvals  
- Matching entities across PDF forms, Excel databases, and CSV exports
- Detecting violation types: unknown entities, mismatched accounts/codes, invalid references, ownership mismatches, amount/fee discrepancies
- Tasks where source data may contain typos (names, IDs) that should be matched fuzzily

## Core Pattern

All reconciliation tasks follow this structure:

| Source Type | Typical Content | Key Fields |
|-------------|---------------|------------|
| Excel registry | Master entity list (employees, speakers) | entity_id, name, payment_account/bank_account |
| CSV approvals | Authorized transactions | approval_code/trip_id, approved_amount/fee, entity_id |
| PDF requests | Individual claim forms | name, requested_amount, payment_account, approval_code |

## Workflow

1. **Load all reference data first**
   - CSV: `pd.read_csv()` or direct text parsing
   - Excel: `pd.read_excel()` (requires pandas) — if `Read` tool fails with binary error, use Python
   - PDF: Use `Read` tool, manually extract fields per page/record from text output

2. **Build lookup indexes**
   - Entity registry: `{entity_id: {name, payment_account, ...}}`
   - Approvals: `{approval_code: {amount/fee, entity_id, ...}}`
   - Name-to-ID index for fuzzy matching: `{normalized_name: entity_id}`

3. **Normalize for fuzzy matching**
   - Lowercase, strip extra spaces, remove excess punctuation
   - Allow single-character differences (insertion/deletion/substitution)
   - Match if edit distance ≤ 1 for names with length > 5

4. **Validate each request sequentially**
   | Check | Generic Condition | Expense Example | Honorarium Example |
   |-------|-----------------|-----------------|-------------------|
   | Unknown Entity | Name not in registry (even fuzzily) | Unknown Employee | Unknown Speaker |
   | Account Mismatch | payment_account ≠ registry | Bank account wrong | Payment account wrong |
   | Invalid Reference | approval_code/trip_id not in approvals | Invalid Trip ID | Invalid Approval Code |
   | Ownership Mismatch | approval's entity_id ≠ request's entity_id | Traveler Mismatch | Speaker Mismatch |
   | Amount Mismatch | abs(requested - approved) > tolerance | Fee vs approved | Fee vs approved |

5. **Output structured results**
   - JSON array of flagged items with: page/request number, entity name, requested amount, payment account, approval code, reason
   - Include valid items summary for verification

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns

- **Don't require exact string matches** on names; typos are expected (Dr Evelyn Hart vs Dr. Evelyn Hart)
- **Don't validate amount equality**; use tolerance (>$0.01 difference)  
- **Don't assume single data format**; expect PDF + Excel + CSV combination
- **Don't stop at first violation**; check all conditions, report most specific reason
- **Don't use Read tool for Excel files** — it's binary-only; use Python pandas instead

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| PDF not parseable | Use `Read` tool; if base64 only, look for embedded text patterns in metadata |
| Excel read fails | Ensure `pandas` + `openpyxl` available; use `python3 -c "import pandas as pd; print(pd.read_excel('path').to_csv())"` |
| Fuzzy matches too permissive | Restrict to edit distance ≤ 1, length > 5; verify against known good records |
| Missing violations | Double-check ownership mismatch: compare approval's entity_id to request's matched entity_id |

## References

- `references/violation-types.md` — Detailed validation rules and priority order for claim and honorarium variants
- `scripts/reconcile_claims.py` — Reusable Python template; customize DATA_PATHS and field names for your task