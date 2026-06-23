---
name: budget-reconciliation-pivot
description: Generate multi-sheet Excel reports from budget allocations and expense transactions joined with organizational hierarchies. Handles wide-to-long budget transformation, variance calculations, utilization metrics, and standard financial analytics by division, department, category, and fiscal quarter. Use when tasks require reconciling actual spending against budget plans, computing variance analysis, or creating financial utilization reports from multi-source data (PDF org charts, CSV transactions, Excel budget files).
---

# Budget Reconciliation Pivot Report Generation

Create comprehensive budget reconciliation reports by joining expense transactions with organizational hierarchies and budget allocations, computing variance and utilization metrics, and generating multi-dimensional financial summaries.

## When to Use

- Reconciling actual expense transactions against planned budget allocations
- Analyzing spending patterns by organizational dimensions (division, department, category)
- Computing variance (budget minus actual) and utilization rates (actual/budget)
- Transforming wide-format budget files (Q1_BUDGET, Q2_BUDGET columns) to long format for analysis
- Creating fiscal period cross-tabulations (category × quarter matrices)
- Financial reporting with drill-down from summary to transaction-level detail

## Standard Workflow

### 1. Parse Organizational Hierarchy (PDF)

Extract team/department/division mapping from PDF org charts:

```python
import re

# Common pattern: TEAM_CODE, TEAM_NAME, DEPT_NAME, DIVISION
pattern = r'(T\d{3})\s+([\w\s]+?)\s+([\w\s]+?)\s+(Business|Technology|Operations)'
matches = re.findall(pattern, pdf_text)
org_df = pd.DataFrame(matches, columns=['TEAM_CODE', 'TEAM_NAME', 'DEPT_NAME', 'DIVISION'])
```

**See `references/pdf-org-patterns.md` for alternative formats.**

### 2. Load Transaction and Budget Data

**Expenses (CSV):**
```python
expenses = pd.read_csv('/path/to/expense_transactions.csv')
# Expected: tx_id, team_code, expense_category, amount, fiscal_quarter
```

**Budget allocations (Excel):** Use pandas, NOT `Read` tool:
```python
budget = pd.read_excel('/path/to/budget_allocations.xlsx')
# Wide format: DEPT_NAME, expense_category, Q1_BUDGET, Q2_BUDGET, Q3_BUDGET, Q4_BUDGET
```

### 3. Transform Wide Budget to Long Format

Budget files typically store quarterly allocations as columns. Convert to long format for joining:

```python
# Identify quarter columns
quarter_cols = ['Q1_BUDGET', 'Q2_BUDGET', 'Q3_BUDGET', 'Q4_BUDGET']
id_vars = [c for c in budget.columns if c not in quarter_cols]

# Melt to long format
budget_long = budget.melt(
    id_vars=id_vars,
    value_vars=quarter_cols,
    var_name='budget_quarter_col',
    value_name='BUDGET_AMOUNT'
)

# Extract quarter designation
budget_long['fiscal_quarter'] = budget_long['budget_quarter_col'].str.extract(r'(Q\d)')
budget_long = budget_long[budget_long['BUDGET_AMOUNT'].notna()]
```

### 4. Join Datasets

**Join order:** Expenses → Org (on team_code) → Budget (on dept + category + quarter)

```python
# Step 1: Expenses to Org
merged = expenses.merge(org_df, left_on='team_code', right_on='TEAM_CODE', how='left')

# Step 2: Enriched expenses to Budget
# Match on DEPT_NAME, expense_category, fiscal_quarter
merged = merged.merge(
    budget_long[['DEPT_NAME', 'expense_category', 'fiscal_quarter', 'BUDGET_AMOUNT']],
    on=['DEPT_NAME', 'expense_category', 'fiscal_quarter'],
    how='left'
)

# Verify join coverage
unmatched_budget = merged['BUDGET_AMOUNT'].isna().sum()
if unmatched_budget > 0:
    print(f"WARNING: {unmatched_budget} expenses without matching budget allocation")
```

### 5. Calculate Financial Metrics

```python
# Variance: Negative = under budget, Positive = over budget
merged['VARIANCE'] = merged['amount'] - merged['BUDGET_AMOUNT']

# Utilization rate: actual spending as percentage of budget
merged['UTILIZATION_PCT'] = (merged['amount'] / merged['BUDGET_AMOUNT']).replace([float('inf'), -float('inf')], float('nan'))

# Alternative with zero handling
merged['UTILIZATION_PCT'] = merged.apply(
    lambda r: r['amount'] / r['BUDGET_AMOUNT'] if r['BUDGET_AMOUNT'] != 0 else float('nan'),
    axis=1
)
```

### 6. Generate Pivot Summary Sheets

```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    # Sheet 1: Source data with all enrichments
    merged.to_excel(writer, sheet_name='SourceData', index=False)
    
    # Sheet 2: Spending by Division
    div_spend = merged.groupby('DIVISION')['amount'].sum().reset_index()
    div_spend.columns = ['DIVISION', 'Sum of amount']
    div_spend.to_excel(writer, sheet_name='Spending by Division', index=False)
    
    # Sheet 3: Spending by Department
    dept_spend = merged.groupby('DEPT_NAME')['amount'].sum().reset_index()
    dept_spend.columns = ['DEPT_NAME', 'Sum of amount']
    dept_spend.to_excel(writer, sheet_name='Spending by Department', index=False)
    
    # Sheet 4: Variance by Department
    dept_var = merged.groupby('DEPT_NAME')['VARIANCE'].sum().reset_index()
    dept_var.to_excel(writer, sheet_name='Variance by Department', index=False)
    
    # Sheet 5: Category × Quarter Matrix
    matrix = merged.pivot_table(
        values='amount',
        index='expense_category',
        columns='fiscal_quarter',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    matrix.to_excel(writer, sheet_name='Category Quarter Matrix', index=False)
    
    # Sheet 6: Average Utilization by Division
    util_div = merged.groupby('DIVISION')['UTILIZATION_PCT'].mean().reset_index()
    util_div.columns = ['DIVISION', 'Average of UTILIZATION_PCT']
    util_div.to_excel(writer, sheet_name='Avg Utilization by Division', index=False)
```

### 7. Verification

```python
xls = pd.ExcelFile('/path/to/output.xlsx')
print(f"Sheets: {xls.sheet_names}")

# Required sheets check
required = ['SourceData', 'Spending by Division', 'Spending by Department',
            'Variance by Department', 'Category Quarter Matrix', 'Avg Utilization by Division']
missing = [s for s in required if s not in xls.sheet_names]
assert not missing, f"Missing sheets: {missing}"

# Enrichment columns check
source = pd.read_excel(xls, sheet_name='SourceData')
required_cols = ['BUDGET_AMOUNT', 'VARIANCE', 'UTILIZATION_PCT']
missing_cols = [c for c in required_cols if c not in source.columns]
assert not missing_cols, f"Missing calculated columns: {missing_cols}"

# Sanity checks
print(f"Total expenses: ${source['amount'].sum():,.2f}")
print(f"Total budget: ${source['BUDGET_AMOUNT'].sum():,.2f}")
print(f"Net variance: ${source['VARIANCE'].sum():,.2f}")

# Variance sign convention check
under_budget = (source['VARIANCE'] < 0).sum()
over_budget = (source['VARIANCE'] > 0).sum()
print(f"Under budget records: {under_budget}, Over budget: {over_budget}")
```

## Common Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| Using `Read` tool on .xlsx budget files | Binary file rejection | Use `pd.read_excel()` |
| Joining expenses directly to budget without org hierarchy | Department names may not match (e.g., "Eng" vs "Engineering") | Join expenses→org→budget to normalize department names |
| Forgetting to melt wide budget format | Cannot match on fiscal_quarter | Use `pd.melt()` to transform Q1_BUDGET columns |
| Division by zero in utilization | Creates inf/-inf values | Check `BUDGET_AMOUNT != 0` before division |
| Integer division for variance | Precision loss in Python 2, still risky | Use float operands or `.astype(float)` |
| Positive variance = under budget | Confusing sign convention | Document: VARIANCE = actual - budget (negative = underspend) |
| Case-sensitive category joins | "Software" != "software" | Normalize: `str.strip().str.title()` before join |
| Default `index=True` in to_excel | Adds unwanted index column | Always `index=False` |
| Ignoring unmatched budget allocations | Silent data quality issues | Report count of unmatched expenses |

## Troubleshooting

**Budget allocations not matching expenses**
- Verify fiscal_quarter format matches: "Q1" vs "Quarter 1" vs "1"
- Check expense_category case sensitivity and whitespace
- Confirm department name mapping: org file may have abbreviations

**Utilization percentages > 100% or negative**
- Expected behavior for over-budget or credit transactions
- Check for zero or negative budget amounts
- Verify amount signs: credits/refunds should be negative

**Wide-to-long transformation fails**
- Ensure quarter columns follow consistent naming: `Q1_BUDGET`, `Q2_BUDGET`, etc.
- Check for merged cells or headers that confuse pandas
- Use `header=` parameter if budget data starts on non-first row

**Variance calculations inconsistent**
- Re-verify sign convention: amount - budget or budget - amount
- Check for missing BUDGET_AMOUNT values (NaN propagates)
- Review credit transactions (negative amounts) handling

**Verifier fails on sheet names or columns**
- Sheet names are case-sensitive and space-sensitive
- Common issues: "Avg" vs "Average", "by" vs "By"
- Verify exact column names in pivot tables: "Sum of amount" vs "amount"

## References

- `references/pdf-org-patterns.md` — Regex patterns for organizational hierarchy extraction
- `references/budget-transform-patterns.md` — Wide-to-long transformations and fiscal period handling

## Relationship to Other Skills

This skill specializes financial variance analysis and budget reconciliation. For event registration reporting with attendee data, use `event-registration-pivot`. For HR compensation analysis, use `hr-compensation-pivot`. For inventory/warehouse reports, use `excel-report-generation`. For general multi-source Excel reporting without financial metrics, use `excel-report-generation`.
