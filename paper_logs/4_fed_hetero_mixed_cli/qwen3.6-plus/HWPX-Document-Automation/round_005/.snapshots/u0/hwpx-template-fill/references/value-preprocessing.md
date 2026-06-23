# Value Preprocessing Patterns for HWPX Templates

Common value transformations needed before filling Korean document templates.

## Unit Stripping

Remove Korean counting units to get bare numbers for forms.

```python
import re

def extract_digits(value):
    """Extract only digits from a string.

    Examples:
        "32명" → "32"
        "150,000원" → "150000"
        "3시간" → "3"
    """
    return re.sub(r'[^0-9]', '', str(value))

# Usage
raw = {"참석자수": "32명", "예산": "150,000원"}
processed = {k: extract_digits(v) for k, v in raw.items()}
# Result: {"참석자수": "32", "예산": "150000"}
```

## Rating Reformatting

Convert machine-readable ratings to Korean document format.

```python
def format_korean_rating(value, max_score=None):
    """Convert rating to Korean format.

    Examples:
        "4.5/5.0" → "4.5점 (5.0점 만점)"
        4.5 (with max_score=5) → "4.5점 (5점 만점)"
        "90/100" → "90점 (100점 만점)"
    """
    if '/' in str(value):
        score, max_val = str(value).split('/')
        return f"{score.strip()}점 ({max_val.strip()}점 만점)"
    elif max_score:
        return f"{value}점 ({max_score}점 만점)"
    return f"{value}점"

# Usage
raw = {"만족도": "4.5/5.0"}
processed = {"만족도": format_korean_rating(raw["만족도"])}
# Result: {"만족도": "4.5점 (5.0점 만점)"}
```

## Phone Normalization

Format Korean mobile numbers consistently.

```python
def normalize_phone(phone):
    """Format phone number as 010-0000-0000.

    Handles various input formats:
        "01011112222" → "010-1111-2222"
        "010-1111-2222" → "010-1111-2222" (unchanged)
        "02-123-4567" → "02-123-4567" (landline preserved)
    """
    digits = re.sub(r'[^0-9]', '', str(phone))
    if len(digits) == 11 and digits.startswith('010'):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    elif len(digits) == 10 and digits.startswith('02'):
        return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
    return phone  # Return original if pattern not matched
```

## Text Enrichment

Append or combine text fields.

```python
def append_text(base_text, addition, separator=' '):
    """Append additional text with separator.

    Examples:
        base="기초 개념 설명이 명확했습니다", addition="후속 심화반 검토 요망"
        → "기초 개념 설명이 명확했습니다 후속 심화반 검토 요망"
    """
    return f"{base_text}{separator}{addition}"

def combine_with_label(value, label, unit=''):
    """Add label and unit to a value.

    Examples:
        value="2026-09-10", label="교육일시"
        → Can be used in template as "{{label}}: {{value}}"
    """
    return f"{value}{unit}"
```

## Date Formatting

Convert between date formats.

```python
from datetime import datetime

def format_korean_date(date_str, input_format='%Y-%m-%d', output_format='%Y년 %m월 %d일'):
    """Convert date string to Korean format.

    Examples:
        "2026-09-10" → "2026년 09월 10일"
    """
    try:
        dt = datetime.strptime(date_str, input_format)
        return dt.strftime(output_format)
    except ValueError:
        return date_str  # Return original if parsing fails
```

## Korean Age Calculation

Calculate Korean age ( 만 나이 or 세는 나이 ) for forms.

```python
from datetime import datetime

def calculate_korean_age(birth_date_str, reference_date=None, method='western'):
    """Calculate age from birth date.

    Args:
        birth_date_str: Birth date in format 'YYYY-MM-DD'
        reference_date: Date to calculate age against (default: today)
        method: 'western' (만 나이) or 'traditional' (세는 나이)

    Returns:
        Age as integer string
    """
    birth = datetime.strptime(birth_date_str, '%Y-%m-%d')
    ref = reference_date or datetime.now()

    if method == 'traditional':
        # Korean traditional age: born at 1, increments on New Year
        age = ref.year - birth.year + 1
    else:
        # Western age (만 나이)
        age = ref.year - birth.year
        if (ref.month, ref.day) < (birth.month, birth.day):
            age -= 1

    return str(age)
```

## Complete Preprocessing Example

```python
import json
import re
from datetime import datetime

def preprocess_training_feedback(raw_data):
    """Example preprocessing for training feedback forms."""
    processed = {}

    # Direct copies
    for key in ['교육명', '교육일시', '장소', '강사', '유익내용',
                '개선사항', '희망교육', '강사평가', '자료평가', '실습평가']:
        processed[key] = raw_data.get(key, '')

    # Strip unit from count
    processed['참석자수'] = re.sub(r'[^0-9]', '', raw_data.get('참석자수', ''))

    # Reformat rating
    satisfaction = raw_data.get('만족도', '')
    if '/' in satisfaction:
        score, max_val = satisfaction.split('/')
        processed['만족도'] = f"{score.strip()}점 ({max_val.strip()}점 만점)"
    else:
        processed['만족도'] = satisfaction

    # Append to opinion text
    base_opinion = raw_data.get('종합의견', '')
    processed['종합의견'] = f"{base_opinion} 후속 심화반 검토 요망."

    return processed

# Usage
with open('raw_data.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

processed = preprocess_training_feedback(raw)
# Now pass processed to fill_hwpx_template function
```
