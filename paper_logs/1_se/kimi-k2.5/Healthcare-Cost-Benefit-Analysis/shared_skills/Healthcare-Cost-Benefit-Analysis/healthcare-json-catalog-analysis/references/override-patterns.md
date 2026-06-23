# Patient Override Patterns

## Standard Override Structure

```csv
therapy_code,revision,status,active_patients
HINF-ALPHA,1,draft,88
HINF-ALPHA,2,approved,92
HINF-BETA,1,approved,78
```

## Selection Algorithm

```python
def resolve_patients(overrides: list[dict], therapy_code: str) -> int | None:
    """
    Select patient count using approval workflow rules.
    """
    # Filter to target therapy
    therapy_rows = [r for r in overrides if r['therapy_code'] == therapy_code]
    
    # Filter to approved status only
    approved = [r for r in therapy_rows if r['status'] == 'approved']
    
    if not approved:
        return None  # Therapy has no approved patient count
    
    # Select highest revision number
    highest = max(approved, key=lambda r: int(r['revision']))
    
    return int(highest['active_patients'])
```

## Status Values

| Status | Meaning | Include? |
|--------|---------|----------|
| `approved` | Valid, active patient count | ✅ Yes |
| `draft` | Pending review, not finalized | ❌ No |
| `rejected` | Invalidated, superseded | ❌ No |
| `pending` | Awaiting approval | ❌ No |

## Revision Handling

- Higher revision number = more recent
- Revisions are per-therapy_code, not global
- Draft revisions with higher numbers do NOT supersede approved lower revisions
- Must have `status=approved` AND highest revision

## Edge Cases

### No approved rows
Therapy is excluded from analysis or uses default patient count.

### Missing therapy_code in overrides
May use catalog default or be excluded; check task requirements.

### Same revision number
Rare collision; use row order or explicit tiebreaker if specified.