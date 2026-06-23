# Validation Checklist & Assertion Templates

Use these patterns to verify outputs before submission.

## Excel Plan Verification
```python
import openpyxl

wb = openpyxl.load_workbook('output.xlsx')
ws = wb['Plan']  # Verify exact sheet name

# Check headers
expected_headers = ['Week', 'Days Worked', 'Scheduled Demand (Std Hrs)', 'Weekly Capacity (Std Hrs)', 'Start of Week Past Due (Std Hrs)', 'End of Week Backlog/Buffer (Std Hrs)', 'Overtime Hours']
actual_headers = [ws.cell(row=1, column=c).value for c in range(1, len(expected_headers)+1)]
assert actual_headers == expected_headers, f"Header mismatch: {actual_headers}"

# Check row count and week sequence
data_rows = ws.max_row - 1
weeks = [ws.cell(row=r, column=1).value for r in range(2, ws.max_row+1)]
assert data_rows == 49, f"Expected 49 rows, got {data_rows}"
assert weeks == list(range(4, 53)), "Week sequence broken or contains gaps"
```

## Summary Text Verification
```python
with open('summary.txt') as f:
    lines = f.read().strip().split('\n')

assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"

summary_line = lines[2].replace('Summary: ', '')
word_count = len(summary_line.split())
sentence_count = summary_line.count('.')

assert word_count <= 60, f"Summary too long: {word_count} words"
assert sentence_count <= 3, f"Too many sentences: {sentence_count}"

# Check mandatory mentions (adjust values as needed)
assert '10' in summary_line or 'N/A' in summary_line, "Missing step-down week numbers"
```

## Policy Logic Verification
When verifier fails but output looks correct, check these common issues:

1. **Days-worked transitions**: Verify the policy logic for when to switch from 6→5→4 days
   - Trace each week's decision against the stated policy rules
   - Check if backlog sign change triggers correct day reduction

2. **First occurrence tracking**: Ensure "first 5-day" and "first 4-day" weeks are captured correctly
   - First 5-day: first week where days_worked == 5 (not 6)
   - First 4-day: first week where days_worked == 4 (not 5 or 6)

3. **Overtime calculation**: Verify formula matches spec (typically `10 * max(0, days - 4)`)

4. **Backlog vs buffer**: Negative end-of-week values represent buffer, not backlog
   - Start of Week Past Due should show 0 when prior week ended with buffer
