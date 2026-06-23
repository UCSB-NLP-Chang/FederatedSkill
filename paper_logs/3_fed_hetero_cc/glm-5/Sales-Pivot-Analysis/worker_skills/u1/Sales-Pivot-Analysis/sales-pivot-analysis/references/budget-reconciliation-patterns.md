# Budget Reconciliation Data Patterns

Patterns for budget reconciliation reports that join expense transactions with org hierarchy PDFs and wide-format budget allocations.

## Data Sources

| Source | Format | Key Columns | Purpose |
|--------|--------|-------------|---------|
| Expense transactions | CSV | tx_id, team_code, expense_category, amount, fiscal_quarter | Actual spending records |
| Org hierarchy | PDF | team_code, DEPT_NAME, DIVISION | Maps teams to departments and divisions |
| Budget allocations | XLSX (wide) | DEPT_NAME, CATEGORY, Q1_BUDGET, Q2_BUDGET, Q3_BUDGET, Q4_BUDGET | Planned budget by dept/category/quarter |

## Wide-to-Long Budget Transformation

Budget XLSX files often store quarters as separate columns. Transform to long format before joining:

```python
budget_long = budget_wide.melt(
    id_vars=['DEPT_NAME', 'CATEGORY'],
    value_vars=['Q1_BUDGET', 'Q2_BUDGET', 'Q3_BUDGET', 'Q4_BUDGET'],
    var_name='fiscal_quarter',
    value_name='BUDGET_AMOUNT'
)
# Normalize quarter names: 'Q1_BUDGET' -> 'Q1'
budget_long['fiscal_quarter'] = budget_long['fiscal_quarter'].str.replace('_BUDGET', '')
```

## Join Sequence

1. **Expenses + Org Hierarchy** (left join on team_code)
2. **Result + Budget Long** (left join on DEPT_NAME + expense_category + fiscal_quarter)

```python
# Step 1: Join expenses with org hierarchy
merged = expenses.merge(org_df, on='team_code', how='left')

# Step 2: Join with budget (composite key)
merged = merged.merge(
    budget_long,
    left_on=['DEPT_NAME', 'expense_category', 'fiscal_quarter'],
    right_on=['DEPT_NAME', 'CATEGORY', 'fiscal_quarter'],
    how='left'
)
```

## Derived Columns

```python
# Variance: actual spending minus budget (negative = under budget)
merged['VARIANCE'] = merged['amount'] - merged['BUDGET_AMOUNT']

# Utilization: actual spending as fraction of budget
merged['UTILIZATION_PCT'] = merged['amount'] / merged['BUDGET_AMOUNT']
```

## Common Pivot Configurations

### Spending by Division
```python
pd.pivot_table(merged, index='DIVISION', values='amount', aggfunc='sum').reset_index()
# Rename columns: ['DIVISION', 'Sum of amount']
```

### Spending by Department
```python
pd.pivot_table(merged, index='DEPT_NAME', values='amount', aggfunc='sum').reset_index()
# Rename columns: ['DEPT_NAME', 'Sum of amount']
```

### Variance by Department
```python
pd.pivot_table(merged, index='DEPT_NAME', values='VARIANCE', aggfunc='sum').reset_index()
# Rename columns: ['DEPT_NAME', 'Sum of VARIANCE']
```

### Category Quarter Matrix
```python
pd.pivot_table(
    merged,
    index='expense_category',
    columns='fiscal_quarter',
    values='amount',
    aggfunc='sum',
    fill_value=0
).reset_index()
# Columns: ['expense_category', 'Q1', 'Q2', 'Q3', 'Q4']
```

### Avg Utilization by Division
```python
pd.pivot_table(merged, index='DIVISION', values='UTILIZATION_PCT', aggfunc='mean').reset_index()
# Rename columns: ['DIVISION', 'Average of UTILIZATION_PCT']
```

## Verification Points

1. All expense rows should join to org hierarchy (check for null DEPT_NAME/DIVISION)
2. Budget join may produce nulls if expense category doesn't match budget CATEGORY exactly
3. VARIANCE should be negative when spending < budget (under budget)
4. UTILIZATION_PCT should be between 0 and 1 for normal cases (may exceed 1 if over budget)
5. Negative amounts in expenses (refunds/credits) are valid and should be preserved
6. Sheet names must match spec exactly (e.g., 'Spending by Division', not 'Spending By Division')