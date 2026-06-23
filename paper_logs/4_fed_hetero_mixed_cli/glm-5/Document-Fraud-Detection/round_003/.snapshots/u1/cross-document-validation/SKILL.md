---
name: cross-document-validation
description: Validate and reconcile data across multiple source files in different formats (Excel, CSV, PDF). Use when tasks require cross-referencing records between datasets, identifying discrepancies, or screening claims against master records. Common scenarios include expense claim validation, speaker honorarium review, invoice reconciliation, clinic shift claims, and transaction matching.
---

# Cross-Document Data Validation

## When to Use
- Validating expense claims against employee directories and approval records
- Reviewing speaker honorarium requests against registries and session approvals
- Validating clinic shift claims against clinician directories and shift authorizations
- Reconciling transactions between systems
- Screening submitted data against master reference files
- Any task requiring data matching across Excel, CSV, or PDF sources

## File Format Handling

| Format | Tool | Notes |
|--------|------|-------|
| `.xlsx`, `.xls` | Python/pandas | Read tool fails on binary Excel files |
| `.csv` | Read tool | Works directly |
| `.pdf` | Read tool | Returns text content or base64 |

### Reading Excel Files
```bash
python3 -c "import pandas as pd; df = pd.read_excel('/path/to/file.xlsx'); print(df.to_string())"
```

## Validation Workflow

1. **Load all reference data first** - registries, approval lists, master records, crosswalk tables
2. **Build lookup structures** - map IDs to names, accounts, approved amounts; build crosswalk mappings
3. **Process each request/record** - extract fields from PDF or input documents
4. **Run validation checks** in order:
   - Entity exists in reference (speaker/employee/clinician found)
   - Account/identifier matches registered value
   - Referenced IDs exist in approval/reference tables (resolve via crosswalk if needed)
   - Amounts match approved limits
   - Cross-references are consistent (approval belongs to correct entity)
5. **Output flagged records** with specific reason codes

## Crosswalk Table Pattern

Some domains use intermediate mapping tables between external reference codes and internal authorization IDs:

```
External Code → Crosswalk → Internal Code → Authorization Record
```

**Example:** Clinic shift claims use `SHIFT-A1` (external) → crosswalk → `INT-5101` (internal) → authorization with approved pay and clinician assignment.

**Validation steps with crosswalk:**
1. Check if external code exists in crosswalk
2. Resolve to internal code
3. Look up authorization by internal code
4. Verify authorization belongs to claiming entity

**Failure mode:** If external code not in crosswalk → "Invalid Reference Code" (not "Unknown Entity")

## Common Validation Checks

| Check Type | Description | Example |
|------------|-------------|----------|
| Unknown Entity | Name/ID not in master records | Clinician not in directory |
| Account Mismatch | Payment account differs from registered | Claim shows BAD-702, registry has PAY-702 |
| Invalid Reference | Referenced ID not found | Shift code doesn't exist in crosswalk |
| Entity Mismatch | Reference belongs to different entity | Authorization assigned to different clinician |
| Amount/Fee Mismatch | Claimed differs from approved | $610 vs approved $640 |

## Anti-Patterns

- **Do not use Read tool on `.xlsx` files** - they are binary and will fail
- **Do not assume exact name matching** - watch for typos ("Maya Ptel" vs "Maya Patel", "Nora Elis" vs "Nora Ellis") and punctuation variations ("Dr Evelyn" vs "Dr. Evelyn")
- **Do not skip building lookup tables** - repeated linear searches are slow and error-prone
- **Do not assume approval codes belong to the requesting entity** - always verify the approval's assigned entity matches the requester
- **Do not skip crosswalk resolution** - external codes must be mapped before checking authorizations

## Output Format

Return flagged records as structured JSON with fields:
- `claim_page_number` or record identifier
- `clinician_name` or entity name
- `requested_pay` or relevant values
- `reason` - specific discrepancy description

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known invariants (by sub-task)

### expense-claim-validation & speaker-honorarium-review & clinic-shift-claims
- Validation priority order: Unknown Entity → Invalid Reference → Entity Mismatch → Account Mismatch → Amount/Fee Mismatch. Stop at first failure.
- Fuzzy match threshold: 90% Levenshtein ratio (not simple sequence matching).
- Amount tolerance: 0.01 for currency comparisons.
- Entity names frequently contain typos ("Briann" vs "Brian", "Reys" vs "Reyes", "Ptel" vs "Patel", "Elis" vs "Ellis") — always use fuzzy matching, never require exact match.

## Scripts

Use `scripts/validate_claims.py` as a template for expense claim validation tasks.

## References

- `references/fuzzy-matching-guide.md` - Algorithm details for name matching with typo and punctuation tolerance
- `references/domain-examples.md` - Concrete field mappings for common validation scenarios including clinic shift claims
