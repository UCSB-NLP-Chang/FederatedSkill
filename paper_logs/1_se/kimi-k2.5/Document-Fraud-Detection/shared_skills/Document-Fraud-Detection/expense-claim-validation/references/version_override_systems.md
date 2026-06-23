# Version Override Systems with Null Handling

## Overview

Some approval systems use version-based overrides where later approved versions can replace earlier values. Unlike amendments that always provide complete records, version systems may have sparse/null fields where the latest approved version's null value intentionally removes or leaves unchanged a field.

## Key Pattern: Null Preserves Previous or Indicates Missing

In version override systems, analyze the sequence carefully:
- If latest approved version has a value → use that value
- If latest approved version has null/empty → check if null means "no value" or "unchanged"
- For amount fields, null typically means "no approved amount" (invalid)
- For participant codes, null is rare; usually the code is preserved

## Example: Clinical Trial Release Versions

```csv
award_ref,version_no,approval_state,version_amount,participant_code
AR-5002,1,approved,1450.0,PC1002
AR-5002,2,approved,,PC1002
AR-5004,1,approved,1025.0,PC1004
AR-5006,1,approved,,PC1005
AR-5006,2,approved,760.0,PC1005
AR-5005,1,rejected,900.0,PC1005
```

### Processing Logic

```python
def get_effective_version(versions_df, award_ref):
    """
    Get effective approved values from version history.
    For amount: latest approved version with non-null amount wins.
    For participant_code: latest approved version's code (usually non-null).
    """
    # Filter to this award and approved state
    award_versions = versions_df[
        (versions_df['award_ref'] == award_ref) &
        (versions_df['approval_state'] == 'approved')
    ]
    
    if len(award_versions) == 0:
        return None
    
    # Sort by version_no ascending to process in order
    sorted_versions = award_versions.sort_values('version_no')
    
    effective = {
        'participant_code': None,
        'version_amount': None,
        'version_no': None
    }
    
    for _, row in sorted_versions.iterrows():
        # Always update participant_code if present (usually non-null)
        if pd.notna(row['participant_code']) and row['participant_code']:
            effective['participant_code'] = row['participant_code']
        
        # For amount: null means "no amount set" - but check if this is override or gap
        # In this system, we take the latest non-null amount from approved versions
        if pd.notna(row['version_amount']):
            effective['version_amount'] = float(row['version_amount'])
            effective['version_no'] = row['version_no']
    
    return effective
```

## Critical Distinction: Null vs Zero

| Scenario | Interpretation | Action |
|----------|---------------|--------|
| `version_amount` is null/empty | No amount specified in this version | Use previous version's amount if valid, else invalid |
| `version_amount` is 0.0 | Explicitly zero | Use zero (valid if system allows) |
| `version_amount` missing from CSV | Parsed as null | Same as null handling |

## Nested JSON Award Structures

Clinical trial and research systems often nest awards under sponsors and programs:

```json
{
  "sponsors": [
    {
      "sponsor_name": "AlphaBio",
      "programs": [
        {
          "program_id": "PG-A",
          "awards": [
            {"award_ref": "AR-5001", "participant_code": "PC1001", "approved_amount": 1200.0, "status": "active"}
          ]
        }
      ]
    }
  ]
}
```

### Flattening Pattern

```python
def flatten_award_catalog(json_path):
    """Flatten nested sponsor/program/award structure."""
    with open(json_path) as f:
        data = json.load(f)
    
    awards = {}
    for sponsor in data.get('sponsors', []):
        for program in sponsor.get('programs', []):
            for award in program.get('awards', []):
                award_ref = award['award_ref']
                awards[award_ref] = {
                    'participant_code': award['participant_code'],
                    'approved_amount': award['approved_amount'],
                    'status': award['status'],  # 'active', 'archived', etc.
                    'program_id': program['program_id'],
                    'sponsor_name': sponsor['sponsor_name']
                }
    
    return awards
```

## Status-Based Invalidation

Awards can be invalidated by status regardless of versions:

```python
def is_award_valid(award_ref, base_awards, versions):
    """Check if award is valid for release request."""
    if award_ref not in base_awards:
        return False, "Invalid Award Ref"
    
    base = base_awards[award_ref]
    
    # Status check: archived, draft, pending = invalid
    if base['status'] != 'active':
        return False, "Invalid Award Ref"  # or "Archived Award"
    
    # Get effective amount from versions
    effective = get_effective_version(versions, award_ref)
    
    if effective is None or effective['version_amount'] is None:
        return False, "Amount Mismatch"  # No approved amount
    
    return True, None
```

## Domain-Specific Field Names

| Generic | Clinical Trial | Research Grant | Fellowship |
|---------|---------------|----------------|------------|
| person_id | participant_code | recipient_id | fellow_id |
| approval_code | award_ref | grant_id | stipend_ref |
| approved_amount | approved_amount / version_amount | grant_value | stipend_amount |
| status | status | state | status |
| payment_account | payment_token | bank_token | disbursement_account |
| page_field | request_page_number | claim_page_number | request_page_number |

## Decision Rules

1. **Reject non-active base status** — An award with `status: 'archived'` is invalid even if versions exist
2. **Process versions in order** — Don't just take max version; process sequentially to handle nulls correctly
3. **Null amount = missing** — If latest approved version has null amount, the award has no valid amount
4. **Preserve participant_code across versions** — Usually constant, but check latest approved version
5. **Rejected versions are ignored** — Only `approval_state == 'approved'` versions count
6. **Amount comparison tolerance** — Use ≤$0.01 tolerance for float comparison

## Alert Reason Mapping

| Issue | Clinical Trial | Research Grant |
|-------|---------------|----------------|
| Unknown person | "Unknown Participant" | "Unknown Recipient" |
| Account mismatch | "Account Mismatch" / "Token Mismatch" | "Account Mismatch" |
| Invalid/archived award | "Invalid Award Ref" | "Invalid Grant ID" |
| Amount mismatch | "Amount Mismatch" | "Amount Mismatch" |
| Ownership mismatch | "Participant Mismatch" | "Recipient Mismatch" |
