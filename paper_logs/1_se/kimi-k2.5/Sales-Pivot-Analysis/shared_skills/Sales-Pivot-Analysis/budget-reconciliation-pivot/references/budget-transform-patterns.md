# Budget Data Transformation Patterns

## Wide-to-Long Transformation

Budget files commonly store quarterly allocations as separate columns. Convert to analysis-friendly long format:

### Standard Quarterly Pattern

```python
import pandas as pd

# Input: DEPT_NAME, category, Q1_BUDGET, Q2_BUDGET, Q3_BUDGET, Q4_BUDGET
quarter_cols = ['Q1_BUDGET', 'Q2_BUDGET', 'Q3_BUDGET', 'Q4_BUDGET']
id_vars = [c for c in budget.columns if c not in quarter_cols]

# Melt to long format
budget_long = budget.melt(
    id_vars=id_vars,
    value_vars=quarter_cols,
    var_name='budget_quarter_col',
    value_name='BUDGET_AMOUNT'
)

# Extract clean quarter designation
budget_long['fiscal_quarter'] = budget_long['budget_quarter_col'].str.extract(r'(Q\d)')

# Remove rows with no budget allocation
budget_long = budget_long[budget_long['BUDGET_AMOUNT'].notna()]
budget_long = budget_long[budget_long['BUDGET_AMOUNT'] != 0]  # Optional
```

### Flexible Quarter Detection

When column names vary:

```python
# Auto-detect quarter columns
quarter_pattern = r'(Q\d).*(?:BUDGET|ALLOCATION|AMOUNT)'
quarter_cols = [c for c in budget.columns if re.search(quarter_pattern, c, re.I)]

# Or detect any Q-prefixed columns
quarter_cols = [c for c in budget.columns if re.match(r'Q\d', c)]
```

## Fiscal Period Handling

### Quarter from Date Columns

```python
# Extract quarter from date fields
budget['fiscal_quarter'] = pd.to_datetime(budget['date']).dt.quarter.apply(lambda x: f'Q{x}')

# Or from month number
month_to_quarter = {1: 'Q1', 2: 'Q1', 3: 'Q1',
                    4: 'Q2', 5: 'Q2', 6: 'Q2',
                    7: 'Q3', 8: 'Q3', 9: 'Q3',
                    10: 'Q4', 11: 'Q4', 12: 'Q4'}
budget['fiscal_quarter'] = budget['month'].map(month_to_quarter)
```

### Fiscal Year Offset

When fiscal year doesn't match calendar year:

```python
# Fiscal year starts in April (Q1 = Apr-Jun)
def fiscal_quarter(date):
    month = date.month
    if month in [4, 5, 6]: return 'Q1'
    elif month in [7, 8, 9]: return 'Q2'
    elif month in [10, 11, 12]: return 'Q3'
    else: return 'Q4'

def fiscal_year(date):
    year = date.year
    if date.month < 4:  # Jan-Mar belongs to previous fiscal year
        return year - 1
    return year
```

## Variance and Utilization Calculations

### Variance Formulas

```python
# Standard: actual - budget (negative = under budget)
df['VARIANCE'] = df['amount'] - df['BUDGET_AMOUNT']

# Alternative: budget - actual (positive = under budget)
# df['VARIANCE'] = df['BUDGET_AMOUNT'] - df['amount']

# Variance percentage
df['VARIANCE_PCT'] = (df['VARIANCE'] / df['BUDGET_AMOUNT'].replace(0, float('nan'))) * 100
```

### Utilization Rate

```python
# Basic calculation
def safe_utilization(amount, budget):
    if pd.isna(budget) or budget == 0:
        return float('nan')
    return amount / budget

df['UTILIZATION_PCT'] = df.apply(
    lambda r: safe_utilization(r['amount'], r['BUDGET_AMOUNT']),
    axis=1
)

# Capped at 100% variant (for compliance reporting)
df['UTILIZATION_PCT_CAPPED'] = df['UTILIZATION_PCT'].clip(upper=1.0)
```

## Data Quality Checks

```python
def validate_budget_data(df):
    """Run standard budget data quality checks."""
    issues = []
    
    # Negative amounts (credits/refunds are valid but flag for review)
    neg_amounts = df[df['amount'] < 0]
    if len(neg_amounts) > 0:
        issues.append(f"Negative amounts (credits): {len(neg_amounts)} records")
    
    # Zero budget with non-zero spend
    zero_budget_spend = df[(df['BUDGET_AMOUNT'] == 0) & (df['amount'] != 0)]
    if len(zero_budget_spend) > 0:
        issues.append(f"Zero budget with spending: {len(zero_budget_spend)} records")
    
    # Missing budget allocations
    missing_budget = df['BUDGET_AMOUNT'].isna().sum()
    if missing_budget > 0:
        issues.append(f"Missing budget allocations: {missing_budget} records")
    
    # Extreme utilization (>500% or negative)
    extreme_util = df[(df['UTILIZATION_PCT'] > 5) | (df['UTILIZATION_PCT'] < 0)]
    if len(extreme_util) > 0:
        issues.append(f"Extreme utilization rates: {len(extreme_util)} records")
    
    return issues
```
