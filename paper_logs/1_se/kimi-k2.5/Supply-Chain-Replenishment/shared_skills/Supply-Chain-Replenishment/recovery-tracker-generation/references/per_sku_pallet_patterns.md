# Per-SKU Pallet Sizing Patterns

## Pallet Guide Sheet Structures

### Pattern A: Simple Two-Column
| SKU | Cases Per Pallet |
|-----|------------------|
| SKU-01 | 48 |
| SKU-02 | 60 |

### Pattern B: With Description
| SKU | Description | Units Per Pallet |
|-----|-------------|------------------|
| SKU-01 | Widget A | 48 |
| SKU-02 | Widget B | 60 |

### Pattern C: Mixed Units
| SKU | Cases Per Pallet | Pallet Weight |
|-----|------------------|---------------|
| SKU-01 | 48 | 500kg |

## Detection Heuristics

```python
# Detect Pallet Guide sheet
if any(x in sheet_name.lower() for x in ['pallet', 'guide', 'config', 'sizing']):
    likely_pallet_sheet = sheet_name

# Detect columns
for cell in header_row:
    if cell:
        lower = str(cell).lower()
        if 'sku' in lower or 'item' in lower:
            sku_col = idx
        if 'per pallet' in lower or 'pallet size' in lower:
            size_col = idx
        if 'case' in lower or 'unit' in lower:
            size_col = idx

# Build lookup
pallet_sizes = {}
for row in data_rows:
    sku = row[sku_col]
    size = row[size_col]
    if sku and isinstance(size, (int, float)):
        pallet_sizes[sku] = int(size)
```

## Validation

- Verify all stock SKUs exist in pallet_sizes dict
- Log warning for missing SKUs (use default or skip)
- Common defaults: 48, 60, 72, 96 units per pallet
