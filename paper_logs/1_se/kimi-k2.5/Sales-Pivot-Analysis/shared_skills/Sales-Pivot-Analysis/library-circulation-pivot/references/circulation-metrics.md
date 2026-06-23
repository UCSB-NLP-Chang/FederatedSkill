# Circulation Metrics Reference

## Core Loan Metrics

### Loan Duration
```python
# Basic duration in days
df['LOAN_DURATION'] = (df['RETURN_DATE'] - df['LOAN_DATE']).dt.days

# Duration categories
def duration_category(days):
    if days <= 7: return 'short'
    elif days <= 14: return 'standard'
    elif days <= 30: return 'extended'
    else: return 'long-term'

df['DURATION_CATEGORY'] = df['LOAN_DURATION'].apply(duration_category)
```

### Temporal Enrichment

```python
# Publication decade
df['DECADE'] = (df['YEAR_PUBLISHED'] // 10 * 10).astype(str) + 's'

# Loan weekday/weekend classification
df['WEEKDAY_BUCKET'] = np.where(
    df['LOAN_DATE'].dt.weekday < 5, 'weekday', 'weekend'
)

# Season/month groupings
df['LOAN_MONTH'] = df['LOAN_DATE'].dt.month
def season(month):
    if month in [12, 1, 2]: return 'winter'
    elif month in [3, 4, 5]: return 'spring'
    elif month in [6, 7, 8]: return 'summer'
    else: return 'fall'
df['SEASON'] = df['LOAN_MONTH'].apply(season)
```

### Collection Analytics

```python
# Turnover rate (loans per item)
turnover = df.groupby('BOOK_ID').size() / df.groupby('BOOK_ID')['YEAR_PUBLISHED'].nunique()

# Genre popularity over time
genre_trends = df.groupby(['DECADE', 'GENRE']).size().unstack(fill_value=0)

# Borrower type distribution by material type
borrower_material = pd.crosstab(df['BORROWER_TYPE'], df['GENRE'], normalize='index') * 100
```

## Advanced Metrics

### Renewal Analysis
If renewal data available:
```python
# Loan with renewals
df['TOTAL_DAYS'] = df['LOAN_DURATION'] + df.get('RENEWAL_DAYS', 0)
df['RENEWAL_COUNT'] = df.get('RENEWAL_COUNT', 0)
```

### Overdue Detection
```python
due_date = df['LOAN_DATE'] + pd.Timedelta(days=df.get('LOAN_PERIOD_DAYS', 14))
df['DAYS_OVERDUE'] = (df['RETURN_DATE'] - due_date).dt.days.clip(lower=0)
df['WAS_OVERDUE'] = df['DAYS_OVERDUE'] > 0
```
