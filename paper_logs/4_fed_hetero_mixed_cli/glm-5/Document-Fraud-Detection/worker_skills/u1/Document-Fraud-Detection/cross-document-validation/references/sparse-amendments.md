# Handling Sparse Amendment/Version Tables

Some domains use amendment or version tables where individual rows may contain null or empty values for certain fields. In these cases, the empty value means "do not override" rather than "override with null".

## The Problem

Consider this version table:

```csv
award_ref,version_no,approval_state,version_amount,participant_code
AR-5002,1,approved,1450.0,PC1002
AR-5002,2,approved,,PC1002
AR-5004,1,approved,1025.0,PC1004
AR-5006,1,approved,,PC1005
AR-5006,2,approved,760.0,PC1005
```

For AR-5002 Version 2, `version_amount` is empty. This means "keep the previous amount" (1450.0), NOT "set amount to null/zero".

## The Solution

When applying version/amendment overrides, check for non-null/non-empty values:

```python
import pandas as pd

def get_effective_values(award_ref, base_record, versions_df):
    """
    Resolve effective values from base record and approved versions.
    Only applies non-null override values.
    """
    # Filter to approved versions for this award
    versions = versions_df[
        (versions_df['award_ref'] == award_ref) & 
        (versions_df['approval_state'] == 'approved')
    ]
    
    if versions.empty:
        return base_record
    
    # Get latest version (highest version_no)
    latest = versions.loc[versions['version_no'].idxmax()]
    
    # Start with base values
    effective = dict(base_record)
    
    # Only override fields that have actual values (not null/empty/NaN)
    for field in ['version_amount', 'participant_code', 'campus_code']:
        if field in latest and pd.notna(latest[field]) and str(latest[field]).strip() != '':
            effective[field] = latest[field]
    
    return effective
```

## Key Rule

**Only apply override fields that contain non-null values.** Empty strings, NaN, and missing values in amendment rows should be ignored, keeping the base approval value.

## Common Sparse Fields

| Field | Meaning When Empty |
|-------|-------------------|
| `version_amount` | Keep base approved amount |
| `participant_code` | Keep base participant assignment |
| `campus_code` | Keep base location |
| `status` | Keep base status |

## Anti-Pattern

```python
# WRONG - blindly applies empty values
if not versions.empty:
    latest = versions.loc[versions['version_no'].idxmax()]
    return latest['version_amount']  # May return NaN!

# CORRECT - check for non-null
if not versions.empty:
    latest = versions.loc[versions['version_no'].idxmax()]
    if pd.notna(latest['version_amount']):
        return latest['version_amount']
    return base_amount
```
