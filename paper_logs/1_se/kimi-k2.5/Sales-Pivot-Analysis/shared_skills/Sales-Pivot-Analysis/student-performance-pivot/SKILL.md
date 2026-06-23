---
name: student-performance-pivot
description: Generate multi-sheet Excel reports from student roster and grade data, with calculated columns (grade bands, weighted scores, retake flags) and pivot table summaries by department, semester, and cross-tabulated matrices. Use when tasks require joining student demographic data with course grades, computing academic metrics, or creating analytical views of enrollment patterns.
---

# Student Performance Pivot Report Generation

Create enriched Excel reports from student roster and grade data with automated calculations and multi-dimensional pivot summaries.

## When to Use

- Joining student roster data (PDF/Excel) with course grade records (Excel/CSV)
- Computing derived academic metrics (grade bands, weighted scores, pass/fail flags)
- Generating cross-tabular summaries by department, semester, or demographic dimensions
- Creating executive summaries with multiple analytical views of the same dataset

## Standard Workflow

### 1. Load Source Data

**Roster (PDF):** Use `Read` tool to extract text, then parse structured fields:
```python
# Extract from PDF text: STUDENT_ID, NAME, DEPARTMENT, ENROLLMENT_YEAR
import re
# Pattern depends on PDF format - look for consistent delimiters
```

**Grades (Excel):** Use pandas directly (do NOT use `Read` on binary .xlsx):
```python
import pandas as pd
grades = pd.read_excel('/path/to/grades.xlsx')
roster = pd.read_excel('/path/to/roster.xlsx')  # if Excel format
```

### 2. Data Quality Checks

Before joining, validate:

| Check | Method | Failure Action |
|-------|--------|----------------|
| Roster-grade ID match | `set(grades['STUDENT_ID']) - set(roster['STUDENT_ID'])` | Report unmatched IDs |
| Duplicate grade rows | `grades.duplicated().sum()` | Remove with `drop_duplicates()` |
| Whitespace in categoricals | `df['SEMESTER'].str.strip().str.title()` | Normalize case |
| Invalid score ranges | `grades[(grades['SCORE'] < 0) | (grades['SCORE'] > 100)]` | Flag or filter |

### 3. Create Enriched Calculated Columns

Standard academic calculations:

```python
def grade_band(score):
    if score >= 90: return 'A'
    elif score >= 80: return 'B'
    elif score >= 70: return 'C'
    elif score >= 60: return 'D'
    else: return 'F'

df['GRADE_BAND'] = df['SCORE'].apply(grade_band)
df['WEIGHTED_SCORE'] = df['SCORE'] * df['CREDITS']
df['RETAKE_FLAG'] = df['SCORE'].apply(lambda x: 'Yes' if x < 70 else 'No')
df['TERM_STATUS'] = df['SEMESTER'].apply(lambda x: 'summer' if 'Summer' in x else 'standard')
```

### 4. Join Datasets

```python
# Left join grades to roster (grades may have multiple rows per student)
merged = grades.merge(roster, on='STUDENT_ID', how='left')

# Verify join coverage
unmatched = merged[merged['DEPARTMENT'].isna()]['STUDENT_ID'].nunique()
print(f"Unmatched students: {unmatched}")
```

### 5. Generate Pivot Summary Sheets

```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    # Full detail with enriched columns
    merged.to_excel(writer, sheet_name='SourceData', index=False)
    
    # Avg Score by Department
    dept_avg = merged.groupby('DEPARTMENT')['SCORE'].mean().round(2).reset_index()
    dept_avg.to_excel(writer, sheet_name='Avg Score by Department', index=False)
    
    # Student counts by Department
    dept_counts = merged.groupby('DEPARTMENT')['STUDENT_ID'].nunique().reset_index()
    dept_counts.columns = ['DEPARTMENT', 'Count']
    dept_counts.to_excel(writer, sheet_name='Students by Department', index=False)
    
    # Credits by Semester
    sem_credits = merged.groupby('SEMESTER')['CREDITS'].sum().reset_index()
    sem_credits.to_excel(writer, sheet_name='Credits by Semester', index=False)
    
    # Cross-tab: Department × Semester
    matrix = merged.pivot_table(
        values='SCORE', 
        index='DEPARTMENT', 
        columns='SEMESTER', 
        aggfunc='mean'
    ).round(2).reset_index()
    matrix.to_excel(writer, sheet_name='Department Semester Matrix', index=False)
```

### 6. Verification

```python
xls = pd.ExcelFile('/path/to/output.xlsx')
print(f"Sheets: {xls.sheet_names}")
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)
    print(f"{sheet}: {df.shape[0]} rows, {df.shape[1]} columns")
    
# Verify enriched columns exist
source = pd.read_excel(xls, sheet_name='SourceData')
required = ['GRADE_BAND', 'WEIGHTED_SCORE', 'RETAKE_FLAG', 'TERM_STATUS']
missing = [c for c in required if c not in source.columns]
assert not missing, f"Missing columns: {missing}"
```

## Common Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| Using `Read` tool on .xlsx | Binary file rejection | Use `pd.read_excel()` via Python tool |
| `pd.pivot()` without aggregation | Only reshapes, doesn't summarize | Use `pivot_table()` with `aggfunc` |
| Integer division for averages | Silent precision loss in Python 2 | Ensure float division or use `.mean()` |
| Default `index=True` in `to_excel()` | Adds unwanted index column | Always specify `index=False` |
| Case-sensitive joins | "Spring 2024" != "spring 2024" | Normalize: `str.strip().str.title()` |

## Troubleshooting

**"No module named 'openpyxl'"**
```bash
pip install openpyxl
```

**PDF parsing yields garbled roster data**
- Try `pdfplumber` for table extraction if `Read` tool output is unstructured
- Use regex patterns on extracted text as fallback

**Memory error on large datasets**
- Use `read_excel(..., usecols=['COL1', 'COL2'])` to load only needed columns
- Process in chunks if >100k records

**Grade bands showing as floats (90.0 instead of A)**
- Ensure `grade_band()` returns strings, check for NaN inputs

## References

- `references/academic-calculations.md` — Grade band logic, weighted formulas, and academic metric patterns
- `references/pivot-patterns.md` — Common educational pivot table configurations