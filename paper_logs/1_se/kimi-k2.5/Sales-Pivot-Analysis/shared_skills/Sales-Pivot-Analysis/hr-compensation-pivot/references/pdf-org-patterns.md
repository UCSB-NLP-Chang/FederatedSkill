# PDF Org Structure Parsing Patterns

## Common HRIS Export Formats

### Format A: Fixed-Width Columns
```
D01  Engineering      San Francisco   5,000,000
D02  Marketing        New York        3,000,000
D03  Sales            Chicago         3,500,000
```

```python
lines = [l for l in pdf_text.split('\n') if l.strip() and l[0:2] == 'D']
data = []
for line in lines:
    code = line[0:3].strip()
    name = line[4:20].strip()
    location = line[21:36].strip()
    budget = line[37:].strip().replace(',', '')
    data.append([code, name, location, budget])
```

### Format B: Labeled Rows
```
Department: D01 - Engineering
Location: San Francisco
Annual Budget: $5,000,000
```

```python
import re
records = re.split(r'Department:\s*', pdf_text)[1:]
data = []
for rec in records:
    code = re.search(r'(D\d{2})', rec)
    name = re.search(r'-\s*([\w\s]+?)(?:\n|Location:)', rec)
    loc = re.search(r'Location:\s*([\w\s]+?)(?:\n|Annual)', rec)
    budget = re.search(r'Budget:\s*\$?([\d,]+)', rec)
    if code and name:
        data.append([
            code.group(1),
            name.group(1).strip(),
            loc.group(1).strip() if loc else None,
            budget.group(1).replace(',', '') if budget else None
        ])
```

### Format C: Table with Headers
```
Code  Name            Location       Budget
D01   Engineering     San Francisco  5000000
D02   Marketing       New York       3000000
```

```python
lines = [l for l in pdf_text.split('\n') if l.strip() and l.startswith('D')]
data = []
for line in lines:
    parts = re.split(r'\s{2,}', line.strip())  # split on 2+ spaces
    if len(parts) >= 4:
        data.append([p.strip() for p in parts])
```

## Data Cleaning

```python
# Standardize location names
location_map = {
    'SF': 'San Francisco',
    'NYC': 'New York',
    'CHI': 'Chicago'
}
df['LOCATION'] = df['LOCATION'].replace(location_map)

# Parse budget with currency symbols
df['ANNUAL_BUDGET'] = df['ANNUAL_BUDGET'].str.replace(r'[$,]', '', regex=True).astype(float)

# Ensure department codes are uppercase standardized
df['DEPT_CODE'] = df['DEPT_CODE'].str.upper().str.strip()
```
