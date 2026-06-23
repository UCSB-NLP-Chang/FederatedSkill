---
name: multi-source-reconciliation
description: Cross-validate records across multiple data sources (PDF claims/requests, Excel directories/registries, CSV approvals) with fuzzy matching for typos. Use for expense screening, honorarium validation, claim verification, clinic shift validation, or any task requiring matching entities across structured and semi-structured sources where names may have minor spelling errors. Handles both direct lookups and crosswalk/indirection patterns where external codes map to internal authorization keys.
---

# Multi-Source Reconciliation & Validation

Cross-validate records across heterogeneous data sources with fuzzy matching for common data entry errors.

## When to Use

- Validating expense claims against employee directories and approval records
- Screening honorarium requests against speaker registries and session approvals
- Validating clinic shift claims with external→internal code crosswalks
- Matching entities across PDF forms, Excel databases, and CSV exports
- Detecting violation types: unknown entities, mismatched accounts/codes, invalid references, ownership mismatches, amount/fee discrepancies
- Tasks where source data may contain typos (names, IDs) that should be matched fuzzily

## Core Pattern

All reconciliation tasks follow this structure:

| Source Type | Typical Content | Key Fields |
|-------------|---------------|------------|
| Excel registry | Master entity list (employees, speakers, clinicians) | entity_id, name, payment_account/bank_account/payout_account |
| CSV approvals | Authorized transactions | approval_code/trip_id/shift_code_internal, approved_amount/fee, entity_id |
| PDF requests | Individual claim forms | name, requested_amount, payment_account, reference_code |
| CSV crosswalk | External→internal code mapping (optional) | external_code, internal_code |

## Workflow

1. **Load all reference data first**
   - CSV: `pd.read_csv()` or direct text parsing
   - Excel: `pd.read_excel()` (requires pandas) — if `Read` tool fails with binary error, use Python
   - PDF: Use `Read` tool. If text extraction fails (base64 only), manually extract fields from visible text patterns

2. **Handle crosswalk indirection if present**
   - Some tasks have external reference codes (e.g., SHIFT-A1) that map to internal authorization keys (e.g., INT-5101)
   - Build crosswalk dict: `{external_code: internal_code}`
   - Resolve: `internal_code = crosswalk.get(request['external_ref'])` before authorization lookup

3. **Build lookup indexes**
   - Entity registry: `{entity_id: {name, payment_account, ...}}`
   - Approvals: `{internal_code: {amount/fee, entity_id, ...}}`
   - Name-to-ID index for fuzzy matching: `{normalized_name: entity_id}`

4. **Normalize for fuzzy matching**
   - Lowercase, strip extra spaces, remove excess punctuation
   - Allow single-character differences (insertion/deletion/substitution)
   - Match if edit distance ≤ 1 for names with length > 5

5. **Validate each request sequentially**

   | Check | Generic Condition | Expense Example | Honorarium Example | Shift Example |
   |-------|-----------------|-----------------|-------------------|---------------|
   | Unknown Entity | Name not in registry (even fuzzily) | Unknown Employee | Unknown Speaker | Unknown Clinician |
   | Account Mismatch | payment_account ≠ registry | Bank account wrong | Payment account wrong | Payout account wrong |
   | Invalid Reference | code not in approvals/crosswalk | Invalid Trip ID | Invalid Approval Code | Invalid Shift Code (not in crosswalk) |
   | Invalid Internal Code | internal_code not in authorizations | — | — | Shift code not authorized |
   | Ownership Mismatch | approval's entity_id ≠ request's entity_id | Traveler Mismatch | Speaker Mismatch | Clinician Mismatch |
   | Amount Mismatch | abs(requested - approved) > tolerance | Fee vs approved | Fee vs approved | Pay vs approved |

6. **Output structured results**
   - JSON array of flagged items with: page/request number, entity name, requested amount, payment account, reference codes (both external and internal if crosswalk exists), reason
   - Include valid items summary for verification

## Crosswalk Pattern (Chained Lookup)

Some tasks require resolving through an intermediate mapping:

```
Request: SHIFT-A1 → Crosswalk → INT-5101 → Authorizations → {pay: 450.0, clinician_id: C701}
```

**Validation order with crosswalk:**
1. Unknown Entity (fuzzy match name to ID)
2. Account Mismatch (check payout account)
3. Invalid Shift Code (external code not in crosswalk)
4. Invalid Internal Code (resolved internal code not in authorizations)  
5. Clinician/Ownership Mismatch (auth.clinician_id ≠ matched.clinician_id)
6. Amount Mismatch

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Anti-Patterns

- **Don't require exact string matches** on names; typos are expected (Dr Evelyn Hart vs Dr. Evelyn Hart, Nora Elis vs Nora Ellis)
- **Don't validate amount equality**; use tolerance (>$0.01 difference)
- **Don't assume single data format**; expect PDF + Excel + CSV combination
- **Don't stop at first violation**; check all conditions, report most specific reason
- **Don't use Read tool for Excel files** — it's binary-only; use Python pandas instead
- **Don't forget crosswalk indirection** — external codes may need mapping before authorization lookup
- **Don't compare names for ownership** — compare entity_ids from matched records

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| PDF not parseable | Use `Read` tool; if base64 only, manually transcribe visible text patterns or use Python PDF parsing libraries |
| Excel read fails | Ensure `pandas` + `openpyxl` available; use `python3 -c "import pandas as pd; print(pd.read_excel('path').to_csv())"` |
| Fuzzy matches too permissive | Restrict to edit distance ≤ 1, length > 5; verify against known good records |
| Missing violations | Double-check ownership mismatch: compare approval's entity_id to request's matched entity_id, not names |
| Crosswalk key error | Verify external code exists in crosswalk before accessing; flag as "Invalid Shift/Code" if missing |

## References

- `references/violation-types.md` — Detailed validation rules and priority order for claim, honorarium, and shift variants
- `scripts/reconcile_claims.py` — Reusable Python template; customize DATA_PATHS and field names for your task
