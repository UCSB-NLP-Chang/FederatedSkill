# Quality Control Patterns Reference

## Core Deviation Calculations

### Dimensional Deviation

```python
# Absolute deviation from tolerance (NaN-safe)
def calculate_deviation(measurement, tolerance):
    """Calculate absolute deviation, preserving NaN."""
    import pandas as pd
    if pd.isna(measurement) or pd.isna(tolerance):
        return float('nan')
    return abs(measurement - tolerance)

# Vectorized with pandas
df['DEVIATION_MM'] = (df['MEASUREMENT_MM'] - df['TOLERANCE_MM']).abs()
# NaN propagates automatically: NaN - X = NaN, abs(NaN) = NaN
```

### Weight Error (Relative)

```python
# Absolute relative error
def weight_error(actual, target):
    import pandas as pd
    if pd.isna(actual) or pd.isna(target) or target == 0:
        return float('nan')
    return abs(actual - target) / target

df['WEIGHT_ERROR'] = df.apply(
    lambda row: weight_error(row['ACTUAL_WEIGHT'], row['TARGET_WEIGHT']),
    axis=1
)
```

## Quality Grade Assignment

### Tiered Grading by Deviation

```python
def assign_grade(deviation, grade_a_max=0.5, grade_b_max=1.0):
    """
    Assign quality grade based on deviation thresholds.
    
    Thresholds:
        A: deviation < grade_a_max
        B: grade_a_max <= deviation < grade_b_max  
        C: deviation >= grade_b_max
        N/A: missing deviation
    """
    import pandas as pd
    if pd.isna(deviation):
        return "N/A"
    elif deviation < grade_a_max:
        return "A"
    elif deviation < grade_b_max:
        return "B"
    else:
        return "C"

# Apply to DataFrame
df['QUALITY_GRADE'] = df['DEVIATION_MM'].apply(
    lambda x: assign_grade(x, grade_a_max=0.5, grade_b_max=1.0)
)
```

### Grade Distribution Validation

```python
def validate_grade_distribution(df, grade_col='QUALITY_GRADE'):
    """Check for expected grade distribution and missing value handling."""
    counts = df[grade_col].value_counts(dropna=False)
    print("Grade distribution:")
    print(counts)
    
    # Check if NaN values got proper "N/A" grade
    na_deviation = df['DEVIATION_MM'].isna().sum()
    na_grade = (df[grade_col] == "N/A").sum()
    
    if na_deviation != na_grade:
        print(f"WARNING: {na_deviation} NaN deviations but {na_grade} N/A grades")
    
    return counts
```

## Manufacturing Report Structure

### Standard 5-Sheet Layout

| Sheet | Content | Key Columns |
|-------|---------|-------------|
| **SourceData** | Full inspection records joined with specs | INSPECTION_ID, PART_ID, LINE, SHIFT, MEASUREMENT_MM, TOLERANCE_MM, DEVIATION_MM, WEIGHT_ERROR, QUALITY_GRADE |
| **Fail Rate by Line** | Count of inspections per production line | LINE, Count |
| **Avg Deviation by Line** | Mean deviation per line | LINE, Average of DEVIATION_MM |
| **Inspections by Shift** | Count by shift | SHIFT, Count |
| **Line Shift Matrix** | Cross-tab of inspections by line × shift | LINE, Morning, Afternoon, Night |

### Generation Pattern

```python
with pd.ExcelWriter('quality_report.xlsx', engine='openpyxl') as writer:
    # Sheet 1: Source data with all calculations
    df.to_excel(writer, sheet_name='SourceData', index=False)
    
    # Sheet 2: Count by line
    df.groupby('LINE').size().reset_index(name='Count').to_excel(
        writer, sheet_name='Fail Rate by Line', index=False)
    
    # Sheet 3: Average deviation by line
    df.groupby('LINE')['DEVIATION_MM'].mean().reset_index(
        name='Average of DEVIATION_MM').to_excel(
        writer, sheet_name='Avg Deviation by Line', index=False)
    
    # Sheet 4: Count by shift
    df.groupby('SHIFT').size().reset_index(name='Count').to_excel(
        writer, sheet_name='Inspections by Shift', index=False)
    
    # Sheet 5: Line × Shift matrix
    df.pivot_table(
        values='INSPECTION_ID',
        index='LINE',
        columns='SHIFT',
        aggfunc='count',
        fill_value=0
    ).reset_index().to_excel(writer, sheet_name='Line Shift Matrix', index=False)
```

## Data Quality Checks for Inspections

```python
def validate_inspection_data(df):
    """Run standard QC data quality checks."""
    import pandas as pd
    issues = []
    
    # Missing critical measurements
    missing_meas = df['MEASUREMENT_MM'].isna().sum()
    if missing_meas > 0:
        issues.append(f"Missing MEASUREMENT_MM: {missing_meas} rows")
    
    # Missing weights
    missing_weight = df['ACTUAL_WEIGHT'].isna().sum()
    if missing_weight > 0:
        issues.append(f"Missing ACTUAL_WEIGHT: {missing_weight} rows")
    
    # Verify NaN deviations match NaN measurements
    nan_deviation = df['DEVIATION_MM'].isna().sum()
    if nan_deviation != missing_meas:
        issues.append(f"NaN deviation count ({nan_deviation}) != NaN measurement count ({missing_meas})")
    
    # Check for negative deviations (calculation error)
    neg_dev = (df['DEVIATION_MM'] < 0).sum()
    if neg_dev > 0:
        issues.append(f"Negative deviations (abs() error): {neg_dev}")
    
    # Verify grade coverage
    expected_grades = {'A', 'B', 'C', 'N/A'}
    actual_grades = set(df['QUALITY_GRADE'].dropna().unique())
    unexpected = actual_grades - expected_grades
    if unexpected:
        issues.append(f"Unexpected grade values: {unexpected}")
    
    return issues
```

## N/A String vs NaN Handling

**Critical:** Pandas interprets the string "N/A" as NaN when reading Excel.

```python
import pandas as pd
from openpyxl import load_workbook

# Writing "N/A" strings
df['GRADE'] = df['DEVIATION'].apply(lambda x: "N/A" if pd.isna(x) else "A")
df.to_excel('output.xlsx', index=False)

# Reading back - "N/A" becomes NaN!
df_read = pd.read_excel('output.xlsx')
print((df_read['GRADE'] == "N/A").sum())  # 0 - all NaN!
print(df_read['GRADE'].isna().sum())       # N - includes original N/As

# To verify actual Excel contents, use openpyxl:
wb = load_workbook('output.xlsx')
ws = wb['Sheet1']
grade_col = 14  # column index for QUALITY_GRADE
na_count = sum(1 for row in ws.iter_rows(min_row=2, values_only=True) 
               if row[grade_col-1] == "N/A")
print(f"Actual 'N/A' strings in Excel: {na_count}")
```

### Verification Pattern for Test Suites

```python
def verify_grade_na_handling(excel_path):
    """Verify N/A grades are correctly stored, not just NaN."""
    from openpyxl import load_workbook
    import pandas as pd
    
    # Check with pandas (will show NaN for both missing and "N/A")
    df = pd.read_excel(excel_path, sheet_name='SourceData')
    pandas_na = df['QUALITY_GRADE'].isna().sum()
    
    # Check actual Excel values with openpyxl
    wb = load_workbook(excel_path)
    ws = wb['SourceData']
    headers = [cell.value for cell in next(ws.iter_rows(max_row=1))]
    grade_idx = headers.index('QUALITY_GRADE')
    
    excel_na_string = 0
    excel_true_na = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        val = row[grade_idx]
        if val == "N/A":
            excel_na_string += 1
        elif val is None or (isinstance(val, float) and pd.isna(val)):
            excel_true_na += 1
    
    return {
        'pandas_interpreted_na': pandas_na,
        'excel_na_strings': excel_na_string,
        'excel_true_missing': excel_true_na
    }
```
