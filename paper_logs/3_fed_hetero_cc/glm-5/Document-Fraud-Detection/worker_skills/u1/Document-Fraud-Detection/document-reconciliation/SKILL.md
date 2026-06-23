---
name: document-reconciliation
description: Cross-validate records across multiple data sources (PDF, Excel, CSV, JSON) to identify discrepancies, validate claims, and flag anomalies. Handles fuzzy matching for typos, exact ID/account validation, multi-hop reference lookups via crosswalk tables, alias name matching, work order status checks, revision/amendment amount and field resolution, snapshot-based value derivation, input record deduplication by packet/revision, and structured discrepancy reporting. Use for expense screening, claim validation, audit tasks, speaker honorarium reviews, vendor payments, field service billing, healthcare shift claims, fleet maintenance chargebacks, stipend disbursements, award reconciliations, cold-chain shipping charge review, clinical trial participant releases, or any multi-source data reconciliation.
---

# Document Reconciliation & Validation

Cross-validate records across heterogeneous data sources with fuzzy matching for common data entry errors.

## When to Use

- Validating expense claims against employee directories and approval records
- Matching entities across PDF forms, Excel databases, CSV exports, and JSON files
- Detecting specific violation types: unknown entities, mismatched accounts, invalid references, entity-reference mismatches, adjusted field mismatches
- Tasks where source data may contain typos (names, IDs) that should be matched fuzzily
- Multi-hop reference validation (external code → crosswalk → internal reference → approval)
- Work order or approval-based billing validation with status checks and revisions/amendments
- Fleet maintenance chargebacks, vendor payments, contractor billing audits
- Stipend disbursements, award reconciliations, grant validations
- Cold-chain shipping charge review with snapshot-based amount derivation
- Clinical trial participant release audits with packet revision handling
- Any multi-source data reconciliation requiring cross-reference validation

## Workflow

1. **Load all reference data first**
   - CSV: `pd.read_csv()` or direct text parsing
   - Excel: `pd.read_excel()` via Python/Bash (Read tool cannot read binary .xlsx files)
   - Excel with multiple sheets: `pd.ExcelFile(path)` then `parse(sheet_name)` for each sheet
   - PDF: Use `pdfplumber` for structured extraction; fallback to `Read` tool for text extraction
   - JSON: `json.load()`; flatten nested structures (e.g., orders under depots, awards under programs) into lookup dicts

2. **Build lookup indexes**
   - Entity directory: `{id: {name, account, ...}}`
   - Alias table: `{alias_name: entity_id}` for alternate name matching (including initial variants)
   - Approvals/authorizations: `{ref_id: {amount, owner_id, status, record_state, ...}}`
   - Snapshots/revisions (if present): `{ref_id: [{seq, amount, carrier_id, state, ...}]}`
   - Crosswalk (if present): `{external_code: internal_code}` for multi-hop lookups
   - Name-to-ID index for fuzzy matching: `{normalized_name: id}`

3. **Handle nested JSON structures**
   - If reference data has nested structure (e.g., orders under depots, awards under programs):
     1. Iterate through parent containers
     2. Extract and flatten child records into a single lookup dict
     3. Preserve parent context if needed (depot, region, sponsor, etc.)
   - Example: `for sponsor in data['sponsors']: for program in sponsor['programs']: for award in program['awards']: awards[award['award_ref']] = award`

4. **Handle multi-hop reference lookups**
   - If records use external codes (e.g., SHIFT-A1) but approvals use internal codes:
     1. Look up external code in crosswalk → get internal code
     2. Look up internal code in approvals → get approved amount and assigned entity
   - If external code not in crosswalk: flag as "Invalid Reference Code"

5. **Deduplicate input records by packet/revision (if applicable)**
   - If input records (PDF pages, form submissions) have packet_id and revision fields:
     1. Group records by packet_id
     2. Within each group, keep only the highest revision
     3. Discard superseded records before validation
   - This prevents validating stale requests that were later revised
   - If same revision appears multiple times, keep the last occurrence

6. **Apply Multi-Source Validation Precedence (CRITICAL)**
   
   When BOTH authorizations AND snapshots/revisions exist for a reference:
   
   ```
   Record.ref_id (e.g., SH-7103)
          ↓
   Step A: Check authorizations for EXISTENCE
          ↓ Not found → Invalid Reference ID
          Found → Proceed to Step B
          ↓
   Step B: Check authorization STATUS/RECORD_STATE
          ↓ draft/closed/inactive/archived → Invalid Reference Status
          approved/active → Proceed to Step C
          ↓
   Step C: Get EXPECTED VALUES from snapshots (NOT authorizations)
          ↓ Filter: snapshot_state='approved'
          ↓ Skip: entries with null/empty amounts
          ↓ Select: highest snapshot_seq
          ↓ Use: expected_charge, carrier_id from that snapshot
          ↓
   Step D: Validate carrier/entity assignment
          ↓ Mismatch → Carrier/Entity Mismatch
          ↓
   Step E: Validate amount
          ↓ Mismatch → Amount Mismatch
   ```
   
   **If only one source exists**: Use it for both existence AND expected values.
   
   **Critical**: Do NOT use authorization amount when snapshots exist. Snapshots override.

7. **Handle snapshot/revision/amendment resolution**
   - Filter to approved entries only (`snapshot_state='approved'`, `state='approved'`, `decision='approved'`)
   - Skip entries with null/empty amounts (common in snapshots)
   - Use highest sequence/revision number's values as expected values
   - Multi-field adjustments: amount AND campus_code/location/temperature_band may change
   - Build effective value lookup: `{ref_id: {expected_amount, effective_campus, carrier_id, ...}}`

8. **Normalize for fuzzy matching**
   - Lowercase, strip extra spaces
   - Allow single-character differences (insertion/deletion/substitution)
   - Match if edit distance ≤ 1 for names with length > 5
   - Check alias table before fuzzy matching (includes initial variants like "First L.")

9. **Validate each record sequentially (priority order)**
   | Check | Failure Condition | Details |
   |-------|-------------------|---------|
   | Unknown Entity | Name doesn't match any entity (exact, alias, or fuzzy) | Check alias table first |
   | Account Mismatch | Record account ≠ entity's registered account | Verify after entity match |
   | Invalid Reference Code | External code not in crosswalk | Multi-hop lookup failed at step 1 |
   | Invalid Reference ID | Internal code not in authorizations | Exists nowhere, not just invalid status |
   | Invalid Reference Status | Reference exists but status is draft/closed/inactive/archived | Use authorization status check |
   | Entity-Reference Mismatch | Snapshot's carrier_id ≠ record's entity_id | Carrier/Provider/Owner Mismatch aliases |
   | Adjusted Field Mismatch | Record field ≠ adjusted value from revision | Campus, location, temperature_band |
   | Amount Mismatch | abs(claimed - expected) > $0.01 | Use snapshot/revision amount, not authorization |

10. **Output structured results**
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
- **Don't ignore reference status**; closed/inactive/archived references are invalid
- **Don't use authorization amount when snapshots exist**; snapshots provide expected values
- **Don't skip status check because snapshots exist**; check authorization status first
- **Don't use original amount if revisions/amendments/snapshots exist**; use highest approved
- **Don't only check amount adjustments**; revisions may change campus, location, temperature_band
- **Don't assume flat JSON**; check for nested structures and flatten as needed
- **Don't trust empty amounts in snapshots**; skip null/empty and use next highest approved
- **Don't validate superseded input records**; deduplicate by packet_id/revision first

## Known invariants (by sub-task)

- **expense-claim-validation**: Standard cross-reference with fuzzy name matching
- **speaker-honorarium-review**: Validate speaker names, payment accounts, approval codes, requested fees
- **clinic-shift-claim-review**: Crosswalk lookup, check shift code validity and authorization
- **field-service-workorder-audit**: Alias resolution, WO status must be 'active', highest approved revision
- **fleet-maintenance-chargeback**: Provider alias resolution, order lifecycle must be 'approved', highest amendment
- **research-stipend-reconciliation**: Recipient name matching with initial variants, award-level state check (archived=invalid), revision handling for amount AND campus
- **warehouse-coldchain-charge-review**: Carrier alias resolution (Ltd suffixes), shipment authorization status check (draft=invalid), snapshot-based amount derivation (highest approved seq with non-null amount), carrier-shipment ownership validation
- **clinical-trial-participant-release-audit**: Participant alias resolution, award status check (archived=invalid), version-based amount derivation (highest approved with non-empty amount), packet revision deduplication in PDF pages

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| Read tool fails on Excel | Use `python3 -c "import pandas as pd; df = pd.read_excel('file.xlsx'); print(df.to_csv(index=False))"` |
| Excel has multiple sheets | Use `pd.ExcelFile(path)` then check `xl.sheet_names` and parse each |
| PDF extraction fails | Use `pdfplumber` via Python import; fallback to `pdftotext` CLI |
| JSON has nested structure | Iterate parent containers, flatten children into single lookup dict |
| Wrong amount used | Check for snapshots/revisions; use highest approved with non-null amount |
| Valid reference flagged | Check if ref exists but has invalid status → "Invalid Reference Status", not "Invalid Reference ID" |
| Snapshot has empty amount | Skip null/empty entries, use next highest approved snapshot_seq |
| Carrier mismatch missed | Compare snapshot's carrier_id to record's matched entity_id, not names |
| Multi-source confusion | Authorizations for existence+status; snapshots for expected values |
| Multiple pages for same request | Check for packet_id/revision fields, keep only highest revision per packet |
| Same revision multiple times | Keep the last occurrence (later page supersedes earlier) |

## References

- `references/violation-types.md` — Detailed validation rules and priority order
- `references/amendment-handling.md` — Snapshot/revision/amendment processing patterns with code
- `scripts/reconcile_claims.py` — Reusable Python template for claim validation