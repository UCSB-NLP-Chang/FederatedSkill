# Academic Calculations Reference

## Grade Band Assignment

Standard 10-point scale with optional customization:

```python
def grade_band(score, scale='standard'):
    """
    Convert numeric score to letter grade.
    
    scale: 'standard' | 'plus_minus' | 'custom_dict'
    """
    if pd.isna(score):
        return None
        
    if scale == 'standard':
        if score >= 90: return 'A'
        elif score >= 80: return 'B'
        elif score >= 70: return 'C'
        elif score >= 60: return 'D'
        else: return 'F'
    
    elif scale == 'plus_minus':
        if score >= 97: return 'A+'
        elif score >= 93: return 'A'
        elif score >= 90: return 'A-'
        elif score >= 87: return 'B+'
        elif score >= 83: return 'B'
        elif score >= 80: return 'B-'
        elif score >= 77: return 'C+'
        elif score >= 73: return 'C'
        elif score >= 70: return 'C-'
        elif score >= 67: return 'D+'
        elif score >= 63: return 'D'
        elif score >= 60: return 'D-'
        else: return 'F'

# Vectorized version for pandas
def grade_band_vectorized(series, scale='standard'):
    """Apply grade band to entire Series efficiently."""
    if scale == 'standard':
        return pd.cut(series, 
                     bins=[-float('inf'), 60, 70, 80, 90, 100],
                     labels=['F', 'D', 'C', 'B', 'A'],
                     right=False)
```

## Weighted Score Calculations

```python
# Point-weighted by credits
df['WEIGHTED_SCORE'] = df['SCORE'] * df['CREDITS']

# Grade Point Average (4.0 scale)
grade_points = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}
df['GRADE_POINTS'] = df['GRADE_BAND'].map(grade_points)
df['WEIGHTED_POINTS'] = df['GRADE_POINTS'] * df['CREDITS']

# Calculate GPA per student
gpa = df.groupby('STUDENT_ID').apply(
    lambda x: x['WEIGHTED_POINTS'].sum() / x['CREDITS'].sum()
).round(2)
```

## Retake/Remediation Flags

```python
# Simple threshold
df['RETAKE_FLAG'] = (df['SCORE'] < 70).map({True: 'Yes', False: 'No'})

# Multiple conditions
df['REMEDIATION_STATUS'] = df['SCORE'].apply(
    lambda x: 'Required' if x < 60 
    else 'Recommended' if x < 70 
    else 'Satisfactory'
)

# Prior attempt tracking (if multiple rows per course)
df['ATTEMPT_NUMBER'] = df.groupby(['STUDENT_ID', 'COURSE_NAME']).cumcount() + 1
df['IS_RETAKE'] = df['ATTEMPT_NUMBER'] > 1
```

## Term Classification

```python
def classify_term(semester_str):
    """Classify semester into term types."""
    s = semester_str.lower()
    if 'summer' in s:
        return 'summer'
    elif 'winter' in s or 'jterm' in s or 'january' in s:
        return 'winter'
    else:
        return 'standard'  # fall/spring

# Extract year for grouping
df['YEAR'] = df['SEMESTER'].str.extract(r'(\d{4})').astype(int)
```