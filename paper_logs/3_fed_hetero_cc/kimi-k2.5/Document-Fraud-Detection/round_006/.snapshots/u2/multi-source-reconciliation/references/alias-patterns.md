# Alias Resolution Strategies

## Overview

Entity registries often contain multiple valid names for the same entity. Common patterns:

- **DBA names**: "Northwind Ltd" → "Northwind Services"
- **Abbreviated forms**: "Apex Field Ops" → "Apex Field Operations"
- **Corporate suffix variations**: "Summit Cooling", "Summit Cooling Co", "Summit Cooling Company"
- **Spacing variations**: "BluePeak Mechanical" → "Blue Peak Mechanical"

## Data Source Patterns

### Excel Multi-Sheet Pattern

```
Sheet: contractors
  contractor_id | legal_name           | payment_account
  C301          | Northwind Services   | ACC-NW-1

Sheet: aliases
  contractor_id | alias_name
  C301          | Northwind Ltd
```

**Detection**: Always check `pd.ExcelFile('file.xlsx').sheet_names` for 'aliases', 'aka', 'alt_names'.

### Single-Table Pattern

```
contractor_id | primary_name         | aliases (comma-separated)
C301          | Northwind Services   | Northwind Ltd,NW Services
```

## Resolution Strategy

1. Build alias index: `{normalized_alias: entity_id}`
2. Build primary index: `{normalized_primary_name: entity_id}`
3. Lookup order: exact alias match → exact primary match → fuzzy match (edit distance ≤ 1)
4. Unknown Entity: only flag if all three fail

## Normalization Rules

```python
def normalize(name: str) -> str:
    name = name.lower().strip()
    name = ' '.join(name.split())  # collapse whitespace
    # Strip common corporate suffixes
    for suffix in [' llc', ' inc', ' corp', ' co', ' company', ' ltd']:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    return name.strip()
```