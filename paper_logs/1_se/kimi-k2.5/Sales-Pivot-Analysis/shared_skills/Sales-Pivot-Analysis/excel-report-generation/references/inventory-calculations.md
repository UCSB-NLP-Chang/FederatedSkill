# Inventory Calculations Reference

## Core Inventory Metrics

### Value and Weight Calculations

```python
# Extended value metrics
df['TOTAL_VALUE'] = df['QUANTITY_ON_HAND'] * df['UNIT_VALUE']
df['TOTAL_WEIGHT'] = df['QUANTITY_ON_HAND'] * df['UNIT_WEIGHT']

# Per-unit verification (catch data entry errors)
df['UNIT_VALUE_CHECK'] = df['TOTAL_VALUE'] / df['QUANTITY_ON_HAND'].replace(0, float('nan'))
value_mismatch = df[abs(df['UNIT_VALUE_CHECK'] - df['UNIT_VALUE']) > 0.01]
```

### Stock Status Tiers

```python
def stock_status(row):
    """Classify stock level based on quantity vs thresholds."""
    qty = row['QUANTITY_ON_HAND']
    
    # Handle missing reorder point (use median or category average)
    reorder_point = row.get('REORDER_POINT', 0)
    
    if qty == 0:
        return 'out_of_stock'
    elif qty < reorder_point * 0.5:
        return 'critical'
    elif qty < reorder_point:
        return 'low'
    elif qty < reorder_point * 2:
        return 'adequate'
    else:
        return 'surplus'

df['STOCK_STATUS'] = df.apply(stock_status, axis=1)
```

### Reorder Flagging

```python
# Simple threshold
df['REORDER_FLAG'] = (df['QUANTITY_ON_HAND'] < df['REORDER_POINT']).map(
    {True: 'Yes', False: 'No'}
)

# With safety stock consideration
def needs_reorder(row):
    if pd.isna(row['REORDER_POINT']):
        return 'No'  # No reorder point defined
    buffer = row.get('SAFETY_STOCK', 0)
    effective_threshold = row['REORDER_POINT'] + buffer
    return 'Yes' if row['QUANTITY_ON_HAND'] < effective_threshold else 'No'

df['REORDER_FLAG'] = df.apply(needs_reorder, axis=1)
```

### Value Tier Assignment

Percentile-based approach (adapts to dataset):

```python
def assign_value_tiers(df, value_col='TOTAL_VALUE', method='percentile'):
    """
    Assign value tiers based on distribution.
    
    method: 'percentile' | 'fixed' | 'category_relative'
    """
    if method == 'percentile':
        # Dataset-adaptive thresholds
        p95 = df[value_col].quantile(0.95)
        p75 = df[value_col].quantile(0.75)
        
        def tier(val):
            if pd.isna(val) or val <= 0:
                return 'invalid'
            elif val >= p95:
                return 'high'
            elif val >= p75:
                return 'medium'
            else:
                return 'low'
        
        df['VALUE_TIER'] = df[value_col].apply(tier)
        
    elif method == 'fixed':
        # Absolute thresholds (customize for your domain)
        bins = [0, 1000, 10000, float('inf')]
        labels = ['low', 'medium', 'high']
        df['VALUE_TIER'] = pd.cut(df[value_col], bins=bins, labels=labels)
        
    elif method == 'category_relative':
        # Percentiles within each category
        df['VALUE_TIER'] = df.groupby('CATEGORY')[value_col].transform(
            lambda x: pd.qcut(x, q=[0, 0.75, 0.95, 1.0], 
                            labels=['low', 'medium', 'high'],
                            duplicates='drop')
        )
    
    return df

# Apply with percentile method (recommended for diverse datasets)
df = assign_value_tiers(df, method='percentile')
```

## Warehouse-Specific Patterns

### Multi-Warehouse Consolidation

```python
# Combine inventory from multiple locations
all_inventory = []
for warehouse_file in ['warehouse_a.xlsx', 'warehouse_b.xlsx']:
    df = pd.read_excel(warehouse_file)
    df['WAREHOUSE'] = warehouse_file.split('_')[0].upper()  # or explicit mapping
    all_inventory.append(df)

combined = pd.concat(all_inventory, ignore_index=True)

# Verify no duplicate records across warehouses
duplicate_check = combined.duplicated(subset=['SKU', 'WAREHOUSE']).sum()
assert duplicate_check == 0, f"Found {duplicate_check} duplicate warehouse/SKU combinations"
```

### Cross-Warehouse Analysis

```python
# Stock by category across warehouses
stock_by_cat = combined.groupby('CATEGORY')['QUANTITY_ON_HAND'].sum().reset_index()

# Value by warehouse
value_by_wh = combined.groupby('WAREHOUSE')['TOTAL_VALUE'].sum().reset_index()

# Category-warehouse matrix (values)
wh_matrix = combined.pivot_table(
    values='TOTAL_VALUE',
    index='CATEGORY',
    columns='WAREHOUSE',
    aggfunc='sum',
    fill_value=0
).reset_index()

# Item counts by category (distinct SKUs)
items_by_cat = combined.groupby('CATEGORY')['SKU'].nunique().reset_index(name='ITEM_COUNT')
```

## Standard Warehouse Report Structure

Recommended 5-sheet structure for multi-warehouse inventory reports:

| Sheet | Content | Key Columns |
|-------|---------|-------------|
| **SourceData** | All enriched records | SKU, CATEGORY, WAREHOUSE, QUANTITY_ON_HAND, UNIT_VALUE, UNIT_WEIGHT, TOTAL_VALUE, TOTAL_WEIGHT, REORDER_FLAG, STOCK_STATUS, VALUE_TIER |
| **Stock by Category** | Total units per category | CATEGORY, QUANTITY_ON_HAND |
| **Value by Warehouse** | Total value per location | WAREHOUSE, TOTAL_VALUE |
| **Items by Category** | Distinct SKU counts | CATEGORY, ITEM_COUNT |
| **Category Warehouse Matrix** | Cross-tab of value by category×warehouse | CATEGORY, Warehouse-A, Warehouse-B, ... |

```python
with pd.ExcelWriter('inventory_report.xlsx', engine='openpyxl') as writer:
    # Sheet 1: Full detail
    combined.to_excel(writer, sheet_name='SourceData', index=False)
    
    # Sheet 2: Stock totals by category
    combined.groupby('CATEGORY')['QUANTITY_ON_HAND'].sum().reset_index().to_excel(
        writer, sheet_name='Stock by Category', index=False)
    
    # Sheet 3: Value by warehouse
    combined.groupby('WAREHOUSE')['TOTAL_VALUE'].sum().reset_index().to_excel(
        writer, sheet_name='Value by Warehouse', index=False)
    
    # Sheet 4: Item counts by category
    combined.groupby('CATEGORY')['SKU'].nunique().reset_index(name='COUNT').to_excel(
        writer, sheet_name='Items by Category', index=False)
    
    # Sheet 5: Cross-tab matrix
    combined.pivot_table(
        values='TOTAL_VALUE',
        index='CATEGORY',
        columns='WAREHOUSE',
        aggfunc='sum',
        fill_value=0
    ).reset_index().to_excel(writer, sheet_name='Category Warehouse Matrix', index=False)
```

## Data Quality Checks for Inventory

```python
def validate_inventory(df):
    """Run standard inventory data quality checks."""
    issues = []
    
    # Negative quantities
    neg_qty = df[df['QUANTITY_ON_HAND'] < 0]
    if len(neg_qty) > 0:
        issues.append(f"Negative quantities: {len(neg_qty)} records")
    
    # Zero unit values (will break tier calculations)
    zero_val = df[df['UNIT_VALUE'] <= 0]
    if len(zero_val) > 0:
        issues.append(f"Zero/negative unit values: {len(zero_val)} records")
    
    # Missing SKUs in product master (post-join check)
    unmatched = df[df['CATEGORY'].isna()]['SKU'].nunique()
    if unmatched > 0:
        issues.append(f"SKUs without category match: {unmatched}")
    
    # Duplicate SKU+warehouse combinations
    dups = df.duplicated(subset=['SKU', 'WAREHOUSE']).sum()
    if dups > 0:
        issues.append(f"Duplicate warehouse/SKU records: {dups}")
    
    return issues

# Run before final output
issues = validate_inventory(combined)
for issue in issues:
    print(f"WARNING: {issue}")
```

## Verification Checklist

After generating report:

- [ ] SourceData has all expected enriched columns (TOTAL_VALUE, TOTAL_WEIGHT, REORDER_FLAG, STOCK_STATUS, VALUE_TIER)
- [ ] Sum of Stock by Category quantities equals total in SourceData
- [ ] Sum of Value by Warehouse equals grand total in SourceData
- [ ] All 5 sheets present with exact names (case-sensitive)
- [ ] No index column in output sheets (verify `index=False`)
- [ ] VALUE_TIER has reasonable distribution (not all 'low' or 'high')
- [ ] Category Warehouse Matrix columns match actual warehouse names in data
