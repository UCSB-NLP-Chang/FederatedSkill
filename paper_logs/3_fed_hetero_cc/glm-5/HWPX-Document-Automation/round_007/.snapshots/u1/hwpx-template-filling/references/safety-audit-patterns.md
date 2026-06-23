# Safety Audit Brief Patterns

Specific patterns for Korean warehouse safety audit HWPX documents.

## Data Structure Mapping

Input JSON typically has this structure:
```json
{
  "summary": {
    "점검ID": "SAF-26-041",
    "현장명": "부산 서부 냉장 창고",
    "주관점검자": "김도윤",
    "점검일": "2026-06-18",
    "위험등급": "High",
    "총평": "...",
    "보고대상": "..."
  },
  "immediate_actions": ["...", "...", "..."],
  "audit_items": [...]  // Often overlooked!
}
```

## Required Transformations

### 1. Date Format
```python
# YYYY-MM-DD → YYYY.MM.DD (required for safety audit briefs)
formatted_date = raw_date.replace('-', '.')
```

### 2. Risk Tier with Severity
```python
severity_map = {
    'High': '즉시조치',
    'Medium': '계획보완',
    'Low': '모니터링'
}
risk_display = f"{risk_tier}({severity_map[risk_tier]})"
```

### 3. Action Array to Numbered Placeholders
```python
actions = data['immediate_actions']
replacements = {
    '조치1': actions[0] if len(actions) > 0 else '',
    '조치2': actions[1] if len(actions) > 1 else '',
    '조치3': actions[2] if len(actions) > 2 else '',
}
```

## Common Failure: Missing Audit Items

The `audit_items` array often contains table data that maps to cell-specific placeholders. Inspect section XML for patterns like:
- `{{항목1_위험요인}}`, `{{항목1_등급}}`
- Or table cell positions that need manual mapping

If `audit_items` exists in JSON but no obvious placeholders exist in template, the table may use static structure with only summary fields dynamic.

## Verification Checklist

- [ ] All `summary` fields mapped to `{{...}}` placeholders
- [ ] `보고대상` field explicitly checked and mapped
- [ ] Date format converted to `YYYY.MM.DD`
- [ ] Risk tier includes severity annotation
- [ ] All `immediate_actions` mapped to `{{조치N}}` placeholders
- [ ] `audit_items` inspected — either mapped to placeholders or confirmed static
- [ ] No remaining `{{...}}` patterns in output
- [ ] All `linesegarray` elements removed from modified sections