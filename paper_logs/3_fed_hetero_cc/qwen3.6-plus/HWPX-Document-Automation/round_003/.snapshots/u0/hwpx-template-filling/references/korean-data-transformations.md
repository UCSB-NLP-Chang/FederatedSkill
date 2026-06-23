# Korean Data Transformations

Common data transformations needed before filling HWPX templates with Korean content.

## Korean Full-Year Age (만 나이)

Korean legal age (만 나이) is calculated as:
- `age = reference_year - birth_year`
- Subtract 1 if the birthday has not yet occurred in the reference year.

```python
from datetime import date

def korean_full_year_age(birth_date: date, reference_date: date) -> int:
    age = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age

# Example:
birth = date(1990, 11, 2)
visit = date(2026, 5, 9)
age = korean_full_year_age(birth, visit)  # Returns 35
```

Use this when templates expect `{{생년월일}}` to be replaced with `YYYY-MM-DD (N세)` format.

## Korean Phone Number Normalization

Normalize Korean phone numbers to `000-0000-0000` format:

```python
import re

def normalize_korean_phone(raw: str) -> str:
    # Extract digits only
    digits = re.sub(r'\D', '', raw)
    # Handle common Korean formats
    if len(digits) == 11 and digits.startswith('010'):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    elif len(digits) == 10:
        # Could be 02-XXXX-XXXX (Seoul) or 0XX-XXX-XXXX
        if digits.startswith('02'):
            return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return raw  # Return as-is if format unknown

# Example:
normalize_korean_phone('01044217783')  # Returns '010-4421-7783'
normalize_korean_phone('010-4421-7783')  # Returns '010-4421-7783'
```

## Date Formatting

Korean templates often expect `YYYY-MM-DD` format:

```python
def format_korean_date(d: date) -> str:
    return d.strftime('%Y-%m-%d')
```

## Usage Pattern

When filling HWPX templates:
1. Load raw JSON data
2. Apply transformations to relevant fields
3. Write transformed JSON to a temp file
4. Pass transformed JSON to `scripts/fill_hwpx.py`

Or inline the transformations in a single processing script if the data pipeline is simple.