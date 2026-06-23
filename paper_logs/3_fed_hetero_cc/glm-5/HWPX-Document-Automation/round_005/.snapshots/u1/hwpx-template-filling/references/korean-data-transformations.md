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

## Budget/Currency Normalization

Korean documents often contain budget values with commas that should be normalized. Remove commas while preserving the currency symbol:

```python
import re

def normalize_budget(raw: str) -> str:
    # Remove commas from numbers while keeping currency symbols
    # Input: "₩450,000,000" -> Output: "₩450000000"
    return re.sub(r'(\d),(\d)', r'\1\2', raw)

# For multiple passes if needed:
def normalize_budget_thorough(raw: str) -> str:
    while ',' in raw:
        raw = re.sub(r'(\d),(\d)', r'\1\2', raw)
    return raw

# Example:
normalize_budget('₩450,000,000')  # Returns '₩450000000'
```

## Unit & Counter Stripping

Korean templates often include raw values with units or counters that must be stripped before filling numeric or count placeholders:

```python
import re

def strip_korean_units(raw: str) -> str:
    """Remove common Korean counters/units (명, 원, 점, 개월, etc.) and whitespace."""
    # Remove trailing units and whitespace
    cleaned = re.sub(r'[\s]*(명|원|점|개월|년|일|시간|분|초|개|권|대|채|평|㎡|㎥|kg|g|L|ml|%)[\s]*$', '', raw.strip())
    # Extract digits if the result is purely numeric-looking
    if re.match(r'^[\d,]+$', cleaned):
        return cleaned.replace(',', '')
    return cleaned

# Example:
strip_korean_units('32명')  # Returns '32'
strip_korean_units('₩450,000')  # Returns '450000'
strip_korean_units('4.5/5.0')  # Returns '4.5/5.0' (unchanged, not a unit match)
```

## Satisfaction Score Reformatting

Korean feedback forms often use `X/Y` format that should be converted to Korean text:

```python
import re

def format_satisfaction_korean(raw: str) -> str:
    """Convert 'X/Y' satisfaction score to Korean format.

    Input: '4.5/5.0' -> Output: '4.5점 (5.0점 만점)'
    Input: '3/5' -> Output: '3점 (5점 만점)'
    """
    match = re.match(r'^([\d.]+)\s*/\s*([\d.]+)$', raw.strip())
    if match:
        score, max_score = match.groups()
        return f"{score}점 ({max_score}점 만점)"
    return raw  # Return as-is if format doesn't match

# Example:
format_satisfaction_korean('4.5/5.0')  # Returns '4.5점 (5.0점 만점)'
format_satisfaction_korean('3/5')  # Returns '3점 (5점 만점)'
```

## Append Text to Field Value

When augmenting existing field values (e.g., adding notes to feedback):

```python
def append_to_field(original: str, suffix: str, separator: str = ' ') -> str:
    """Append text to a field value with proper spacing.

    Input: ('기존 의견입니다.', '추가 내용.') -> Output: '기존 의견입니다. 추가 내용.'
    """
    if not original:
        return suffix
    if not suffix:
        return original
    # Ensure proper sentence ending
    if original.endswith('.') or original.endswith('!') or original.endswith('?'):
        return f"{original}{separator}{suffix}"
    return f"{original}.{separator}{suffix}"

# Example:
append_to_field('기초 개념 설명이 명확했으나 실습 난이도 조정이 필요합니다.', '후속 심화반 검토 요망.')
# Returns: '기초 개념 설명이 명확했으나 실습 난이도 조정이 필요합니다. 후속 심화반 검토 요망.'
```

## Month Span Calculation

Calculate the number of months between two dates for project schedules:

```python
from datetime import date

def month_span(start: date, end: date) -> int:
    """Calculate months between dates (inclusive of start month)."""
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return months

def format_month_span(start: date, end: date) -> str:
    """Return Korean month span text like '(3개월)'."""
    months = month_span(start, end)
    return f"({months}개월)"

# Example:
start = date(2026, 8, 1)
end = date(2026, 10, 31)
format_month_span(start, end)  # Returns '(3개월)'
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
4. Pass transformed JSON to `scripts/fill_hwpx_template.py`

Or inline the transformations in a single processing script if the data pipeline is simple.

## Common Transformation Summary

| Field Type | Input Example | Output Example | Function |
|------------|---------------|----------------|----------|
| Count with unit | '32명' | '32' | `strip_korean_units()` |
| Satisfaction score | '4.5/5.0' | '4.5점 (5.0점 만점)' | `format_satisfaction_korean()` |
| Free-form text + append | '기존 의견.' | '기존 의견. 추가 내용.' | `append_to_field()` |
| Phone | '01044217783' | '010-4421-7783' | `normalize_korean_phone()` |
| Budget | '₩450,000,000' | '₩450000000' | `normalize_budget()` |
| Age | birth_date + visit_date | 35 | `korean_full_year_age()` |
| Month span | dates | '(3개월)' | `format_month_span()` |