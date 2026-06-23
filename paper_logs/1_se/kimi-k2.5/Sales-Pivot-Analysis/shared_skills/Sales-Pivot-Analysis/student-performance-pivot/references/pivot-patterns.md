# Educational Pivot Table Patterns

## Common Educational Summaries

### Performance by Demographics

```python
# Average score by department
dept_avg = df.groupby('DEPARTMENT')['SCORE'].mean().round(2).reset_index()

# Pass rate by department
pass_rate = df.groupby('DEPARTMENT').apply(
    lambda x: (x['SCORE'] >= 70).mean() * 100
).round(2).reset_index(name='PASS_RATE_PCT')

# Distribution of grade bands
grade_dist = pd.crosstab(
    df['DEPARTMENT'], 
    df['GRADE_BAND'],
    normalize='index'
) * 100
```

### Temporal Patterns

```python
# Enrollment trends by semester
enrollment = df.groupby('SEMESTER')['STUDENT_ID'].nunique().reset_index()

# Average scores by term over time
term_trends = df.groupby('SEMESTER')['SCORE'].mean().reset_index()

# Course load distribution
course_load = df.groupby(['STUDENT_ID', 'SEMESTER'])['CREDITS'].sum().reset_index()
```

### Cross-Tabulation Matrices

```python
# Department × Semester performance matrix
dept_sem_matrix = df.pivot_table(
    values='SCORE',
    index='DEPARTMENT',
    columns='SEMESTER',
    aggfunc='mean'
).round(2)

# Grade distribution by department
grade_dept = pd.crosstab(
    df['DEPARTMENT'],
    df['GRADE_BAND'],
    margins=True
)

# Enrollment year × Current performance
year_perf = df.pivot_table(
    values='SCORE',
    index='ENROLLMENT_YEAR',
    columns='GRADE_BAND',
    aggfunc='count',
    fill_value=0
)
```

## Multi-Sheet Report Structure

Standard sheet order for academic reports:

1. **SourceData** — Full detail with all enriched columns
2. **Summary by Department** — Avg scores, counts, pass rates
3. **Summary by Semester** — Temporal trends, credit totals
4. **Cross-Tab Matrix** — Department × Semester or other dimensions
5. **Student-Level Summary** — One row per student with aggregates

## Export Formatting Notes

- Always use `index=False` in `to_excel()`
- Round averages to 2 decimal places for readability
- Sort categorical outputs logically (by year, alphabetically by dept name)
- Consider adding a "Notes" sheet with data definitions if report is shared