---
name: workload-capacity-planning
description: Simulates deterministic weekly capacity, backlog, and overtime policies from Excel or CSV input data. Generates structured Excel plans and strictly formatted summary text files. Use when tasks require week-by-week workload simulation, backlog burn-down calculations, and output validation against strict formatting constraints. Trigger when you see Excel/CSV capacity data, weekly demand schedules, step-down plans, or phrases like 'catch-up plan', 'backlog clearance', 'overtime policy'.
---

# Workload & Capacity Planning Simulation

## ⚠️ CRITICAL RULES - STOP BEFORE PROCEEDING

**READ THESE BEFORE STARTING. These are the most common failure causes.**

1. **ALWAYS use `python3` command** — never `python`. The `python` command may not be aliased on your system.
2. **NEVER use Read tool on .xlsx files** — it cannot read binary Excel. Always use Python with openpyxl.
3. **STOP after parsing and VERIFY data is non-empty** — if `len(demand_dict) == 0`, your parsing logic targets wrong rows/columns. Re-inspect immediately.
4. **BEFORE writing summary, VERIFY week numbers match tracked variables** — the `first_4_day` and `first_5_day` values in your summary must exactly match your simulation variables. Do not sort or swap them.

---

## Step 0: Mandatory Layout Inspection
**Never assume layout orientation.** Always run a quick inspection before parsing. Use `python3` (not `python`).

### For Excel (.xlsx):
```python
import openpyxl
wb = openpyxl.load_workbook('input.xlsx', data_only=True)
ws = wb.active
print(f"Dimensions: {ws.dimensions}, MaxRow: {ws.max_row}, MaxCol: {ws.max_column}")
for r in range(1, min(4, ws.max_row+1)):
    print(f"Row {r}: {[ws.cell(row=r, column=c).value for c in range(1, min(4, ws.max_column+1))]}")
```

### For CSV:
```python
import csv
with open('input.csv') as f:
    reader = csv.reader(f)
    for i, row in enumerate(reader):
        if i < 3:
            print(f"Row {i}: {row[:10]}...")  # Print first 10 columns
```

**Decision Rule**:
- If `max_column <= 3` and Row 1 contains labels like "Week", "Period", "Demand" → **Vertical Layout**. Parse with `ws.iter_rows(min_row=2, values_only=True)`.
- If `max_column > 10` and headers contain period numbers (e.g., `4, 5, 6...`) → **Horizontal Layout**. See `references/horizontal-data-parsing.md`.
- For CSV: if first row contains sequential numbers (weeks/periods) and second row starts with "Demand" → **Horizontal CSV**. Parse with `csv.DictReader` or index-based extraction.

**Terminology note**: Tasks may use "Week", "Period", or "Phase" interchangeably. Headers may say "Start of Week" or "Start of Period"—treat these as equivalent.

## Step 1: Data Extraction & Duplicate Detection
When parsing demand data, check for duplicate period entries:
```python
phases = []
demands = []
for row in ws.iter_rows(min_row=2, values_only=True):
    phase = row[0]
    demand = row[1]
    if phase is not None:
        phases.append(int(phase))
        demands.append(float(demand) if demand else 0)

# Check for duplicates
duplicates = [p for p in set(phases) if phases.count(p) > 1]
if duplicates:
    print(f"WARNING: Duplicate phases detected: {duplicates}")
    # Resolution: Sum demands for duplicate phases
    phase_demand = {}
    for p, d in zip(phases, demands):
        phase_demand[p] = phase_demand.get(p, 0) + d
    phases = sorted(phase_demand.keys())
    demands = [phase_demand[p] for p in phases]

# ⚠️ STOP: Verify parsed data is non-empty
assert len(phases) > 0 and len(demands) > 0, "PARSING FAILED: Zero demand values extracted. Re-inspect sheet structure."
print(f"Parsed {len(phases)} periods successfully")
```

## Workflow
1. **Extract Input Data**: Run layout inspection. Check for and resolve duplicate periods. Identify sheet orientation. Parse period-to-demand mapping carefully. Handle multiple sheets if present (e.g., base demand + adjustments).
2. **Resolve Initial State**: Carefully separate "Start of Period Past Due" from "Scheduled Demand" if the prompt provides a combined initial condition (e.g., "Start + Demand = X"). Avoid double-counting demand in the first period's calculation.
   - Formula: `calc_start = combined_value - demand[first_period]`
3. **Define Policy Rules**: Map the deterministic decision tree from the prompt:
   - Capacity per day (common: 20, 25, or 30 std hrs)
   - Days-to-capacity mapping (4 days = 80/100/120, 5 days = 100/125/150, 6 days = 120/150/180)
   - Backlog clearing logic (choose minimum days to drive `End of Period <= 0`)
   - Steady-state logic (if demand <= capacity_4d, use 4 days; else if <= capacity_5d, use 5 days, etc.)
   - Overtime calculation: `ot_rate * max(0, days_worked - base_days)`
4. **Run Simulation**: Iterate period-by-period. Track:
   - `prior_end`: Signed backlog/buffer from previous period
   - `start_past_due`: `max(0, prior_end)` for reporting
   - `capacity`: Based on days selected by policy
   - `overtime`: Based on days worked
   - `end_of_period`: `start_past_due + demand - capacity`

   Record first occurrences: first 4-day period, first 5-day period (track as `None` initially, assign period number when first triggered).

   **Note on transition ordering**: The first 4-day week may occur before the first 5-day week if demand spikes after backlog clears. Track actual occurrences, not assumed sequences.
5. **Generate Excel Output**: Create workbook. Name sheet exactly as specified (e.g., `Plan`). Write headers and data rows. **Never round numeric values**—pass raw floats. Ensure period sequences are contiguous.
6. **Generate Summary Text**: Format strictly per task spec. Common pattern: 3 lines (First_Period_5_Days, First_Period_4_Days, Summary).
   - Use `N/A` for transitions never triggered
   - Summary: max 60 words, max 3 sentences
   - Must explicitly mention step-down period numbers or `N/A`
   - **Python Tip**: Compute transition periods as integers first (`first_5 = int(...)`) before using them in f-strings or arithmetic to avoid type errors.

   **⚠️ STOP: Before writing summary, verify consistency:**
   ```python
   # Verify summary values match tracked simulation variables
   first_4_str = str(first_4_day) if first_4_day is not None else 'N/A'
   first_5_str = str(first_5_day) if first_5_day is not None else 'N/A'
   print(f"First 4-day week: {first_4_str}, First 5-day week: {first_5_str}")
   # Ensure these exact values go into your summary file
   ```
7. **Verify Programmatically**: Run assertions before submitting. See `references/validation-checklist.md`.
8. **Cleanup**: Remove temporary helper scripts (`generate_plan.py`, `verify_plan.py`, etc.) after verification passes.

## Critical Decision Rules
- **Excel Orientation**: If you see `(1):Week` or row 4 with period numbers `(2):4 (3):5...` in the raw cell output, you're looking at horizontal/transposed data. Use column-based parsing. See `references/horizontal-data-parsing.md`.
- **CSV Input**: If input is CSV with weeks as columns (first row: `Week,5,6,7...`; second row: `Demand,164.51,155.93...`), parse with `csv.reader` and extract demand by column index. Same horizontal parsing logic applies.
- **Library Choice**: Always use `openpyxl` for Excel operations. Do not use pandas for Excel parsing—it adds dependency complexity and is unnecessary for this workflow.
- **Duplicate Periods**: Input data may contain duplicate period entries (e.g., phase 10 appearing twice). Detect these and resolve by summing demand values before simulation.
- **Initial Condition Parsing**: If given `Start of Period Past Due + Scheduled Demand = X`, compute `Calc Start = X - Demand[first_period]` to prevent double-counting when applying `End = Calc Start + Demand - Capacity`.
- **State Tracking**: Use `max(0, prior_end)` for reporting `Start of Period Past Due`, but keep the signed `prior_end` for actual backlog/buffer calculations. Negative values indicate buffer (ahead of schedule).
- **N/A Handling**: If a policy state (e.g., 5-day period) is never triggered, explicitly output `N/A` in both the tracking variables and the summary text. Do not invent placeholder periods.
- **Summary Constraints**: Count words and sentences programmatically. Ensure the summary explicitly mentions both step-down period numbers (or `N/A`).

## Summary Text Generation
**Common failure: exceeding sentence count limit.** Most tasks require max 3 sentences.

Before writing summary file, validate:
```python
summary_text = "Your generated summary here."
word_count = len(summary_text.split())
sentence_count = summary_text.count('.')
print(f"Words: {word_count}, Sentences: {sentence_count}")
assert sentence_count <= 3, f"Too many sentences: {sentence_count}"
assert word_count <= 60, f"Too many words: {word_count}"
```

**To reduce sentence count**: Combine related clauses with commas or conjunctions instead of periods:
- Before: "Catch-up completed by Week 22. Step-down to 4-day weeks in Week 23. Then 5-day weeks in Week 24. Final buffer of 645 hours." (4 sentences)
- After: "Catch-up completed by Week 22. Step-down to 4-day weeks in Week 23, then 5-day weeks in Week 24 for higher demand periods, accumulating a final buffer of 645 hours." (3 sentences)

## Output Precision
Never round, truncate, or fixed-format numeric values when writing outputs (Excel cells, JSON, CSV). Pass raw float values directly.
- **DO NOT**: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- **DO**: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- Rationale: The verifier's tolerance (often 1e-4) decides precision; provide full precision.

## Verification
Always validate before submitting. See `references/validation-checklist.md` for reusable assertion templates covering:
- Excel: Sheet name, headers, row count, period contiguity, duplicate detection
- Text: Line count, word/sentence limits, mandatory value presence
- Summary consistency: Verify summary text values match tracked simulation variables

## Anti-Patterns
- **Do not** use the Read tool on .xlsx files. The Read tool cannot read binary Excel files and will fail. Always use Python with openpyxl instead.
- **Do not** assume vertical/table layout for Excel input. Always run the Step 0 inspection first. Many tasks use simple 2-column vertical layouts.
- **Do not** ignore duplicate period entries in input data—they will corrupt simulation results if not handled.
- **Do not** assume initial condition is purely backlog; verify if it includes scheduled demand and subtract first period demand if so.
- **Do not** use string formatting on numeric outputs (no rounding).
- **Do not** hardcode summary text; generate dynamically from tracked variables.
- **Do not** skip verification; formatting constraints are strict and easily violated.
- **Do not** use `python` command; always use `python3`.
- **Do not** use pandas for Excel parsing; use openpyxl directly.
- **Do not** proceed with simulation if parsed demand dict is empty—re-inspect sheet structure first.
- **Do not** leave temporary helper scripts in the workspace after verification.

## Known invariants (by sub-task)

### capacity-backlog-simulation
- Input data may contain duplicate period entries—always detect and resolve (typically by summing demand) before simulation.
- Initial condition statements often combine "Start of Period Past Due" with "Scheduled Demand" — parse carefully to avoid double-counting in Period 1.
- Summary text must be generated dynamically from tracked variables; hardcoded text goes stale.
- Word/sentence count constraints are strict and easily violated by minor phrasing changes.
- Horizontal Excel layouts (periods as columns) require column-wise iteration instead of row-wise.
- Period ranges vary by task (commonly 1-52 or 4-53); never assume a fixed row count.
- Capacity values (hrs/day) are task-specific; common values include 20, 25, 30—read from task description.
- Step-down transitions may occur out of order (e.g., 4-day week before 5-day week) depending on demand volatility after backlog clears.