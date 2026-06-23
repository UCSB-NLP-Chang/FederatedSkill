---
name: hr-compensation-pivot
description: Generate multi-sheet Excel reports from employee compensation data joined with department/organizational catalogs. Calculates derived fields like total compensation, experience bands, compensation ratios, and produces standard HR analytics by department, location, job level, and cross-tabulated matrices. Use when tasks require combining employee records with department metadata, computing compensation metrics, or analyzing workforce distribution patterns.
---

# HR Compensation Pivot Report Generation

Create enriched compensation reports by joining employee records with department catalogs, computing workforce metrics, and generating multi-dimensional HR analytics.

## When to Use

- Employee compensation records (CSV/Excel) need joining with department/org structure data (often from PDF/Excel catalogs)
- Analysis requires derived metrics: total compensation, experience bands, comp-to-budget ratios
- Output needs standard HR analytics: headcount by location, avg salary by department, total comp by job title, cross-tabulations
- Data sources mix employee transactions with organizational hierarchy catalogs

## Standard Workflow

### 1. Parse Department Catalog (PDF or Excel)

**PDF catalogs:** Extract text then parse structured fields:
```python
import re
# Look for patterns like: DEPT_CODE, DEPT_NAME, LOCATION, BUDGET
# Common formats: fixed-width, labeled rows, or delimited

# Example extraction
pattern = r'(D\d{2})\s+([\w\s]+?)\s+([A-Za-z\s]+?)\s+([\d,]+)'
matches = re.findall(pattern, pdf_text)
dept_df = pd.DataFrame(matches, columns=['DEPT_CODE', 'DEPT_NAME', 'LOCATION', 'ANNUAL_BUDGET'])
dept_df['ANNUAL_BUDGET'] = dept_df['ANNUAL_BUDGET'].str.replace(',', '').astype(float)
```

**Excel catalogs:** Direct pandas read:
```python
dept_df = pd.read_excel('/path/to/departments.xlsx')
# Expected: DEPT_CODE/DEPT_ID, DEPT_NAME, LOCATION, ANNUAL_BUDGET, etc.
```

### 2. Load Employee Records
```python
emp_df = pd.read_csv('/path/to/employee_compensation.csv')
# Expected: emp_id, full_name, department_code, job_title, base_salary, 
#           annual_bonus, years_of_service, hire_year
```

### 3. Data Quality Checks

| Check | Method | Failure Action |
|-------|--------|----------------|
| Department code match | `set(emp['department_code']) - set(dept['DEPT_CODE'])` | Report unmatched, filter or map |
| Negative/zero salaries | `emp[emp['base_salary'] <= 0]` | Flag data quality issue |
| Missing bonus values | `emp['annual_bonus'].isna().sum()` | Fill with 0 or flag |
| Duplicate employee IDs | `emp['emp_id'].duplicated().sum()` | Remove duplicates |

### 4. Create Calculated Columns

**Core compensation metrics:**
```python
# Total compensation
df['TOTAL_COMP'] = df['base_salary'] + df['annual_bonus']

# Experience bands (adjust thresholds to org norms)
def experience_band(years):
    if years < 3: return 'Junior'
    elif years < 8: return 'Mid'
    elif years < 15: return 'Senior'
    else: return 'Veteran'

df['EXPERIENCE_BAND'] = df['years_of_service'].apply(experience_band)

# Compensation ratio (requires department budget from join)
df['COMP_RATIO'] = df['TOTAL_COMP'] / df['ANNUAL_BUDGET']
```

### 5. Join Datasets
```python
# Left join: employees enriched with department data
merged = emp_df.merge(dept_df, left_on='department_code', right_on='DEPT_CODE', how='left')

# Verify join coverage
unmatched = merged[merged['DEPT_NAME'].isna()]['department_code'].nunique()
print(f"Unmatched department codes: {unmatched}")
```

### 6. Generate Pivot Summary Sheets
```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    # Full detail with enriched data
    merged.to_excel(writer, sheet_name='SourceData', index=False)
    
    # Avg Salary by Department
    dept_avg = merged.groupby('DEPT_NAME')['base_salary'].mean().round(2).reset_index()
    dept_avg.to_excel(writer, sheet_name='Avg Salary by Department', index=False)
    
    # Headcount by Location
    loc_count = merged.groupby('LOCATION').size().reset_index(name='Employee Count')
    loc_count.to_excel(writer, sheet_name='Headcount by Location', index=False)
    
    # Total Compensation by Job Title
    title_comp = merged.groupby('job_title')['TOTAL_COMP'].sum().reset_index()
    title_comp.to_excel(writer, sheet_name='Total Compensation by Title', index=False)
    
    # Cross-tab: Department × Job Title (average salary)
    matrix = merged.pivot_table(
        values='base_salary',
        index='DEPT_NAME',
        columns='job_title',
        aggfunc='mean'
    ).round(2).reset_index()
    matrix.to_excel(writer, sheet_name='Department Location Matrix', index=False)
```

### 7. Verification
```python
xls = pd.ExcelFile('/path/to/output.xlsx')
print(f"Sheets: {xls.sheet_names}")

# Verify expected sheets exist
expected = ['SourceData', 'Avg Salary by Department', 'Headcount by Location',
            'Total Compensation by Title', 'Department Location Matrix']
missing = [s for s in expected if s not in xls.sheet_names]
assert not missing, f"Missing sheets: {missing}"

# Verify calculated columns
source = pd.read_excel(xls, sheet_name='SourceData')
required = ['TOTAL_COMP', 'EXPERIENCE_BAND', 'COMP_RATIO']
missing_cols = [c for c in required if c not in source.columns]
assert not missing_cols, f"Missing calculated columns: {missing_cols}"

# Spot-check calculations
assert (source['TOTAL_COMP'] == source['base_salary'] + source['annual_bonus']).all()
```

## Common Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| Hardcoding department metadata | Brittle, doesn't scale | Join with catalog from source |
| Integer division for COMP_RATIO | Silent precision loss | Ensure float division |
| Assuming all dept codes match | Silent data loss | Verify unmatched count post-join |
| Missing bonus as NaN | Creates NaN TOTAL_COMP | Fill missing bonuses with 0 before calc |
| Experience bands as numeric | Loses semantic meaning | Use categorical strings (Junior/Mid/Senior/Veteran) |

## Troubleshooting

**PDF catalog parsing fails**
- Try `pdfplumber` for table extraction if text is garbled
- Use flexible regex with optional whitespace: `r'\s+'`
- Check for multi-column layouts that confuse line extraction

**COMP_RATIO shows inf or extreme values**
- Check for zero or missing ANNUAL_BUDGET values
- Verify budget numbers aren't in thousands (e.g., 3500 vs 3500000)

**Experience band distribution unexpected**
- Adjust thresholds to match org norms (e.g., 2/5/10 vs 3/8/15)
- Check for data entry errors in years_of_service

**Verifier fails on sheet names**
- Sheet names are case-sensitive and space-sensitive
- Common issue: "Avg" vs "Average", "Headcount" vs "Head Count"

## References

- `references/hr-calculations.md` — Detailed compensation formulas, experience band variants, and workforce metrics
- `references/pdf-org-patterns.md` — Regex patterns for common HRIS/PDF department exports