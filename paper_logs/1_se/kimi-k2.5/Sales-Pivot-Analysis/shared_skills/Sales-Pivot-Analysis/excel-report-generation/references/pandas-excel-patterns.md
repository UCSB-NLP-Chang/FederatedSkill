# Pandas Excel Patterns

## Reading Excel Files

```python
import pandas as pd

# Single sheet (default: first sheet)
df = pd.read_excel('file.xlsx')

# Specific sheet
df = pd.read_excel('file.xlsx', sheet_name='Sheet1')

# All sheets to dict
dfs = pd.read_excel('file.xlsx', sheet_name=None)  # dict of sheet_name: DataFrame

# Specific columns only
df = pd.read_excel('file.xlsx', usecols=['A', 'B', 'C'])

# Skip rows
df = pd.read_excel('file.xlsx', skiprows=2)
```

## Writing Multi-Sheet Excel

```python
with pd.ExcelWriter('output.xlsx', engine='openpyxl') as writer:
    df1.to_excel(writer, sheet_name='Sheet1', index=False)
    df2.to_excel(writer, sheet_name='Sheet2', index=False)
    
    # Access workbook for formatting (optional)
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
```

## Common Aggregations for Pivot Tables

```python
# Simple groupby
df.groupby('CATEGORY')['REVENUE'].sum()

# Multiple aggregations
df.groupby('CATEGORY').agg({
    'REVENUE': 'sum',
    'QUANTITY': 'sum',
    'TRANSACTION_ID': 'count'  # transaction count
}).rename(columns={'TRANSACTION_ID': 'TRANSACTION_COUNT'})

# Pivot table (cross-tab)
pd.pivot_table(df, values='REVENUE', index='CATEGORY', 
               columns='REGION', aggfunc='sum', fill_value=0)
```

## Data Cleaning Snippets

```python
# Strip whitespace and normalize case
df['REGION'] = df['REGION'].str.strip().str.title()

# Remove rows with invalid quantities
df = df[df['QUANTITY'] > 0]

# Check for unmatched IDs after join
unmatched = df[df['CATEGORY'].isna()]['PRODUCT_ID'].unique()

# Handle division by zero for margins
df['MARGIN_PCT'] = df['PROFIT'] / df['REVENUE'].replace(0, float('nan'))
```