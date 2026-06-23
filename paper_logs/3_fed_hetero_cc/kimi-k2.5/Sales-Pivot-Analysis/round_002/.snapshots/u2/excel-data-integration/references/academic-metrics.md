# Academic Metrics Reference

Domain-specific formulas for student performance reports.

## Input Schema

**Excel grades:**
- STUDENT_ID (join key)
- SCORE (numeric, 0-100)
- CREDITS (numeric, positive)
- SEMESTER (categorical)
- DEPARTMENT (categorical)

**PDF roster:**
- STUDENT_ID (join key)
- STUDENT_NAME (string)
- PROGRAM (categorical)

## Derived Columns

```python
# GRADE_BAND: Letter grade based on 10-point scale
def assign_grade_band(score):
    if score >= 90: return 'A'
    elif score >= 80: return 'B'
    elif score >= 70: return 'C'
    elif score >= 60: return 'D'
    else: return 'F'

merged['GRADE_BAND'] = merged['SCORE'].apply(assign_grade_band)

# WEIGHTED_SCORE: Score weighted by course credits
merged['WEIGHTED_SCORE'] = merged['SCORE'] * merged['CREDITS']

# RETAKE_FLAG: Flag for scores below passing threshold
merged['RETAKE_FLAG'] = merged['SCORE'].apply(lambda x: 'Yes' if x < 70 else 'No')

# TERM_STATUS: Detect special terms (e.g., summer sessions)
merged['TERM_STATUS'] = merged['SEMESTER'].apply(
    lambda x: 'special' if 'Summer' in str(x) else 'standard'
)
```

## Pivot Tables

1. **Avg Score by Department** — mean of SCORE grouped by DEPARTMENT
2. **Students by Department** — count of records grouped by DEPARTMENT
3. **Credits by Semester** — sum of CREDITS grouped by SEMESTER
4. **Dept-Semester Matrix** — mean of SCORE, rows=DEPARTMENT, columns=SEMESTER

```python
pivot_avg = merged.pivot_table(index='DEPARTMENT', values='SCORE', aggfunc='mean').reset_index()
pivot_count = merged.pivot_table(index='DEPARTMENT', values='STUDENT_ID', aggfunc='count').reset_index()
pivot_credits = merged.pivot_table(index='SEMESTER', values='CREDITS', aggfunc='sum').reset_index()
pivot_matrix = merged.pivot_table(index='DEPARTMENT', columns='SEMESTER', values='SCORE', aggfunc='mean').reset_index()
```

## Sheet Names (typical)

- "Avg Score by Department"
- "Students by Department"
- "Credits by Semester"
- "Department Semester Matrix"
- "SourceData"

**Always use exact names from task specification.**

## Validation Checks

- GRADE_BAND distribution sums to total row count
- No null DEPARTMENT values after merge (indicates join failure)
- All scores in valid range (0-100)
