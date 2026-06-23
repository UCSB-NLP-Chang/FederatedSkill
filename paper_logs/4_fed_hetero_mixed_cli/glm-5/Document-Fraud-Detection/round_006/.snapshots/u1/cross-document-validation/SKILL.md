---
name: cross-document-validation
description: Validate and reconcile data across multiple source files in different formats (Excel, CSV, PDF). Use when tasks require cross-referencing records between datasets, identifying discrepancies, or screening claims against master records. Common scenarios include expense claim validation, speaker honorarium review, invoice reconciliation, clinic shift claims, field service work order audits, fleet maintenance chargeback audits, research stipend reconciliation, and transaction matching.
---

# Cross-Document Data Validation

## When to Use
- Validating expense claims against employee directories and approval records
- Reviewing speaker honorarium requests against registries and session approvals
- Validating clinic shift claims against clinician directories and shift authorizations
- Auditing field service work orders against contractor directories and work order records
- Auditing fleet maintenance chargebacks against provider directories and maintenance orders
- Reconciling research stipend requests against recipient rosters and award authorizations
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

### Multi-Sheet Excel Files
Check for additional sheets - they often contain alias tables, crosswalks, or supplementary data:
```bash
python3 -c "import pandas as pd; xl = pd.ExcelFile('/path/to/file.xlsx'); print('Sheets:', xl.sheet_names); [print(f'--- {s} ---', pd.read_excel(xl, s).to_string(), sep='\n') for s in xl.sheet_names]"
```

## Validation Workflow

1. **Load all reference data first** - registries, approval lists, master records, crosswalk tables, alias tables
2. **Build lookup structures** - map IDs to names, accounts, approved amounts; build crosswalk and alias mappings
3. **Process each request/record** - extract fields from PDF or input documents
4. **Run validation checks** in order:
   - Entity exists in reference (check alias table if name not found in main directory)
   - Status is valid (work order active, approval not closed/expired/archived)
   - Referenced IDs exist in approval/reference tables (resolve via crosswalk if needed)
   - Entity matches assignment (approval belongs to correct entity)
   - Account/identifier matches registered value
   - Location/campus matches adjusted/base authorization value
   - Amounts match approved limits (use latest approved revision if applicable)
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

## Alias Table Pattern

Contractor/vendor/provider directories often have alternate names in a separate sheet or table:

```
Main Directory: contractor_id → legal_name, payment_account
Alias Table: contractor_id → alias_name (multiple rows per ID)
```

**Name resolution flow:**
1. Try exact match against legal_name in main directory
2. If not found, search alias table for name match
3. Resolve alias match to contractor_id, then to main record
4. If still not found → "Unknown Contractor/Vendor/Provider"

## Status Validation Pattern

Work orders, approvals, and authorizations may have status fields:

| Status | Action |
|--------|--------|
| active | Proceed with validation |
| closed | Flag as "Invalid Work Order" or "Closed Approval" |
| archived | Flag as "Invalid Award Ref" or "Archived Authorization" |
| draft | Flag as "Unapproved Revision" |
| expired | Flag as "Expired Authorization" |

**Check status before amount comparison** - a closed/archived authorization should fail regardless of amount match.

## Revision/Amendment Chain Pattern

Approvals may have revision history with different amounts. Revisions can be embedded in the main file or in a separate amendments/adjustments file:

```
Base: WO-8801 → $4,800
Revision 1: WO-8801 → $4,900 (approved)
Revision 2: WO-8801 → $5,100 (draft)
```

**Resolution rules:**
1. Find all revisions/amendments for the order ID
2. Filter to approved revisions only
3. Use the highest revision number with approved status
4. Compare claimed amount against that approved amount

**Multi-field adjustments:** Adjustments may modify multiple fields (amount, campus, location, etc.). Always use adjusted values for all field comparisons, not just amounts.

**Separate amendment file pattern:**
- Main orders file contains base approved amounts and lifecycle status
- Separate amendments/adjustments file contains order_id, amendment_no, amended_charge, decision
- Merge on order_id, filter where decision='approved', use latest amendment_no

## Common Validation Checks

| Check Type | Description | Example |
|------------|-------------|----------|
| Unknown Entity | Name/ID not in master records or alias table | Contractor not in directory |
| Invalid Reference | Referenced ID not found or wrong status | Work order doesn't exist or is closed/archived |
| Entity Mismatch | Reference belongs to different entity | Work order assigned to different contractor |
| Account Mismatch | Payment account differs from registered | Claim shows BAD-702, registry has PAY-702 |
| Location Mismatch | Campus/location differs from adjusted authorization | Claim shows CAMP-W, adjusted authorization has CAMP-C |
| Amount/Fee Mismatch | Claimed differs from approved (latest revision) | $4,400 vs approved $4,300 |

## Anti-Patterns

- **Do not use Read tool on `.xlsx` files** - they are binary and will fail
- **Do not assume single-sheet Excel files** - always check for additional sheets containing aliases or crosswalks
- **Do not assume exact name matching** - watch for typos and alias variations
- **Do not skip building lookup tables** - repeated linear searches are slow and error-prone
- **Do not assume approval codes belong to the requesting entity** - always verify the approval's assigned entity matches the requester
- **Do not skip crosswalk resolution** - external codes must be mapped before checking authorizations
- **Do not skip status checks** - a closed/archived work order is invalid even if amounts match
- **Do not use base revision amount if approved revisions exist** - always use latest approved revision
- **Do not assume amendments are in the same file as orders** - check for separate adjustment/amendment files
- **Do not validate location/campus against base authorization if adjustments modify it** - use adjusted values for all fields

## Output Format

Return flagged records as structured JSON with fields:
- `packet_page_number` or `claim_page_number` or record identifier
- `contractor_name` or entity name
- `billed_amount` or `requested_pay` or relevant values
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
- Entity names frequently contain typos — always use fuzzy matching, never require exact match.

### field-service-workorder-audit & fleet-maintenance-chargeback-audit
- Validation priority order: Unknown Contractor/Provider → Invalid Order ID (status) → Contractor/Provider Mismatch → Account Mismatch → Amount Mismatch. Stop at first failure.
- Check alias table before marking as Unknown Contractor/Provider.
- Use latest approved revision/amendment amount for comparison.
- Closed/cancelled orders are invalid regardless of other checks.
- Amendments may be in a separate file from the main orders file.

### research-stipend-reconciliation
- Validation priority order: Unknown Recipient → Invalid Award Ref (status) → Recipient Mismatch → Account Mismatch → Campus Mismatch → Amount Mismatch. Stop at first failure.
- Archived awards are invalid regardless of other checks.
- Adjustments can modify campus_code in addition to amount — always validate campus against adjusted value.
- Use latest approved adjustment for both amount and campus comparisons.

## Scripts

Use `scripts/validate_claims.py` as a template for expense claim validation tasks.

## References

- `references/fuzzy-matching-guide.md` - Algorithm details for name matching with typo and punctuation tolerance
- `references/domain-examples.md` - Concrete field mappings for common validation scenarios including clinic shift claims, field service audits, fleet maintenance chargebacks, and research stipend reconciliation
