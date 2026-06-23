# Sales Metrics Reference

Domain-specific formulas for sales/business pivot reports.

## Input Schema

**Excel transactions:**
- PRODUCT_ID (join key)
- QUANTITY (numeric, positive)
- UNIT_PRICE (numeric)
- REGION (categorical)
- TRANSACTION_ID (unique identifier)

**PDF catalog:**
- PRODUCT_ID (join key)
- CATEGORY (categorical)
- UNIT_COST (numeric)

## Derived Columns

```python
# REVENUE: Total sales amount
merged['REVENUE'] = merged['QUANTITY'] * merged['UNIT_PRICE']

# PROFIT: Revenue minus cost of goods
merged['PROFIT'] = merged['REVENUE'] - (merged['QUANTITY'] * merged['UNIT_COST'])

# MARGIN_PCT: Profit margin as decimal
merged['MARGIN_PCT'] = merged['PROFIT'] / merged['REVENUE']
```

**Note:** MARGIN_PCT can be negative if costs exceed revenue. Do not clamp to [0, 1].

## Pivot Tables

1. **Revenue by Category** — sum of REVENUE grouped by CATEGORY
2. **Units by Region** — sum of QUANTITY grouped by REGION
3. **Category-Region Matrix** — sum of REVENUE, rows=CATEGORY, columns=REGION

```python
pivot_revenue = merged.pivot_table(index='CATEGORY', values='REVENUE', aggfunc='sum').reset_index()
pivot_units = merged.pivot_table(index='REGION', values='QUANTITY', aggfunc='sum').reset_index()
pivot_matrix = merged.pivot_table(index='CATEGORY', columns='REGION', values='REVENUE', aggfunc='sum').reset_index()
```

## Sheet Names (typical)

- "Revenue by Category"
- "Units by Region"
- "Category Region Matrix"
- "SourceData"

**Always use exact names from task specification.**
