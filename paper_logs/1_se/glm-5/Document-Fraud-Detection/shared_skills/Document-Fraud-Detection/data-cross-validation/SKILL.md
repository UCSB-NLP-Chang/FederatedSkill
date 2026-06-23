---
name: data-cross-validation
description: Cross-reference data from multiple file formats (PDF, CSV, xlsx, JSON) to validate records and flag discrepancies. Use when auditing claims, verifying entries against master records, reconciling data across sources, validating work orders against contractor directories, or processing request bundles with revisions.
---

# Data Cross-Validation

## When to Use
- Auditing expense claims, invoices, or transactions against approval records
- Verifying employee or entity data against a master directory
- Reconciling data across multiple source files in different formats
- Validating work orders, service tickets, or requests against reference data
- Processing PDF request bundles with multiple pages and revisions
- Flagging discrepancies, unknown entities, or mismatched values

## Workflow

1. **Identify all data sources** and their formats (PDF, CSV, xlsx, JSON)
2. **Read each source** using the appropriate method:
   - PDF, CSV, JSON, text: Use `Read` tool directly
   - xlsx, xls, other binary formats: Use Python/pandas (see below)
3. **Extract key fields** from each source into comparable structures
4. **For PDF request bundles**: Identify request pages vs cover/appendix pages; deduplicate by keeping highest revision
5. **Define validation rules** based on the task (existence, matching, bounds, status, ownership)
6. **Cross-reference records** and flag any that fail validation
7. **Output flagged records** with clear reason codes

## Reading Binary Files (xlsx, xls)

The `Read` tool cannot read binary Excel files. Use Python/pandas:

```bash
python3 -c "import pandas as pd; df = pd.read_excel('/path/to/file.xlsx'); print(df.to_string())"
```

For structured output, convert to JSON:
```bash
python3 -c "import pandas as pd; df = pd.read_excel('/path/to/file.xlsx'); print(df.to_json(orient='records'))"
```

### Multi-Sheet Excel Files

Excel files may contain multiple sheets with related data (e.g., main records + aliases). Always check for additional sheets:

```bash
python3 -c "import pandas as pd; xl = pd.ExcelFile('/path/to/file.xlsx'); print('Sheets:', xl.sheet_names); [print(f'\n--- Sheet: {s} ---\n', pd.read_excel(xl, s).to_string()) for s in xl.sheet_names]"
```

Common multi-sheet patterns:
- **Main + aliases**: One sheet has canonical names/IDs, another has alternate names for matching
- **Main + revisions**: One sheet has current records, another has version history
- **Main + lookup**: One sheet has transactions, another has reference codes

## PDF Request Bundles

When validating requests from a PDF bundle:

1. **Identify page types**: Cover pages, request pages, appendix/summary pages
2. **Extract request identifiers**: Each request page typically has a packet ID and revision number
3. **Deduplicate by revision**: When the same packet ID appears on multiple pages with different revisions, keep only the highest revision
4. **Skip non-request pages**: Cover pages and appendices typically don't require validation

Example deduplication logic:
- Page 2: PKT-01 Rev 1
- Page 3: PKT-01 Rev 2 → Keep page 3, discard page 2
- Page 10: PKT-07 Rev 1 (Eli Grant)
- Page 11: PKT-07 Rev 1 (Eli Grnt) → Same packet/revision; keep later page or flag both if names differ

## Common Validation Checks

| Check Type | Description | Example Condition |
|------------|-------------|------------------|
| Existence | Entity exists in master records | clinician_id in directory |
| Field Match | Field values match across sources | claimed_amount == approved_amount |
| Reference Validity | Referenced ID exists in lookup | shift_code in crosswalk |
| Ownership | Referenced entity belongs to claimant | trip.employee_id == claim.employee_id |
| Account Match | Bank/account details match directory | claim.bank_account == employee.bank_account |
| Token Mismatch | Token on request doesn't match registry | request.payment_token != participant.payment_token |
| Cross-Reference | Approval/authorization belongs to correct entity | approval.speaker_id == request.speaker_id |
| Award Ownership | Referenced award belongs to different participant | request.award_ref belongs to participant_code != request.participant_code |
| Assignment Mismatch | Resource/code belongs to different entity than claimant | shift.clinician_id != claim.clinician_id |
| Carrier Mismatch | Carrier on request differs from carrier assigned to shipment | request.carrier_id != shipment.carrier_id |
| Amount Mismatch | Requested amount differs from approved amount | request.amount != approval.approved_amount |
| Campus/Location Mismatch | Location code differs from expected (esp. after adjustments) | request.campus_code != award.campus_code |
| Status Validity | Record has acceptable status/lifecycle | work_order.status == 'active', order.lifecycle == 'approved' |
| Archived Record | Referenced record is archived/inactive | award.status == 'archived' → reject |
| Revision Lookup | Use latest approved revision for amounts | max(revision.amount where approval_state == 'approved') |
| Contractor Mismatch | Billing entity differs from work order owner | packet.contractor_id != work_order.contractor_id |
| Unknown Entity | Name/ID not found in master records or aliases | participant_name not in participants and not in aliases |

### Status Field Variations

Status fields may be named differently across files and use different value sets:
- Field names: `status`, `state`, `lifecycle`, `approval_state`, `record_state`, `snapshot_state`
- Value sets: `active`/`archived`, `approved`/`rejected`, `open`/`closed`/`cancelled`, `approved`/`draft`

Always check the actual field name and values in each file rather than assuming a standard naming convention.

## Handling Name Variations

- **Minor typos**: Accept close matches (e.g., "Elis" → "Ellis", "Ptel" → "Patel", "Haan" → "Han")
- **Alias tables**: When Excel has a separate aliases sheet, use it to map alternate names to canonical IDs
- **Unknown entities**: Flag when no reasonable match exists in master directory
- When in doubt, flag for human review rather than silently accepting

## Handling Revisions and Amendments

When reference data has version history, revisions, or amendments:

1. **Check for separate amendment files** - adjustments may be in a separate CSV/JSON rather than the main records
2. **Filter to approved/valid revisions only** (e.g., `decision == 'approved'`, `approval_state == 'approved'`, `snapshot_state == 'approved'`)
3. **Select the highest revision number** for each record
4. **Apply all adjusted fields**, not just amounts - adjustments may modify campus codes, dates, or other fields

Example workflow with separate amendment file:
- Main orders file: MO-9003 has approved_charge $1,150
- Amendments file: MO-9003 has amendment_no 1, amended_charge $1,175, decision 'approved'
- Result: Use $1,175 for validation

Example with campus change:
- Main awards file: AWD-3004 has campus_code CAMP-W
- Adjustments file: AWD-3004 has revision 1, campus_code CAMP-C, state 'approved'
- Result: Validate against CAMP-C, not CAMP-W

Example: Work order WO-8807 has original $6,200, revision 1 at $6,400 (approved), revision 2 at $6,550 (approved). Use $6,550.

### Snapshot Sequence Selection

When reference data has snapshot sequences (e.g., `snapshot_seq`, `version_no`) with state fields:

1. **Filter to approved state only** - ignore `draft`, `pending`, `rejected`, or other non-final states
2. **Select highest sequence with non-empty values** - later snapshots may have empty fields; use the highest sequence where the needed field is populated
3. **Do not cascade empty values** - if snapshot_seq 2 has empty charge, use snapshot_seq 1's charge

Example: Shipment SH-7103 has snapshots:
- seq 1: state='approved', charge=745.0, carrier=CR903
- seq 2: state='approved', charge=(empty), carrier=CR903
- seq 3: state='draft', charge=760.0, carrier=CR903

Result: Use charge=745.0 from seq 1 (seq 2 has empty charge, seq 3 is draft)

## Output Format

Return flagged records as a JSON array with consistent structure:
```json
[
  {
    "record_identifier": "page_2",
    "entity_name": "Victor Han",
    "flag_reason": "Account Mismatch",
    "details": "BAD-702 ≠ PAY-702"
  }
]
```

Match the expected field names for the specific task (e.g., `request_page_number`, `participant_name`, `requested_amount`, `flag_reason`).

## Anti-Patterns

- **Do not** attempt to read xlsx/xls files with the `Read` tool; it will fail with a binary file error
- **Do not** assume Excel files have only one sheet; check for additional sheets that may contain aliases or revisions
- **Do not** assume all names match exactly; watch for typos (e.g., "Chenn" vs "Chen", "Kapor" vs "Kapoor", "Reys" vs "Reyes")
- **Do not** validate only one dimension; check existence, amounts, references, ownership, status, and cross-references
- **Do not** skip the master directory lookup; unknown entities must be flagged
- **Do not** assume an approval code is valid just because it exists; verify it belongs to the correct entity
- **Do not** assume a shift/code belongs to the claiming entity; verify assignment ownership
- **Do not** use original amounts when revisions exist; always check for and apply approved revisions
- **Do not** assume adjustments only modify amounts; check for changes to campus codes, dates, or other fields
- **Do not** assume a work order is valid just because it exists; verify status/lifecycle is active/approved, not closed/cancelled
- **Do not** ignore separate amendment files; check for adjustment CSVs or JSONs that modify base amounts
- **Do not** assume status field names; check for `status`, `state`, `lifecycle`, `approval_state`, `record_state`, `snapshot_state`
- **Do not** use draft/pending/rejected snapshots; filter to approved state before selecting values
- **Do not** let empty values in later snapshots override valid earlier values
- **Do not** validate all pages in a PDF bundle; skip cover pages and appendices, deduplicate by revision
- **Do not** assume a referenced award/record belongs to the requesting entity; verify ownership
- **Do not** accept archived/inactive records as valid references; check status fields

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Read tool fails on file | Check if binary format; use Python/pandas for xlsx |
| Names don't match exactly | Use fuzzy matching or check alias sheet |
| Missing reference data | Verify all source files and sheets were read successfully |
| Inconsistent ID formats | Normalize IDs before comparison (strip whitespace, case) |
| Valid approval but wrong entity | Check cross-reference: approval's associated entity matches request |
| Valid code but wrong owner | Check assignment: code's assigned entity matches claimant |
| Amount discrepancy | Compare billed amount against approved amount (check revisions/amendments) |
| Campus/location mismatch | Check if adjustments modified the campus code; use adjusted value |
| Work order rejected | Verify work order status is active/open, not closed/cancelled |
| Multiple amounts for same record | Check for revision history or separate amendment file; use highest approved revision |
| Unknown contractor name | Check alias sheet for alternate names |
| Amendment not applied | Look for separate amendment/adjustment file; filter by approved status |
| Order exists but invalid | Check lifecycle/status field; reject closed, cancelled, or pending records |
| Status field not found | Check for alternate field names: status, state, lifecycle, approval_state, record_state, snapshot_state |
| Multiple snapshots for same record | Filter to approved state, select highest sequence with non-empty values |
| Carrier mismatch on request | Verify request.carrier_id matches shipment.carrier_id from reference data |
| Empty values in snapshots | Use highest approved snapshot where the needed field is populated, not just highest sequence |
| Token mismatch on request | Verify request.payment_token matches participant.payment_token in registry |
| Award belongs to different participant | Check award.participant_code matches request.participant_code |
| Archived award referenced | Check award.status != 'archived' before accepting as valid reference |
| Multiple pages for same request | Deduplicate by packet ID, keep highest revision number |