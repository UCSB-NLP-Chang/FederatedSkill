# Validation Checklist & Assertion Templates

Use these patterns to verify outputs before submission.

## Excel Plan Verification
```python
import openpyxl

wb = openpyxl.load_workbook('output.xlsx')
ws = wb['Plan']  # Verify exact sheet name

# Check headers
expected_headers = ['Period', 'Days Worked', 'Scheduled Demand (Std Hrs)', 'Weekly Capacity (Std Hrs)', 'Start of Period Past Due (Std Hrs)', 'End of Period Backlog/Buffer (Std Hrs)', 'Overtime Hours']
# Note: Headers may use 'Week' instead of 'Period' - adjust expected_headers accordingly
actual_headers = [ws.cell(row=1, column=c).value for c in range(1, len(expected_headers)+1)]
assert actual_headers == expected_headers, f"Header mismatch: {actual_headers}"

# Check row count and period sequence
data_rows = ws.max_row - 1
periods = [ws.cell(row=r, column=1).value for r in range(2, ws.max_row+1)]

# Verify contiguous sequence (handles any start/end period, e.g., 1-52 or 4-53)
expected_periods = list(range(min(periods), max(periods)+1))
assert periods == expected_periods, f"Period sequence broken or contains gaps. Got {periods}"

# Verify no missing values in critical columns
for r in range(2, ws.max_row+1):
    for c in [1, 2, 3, 4, 7]:  # Period, Days, Demand, Capacity, Overtime
        val = ws.cell(row=r, column=c).value
        assert val is not None, f"Missing value at row {r}, col {c}"
```

## Transition Boundary Verification
When the simulation involves step-down policies (e.g., 6-day → 5-day → 4-day), explicitly verify the boundary periods:

```python
# Example: Verify transition around period 29
wb = openpyxl.load_workbook('output.xlsx')
ws = wb['Plan']

# Find the transition rows (adjust row numbers based on your period range)
for r in range(2, ws.max_row+1):
    period = ws.cell(row=r, column=1).value
    days = ws.cell(row=r, column=2).value
    eow = ws.cell(row=r, column=6).value  # End of period
    
    if period == 28:
        assert days == 6, f"Period 28 should be 6 days, got {days}"
        assert eow > 0, f"Period 28 should end with backlog, got {eow}"
    elif period == 29:
        assert days == 5, f"Period 29 should be first 5-day week, got {days}"
        # May have small buffer or near-zero backlog
    elif period == 30:
        assert days == 4, f"Period 30 should be first 4-day week, got {days}"
```

**Out-of-order transitions**: A first_4_day week may legitimately occur before first_5_day if demand spikes after backlog clears. Verify by checking actual simulation state, not by assuming 5-day always precedes 4-day.

## Summary Text Verification
```python
with open('summary.txt') as f:
    lines = f.read().strip().split('\n')

assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"

# Check format: First_Week_5_Days: X (or First_Period_5_Days)
line1_parts = lines[0].split(': ')
assert len(line1_parts) == 2 and '5' in line1_parts[0], f"Line 1 format wrong: {lines[0]}"

line2_parts = lines[1].split(': ')
assert len(line2_parts) == 2 and '4' in line2_parts[0], f"Line 2 format wrong: {lines[1]}"

# Validate values are integers or "N/A"
for val in [line1_parts[1], line2_parts[1]]:
    if val != 'N/A':
        int(val)  # Will raise ValueError if not valid integer

summary_line = lines[2].replace('Summary: ', '')
word_count = len(summary_line.split())
sentence_count = summary_line.count('.')

assert word_count <= 60, f"Summary too long: {word_count} words"
assert sentence_count <= 3, f"Too many sentences: {sentence_count}"

# Check mandatory mentions (values will vary by task)
# Summary should mention specific period numbers or N/A for step-down transitions
```

## Summary Consistency Verification
After simulation, verify summary text matches tracked variables:
```python
# Assuming first_4_day and first_5_day are tracked integers or None
first_4_str = str(first_4_day) if first_4_day is not None else 'N/A'
first_5_str = str(first_5_day) if first_5_day is not None else 'N/A'

with open('summary.txt') as f:
    content = f.read()

assert f"First_Week_4_Days: {first_4_str}" in content, f"Summary 4-day mismatch"
assert f"First_Week_5_Days: {first_5_str}" in content, f"Summary 5-day mismatch"
```

## Precision Verification
```python
# Ensure no rounding was applied
wb = openpyxl.load_workbook('output.xlsx')
ws = wb['Plan']

# Check a few cells for raw float precision (not rounded to 2 decimals)
sample = ws.cell(row=10, column=6).value  # End of Period column
if isinstance(sample, float):
    # Should have full precision, not exactly X.00 or X.XX
    # This is a heuristic - precise validation depends on expected values
    str_val = str(sample)
    assert '.' in str_val, "Value appears to be integer when float expected"
```

## Policy Logic Verification
When verifier fails but output looks correct, check these common issues:

1. **Days-worked transitions**: Verify the policy logic for when to switch from 6→5→4 days
   - Trace each period's decision against the stated policy rules
   - Check if backlog sign change triggers correct day reduction

2. **First occurrence tracking**: Ensure "first 5-day" and "first 4-day" periods are captured correctly
   - First 5-day: first period where days_worked == 5 (not 6)
   - First 4-day: first period where days_worked == 4 (not 5 or 6)
   - These may not be in ascending order; do not sort them

3. **Overtime calculation**: Verify formula matches spec (typically `ot_rate * max(0, days - base_days)`)

4. **Backlog vs buffer**: Negative end-of-period values represent buffer, not backlog
   - Start of Period Past Due should show 0 when prior period ended with buffer
