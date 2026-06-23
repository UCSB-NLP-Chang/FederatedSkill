# PDF Org Hierarchy Parsing Patterns

## Common HRIS/Finance System Export Formats

### Format A: Fixed-Width Columns
```
T101  Frontend Team      Engineering    Technology
T102  Backend Team       Engineering    Technology
T103  DevOps Team        Engineering    Technology
```

```python
lines = [l for l in pdf_text.split('\n') if l.strip() and l.startswith('T')]
data = []
for line in lines:
    team_code = line[0:4].strip()
    team_name = line[5:25].strip()
    dept_name = line[26:42].strip()
    division = line[43:].strip()
    data.append([team_code, team_name, dept_name, division])
```

### Format B: Delimited (Tab/Comma/Pipe)
```
T101,Frontend Team,Engineering,Technology
T102,Backend Team,Engineering,Technology
```

```python
import re
lines = [l for l in pdf_text.split('\n') if l.strip() and l.startswith('T')]
data = []
for line in lines:
    parts = re.split(r'[,\t|]', line)
    if len(parts) >= 4:
        data.append([p.strip() for p in parts[:4]])
```

### Format C: Labeled Fields
```
Team: T101
Name: Frontend Team
Department: Engineering
Division: Technology
```

```python
import re
records = re.split(r'Team:\s*', pdf_text)[1:]
data = []
for rec in records:
    team_code = re.search(r'^(T\d+)', rec).group(1)
    name = re.search(r'Name:\s*(.+?)(?:\n|Department:)', rec, re.DOTALL)
    dept = re.search(r'Department:\s*([\w\s]+?)(?:\n|Division:)', rec)
    div = re.search(r'Division:\s*([\w\s]+)', rec)
    data.append([
        team_code,
        name.group(1).strip() if name else None,
        dept.group(1).strip() if dept else None,
        div.group(1).strip() if div else None
    ])
```

## Name Normalization

```python
# Standardize department abbreviations
dept_map = {
    'eng': 'Engineering',
    'fin': 'Finance',
    'ops': 'Operations',
    'hr': 'HR',
    'mktg': 'Marketing',
    'prod': 'Product',
}

df['DEPT_NAME'] = df['DEPT_NAME'].str.strip().str.lower()
df['DEPT_NAME'] = df['DEPT_NAME'].replace(dept_map)
df['DEPT_NAME'] = df['DEPT_NAME'].str.title()

# Standardize division names
div_map = {
    'tech': 'Technology',
    'biz': 'Business',
    'op': 'Operations',
}
df['DIVISION'] = df['DIVISION'].str.strip().str.title()
df['DIVISION'] = df['DIVISION'].replace(div_map)
```

## Verification

```python
# Check for expected team code pattern
invalid_codes = df[~df['TEAM_CODE'].str.match(r'T\d{3}', na=False)]
if len(invalid_codes) > 0:
    print(f"WARNING: {len(invalid_codes)} invalid team codes")

# Verify no duplicate team codes
dupes = df['TEAM_CODE'].duplicated().sum()
assert dupes == 0, f"Duplicate team codes: {dupes}"

# Verify division values are standard
expected_divisions = {'Business', 'Technology', 'Operations'}
unexpected = set(df['DIVISION'].unique()) - expected_divisions
if unexpected:
    print(f"WARNING: Unexpected divisions: {unexpected}")
```
