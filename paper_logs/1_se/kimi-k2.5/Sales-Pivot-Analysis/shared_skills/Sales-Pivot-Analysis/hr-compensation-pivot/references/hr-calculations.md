# HR Calculations Reference

## Core Compensation Metrics

### Total Compensation
```python
# Standard total comp
df['TOTAL_COMP'] = df['base_salary'] + df['annual_bonus']

# Extended with equity (if available)
df['TOTAL_COMP'] = df['base_salary'] + df['annual_bonus'] + df.get('equity_value', 0)

# Monthly equivalent
df['MONTHLY_COMP'] = df['TOTAL_COMP'] / 12
```

### Experience Band Variants

**Standard 4-tier:**
```python
def experience_band(years):
    if years < 3: return 'Junior'
    elif years < 8: return 'Mid'
    elif years < 15: return 'Senior'
    else: return 'Veteran'
```

**Tech industry variant:**
```python
def experience_band_tech(years):
    if years < 2: return 'Entry'
    elif years < 5: return 'Mid'
    elif years < 10: return 'Senior'
    else: return 'Staff/Principal'
```

**Tenure-based (for academic/govt):**
```python
def experience_band_tenure(years):
    if years < 1: return 'Probationary'
    elif years < 5: return 'Early Career'
    elif years < 15: return 'Established'
    else: return 'Veteran'
```

### Compensation Ratios

```python
# Individual vs department budget
df['COMP_TO_DEPT_BUDGET'] = df['TOTAL_COMP'] / df['ANNUAL_BUDGET']

# Individual vs department average (pay equity analysis)
dept_avg = df.groupby('DEPT_NAME')['TOTAL_COMP'].transform('mean')
df['COMP_TO_DEPT_AVG'] = df['TOTAL_COMP'] / dept_avg

# Percentile within department
df['DEPT_PERCENTILE'] = df.groupby('DEPT_NAME')['TOTAL_COMP'].rank(pct=True)
```

### Cost Metrics

```python
# Department total cost
dept_cost = df.groupby('DEPT_NAME').agg({
    'TOTAL_COMP': 'sum',
    'base_salary': 'sum',
    'annual_bonus': 'sum'
}).round(2)

# Cost per employee
dept_cost['COST_PER_EMP'] = dept_cost['TOTAL_COMP'] / df.groupby('DEPT_NAME').size()

# Budget utilization
dept_cost['BUDGET_UTIL_PCT'] = (dept_cost['TOTAL_COMP'] / 
    dept_df.set_index('DEPT_NAME')['ANNUAL_BUDGET'] * 100).round(2)
```

## Workforce Distribution Metrics

```python
# Headcount by multiple dimensions
hc_by_dept_loc = df.groupby(['DEPT_NAME', 'LOCATION']).size().unstack(fill_value=0)

# Experience distribution
exp_dist = df['EXPERIENCE_BAND'].value_counts(normalize=True) * 100

# Salary distribution statistics
salary_stats = df.groupby('DEPT_NAME')['base_salary'].agg(['count', 'mean', 'median', 'std']).round(2)

# Pay equity by dimension
gender_pay_gap = df.groupby(['DEPT_NAME', 'gender'])['TOTAL_COMP'].mean().unstack()
gender_pay_gap['GAP_PCT'] = ((gender_pay_gap['Male'] - gender_pay_gap['Female']) / 
                             gender_pay_gap['Female'] * 100).round(2)
```

## Temporal Calculations

```python
# Years of service from hire date
df['years_of_service'] = (pd.Timestamp.now() - pd.to_datetime(df['hire_date'])).dt.days / 365.25

# Generation from hire year
def generation(hire_year):
    if hire_year < 1996: return 'Boomer'
    elif hire_year < 1981: return 'Gen X'
    elif hire_year < 1997: return 'Millennial'
    else: return 'Gen Z'

df['GENERATION'] = df['hire_year'].apply(generation)
```
