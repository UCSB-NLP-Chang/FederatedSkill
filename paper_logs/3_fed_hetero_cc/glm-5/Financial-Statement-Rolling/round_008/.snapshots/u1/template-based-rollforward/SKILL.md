---
name: template-based-rollforward
description: Build rollforward workbooks starting from an existing Excel template file. Use when the task provides a template.xlsx to populate rather than building from scratch, or when GL balances must be mapped to specific month-ending columns (E, H, K, N). Distinct from financial-rollforward-workbook which builds from scratch.
---

# Template-Based Rollforward Builder

## When to use
- Task provides `template.xlsx` or similar starter file to populate
- Must preserve existing template structure, headers, or styling
- GL balances map to alternating columns (E, H, K, N for month endings)
- Building summary sheets that link to multiple detail sheet control rows
- Data requires normalization (filtering, deduplication, overrides, insertions) before populating

## STOP AND CHECK: Pre-Flight Checklist (MANDATORY)

**Before running tests or declaring success, verify:**

1. **Template loaded**: Used `load_workbook(template_path)`, NOT `Workbook()`
2. **Variance formula**: `=N{gl_row}-N{eb_row}` — column N for BOTH operands
3. **Ending Balance first period**: `=B{pt_row}+C{pt_row}-D{pt_row}` — reference PT row
4. **Summary GL links**: Use `!N{gl_row}`, NOT `!O{gl_row}`
5. **Row alignment**: Label A{n} and formula B{n} in same row

If any check fails, the test suite WILL fail. Fix first.

## Workflow (MANDATORY sequence)

1. **Load the template first.** Use `openpyxl.load_workbook(template_path)` to preserve all formatting, headers, and structure. Do NOT create a new workbook.
2. **Parse all input sources.** Load JSON snapshots, CSV adjustments, JSON GL balances, and any account mapping files.
3. **Normalize data.** Apply the normalization pipeline below BEFORE writing to sheets.
4. **Populate detail sheets.** Write data rows into the template's existing structure. Preserve template headers and formatting.
5. **Write control rows.** Period Totals -> Ending Balance -> Variance -> GL Balance. Use formula patterns from `financial-rollforward-workbook` skill.
6. **Build summary sheet.** Cross-sheet links with single quotes for sheet names containing spaces.
7. **Run quick validation.** `python scripts/verify_template_rollforward.py <workbook>` — catches the most common bugs.
8. **Run the actual test suite.** Self-verification is insufficient. Run `pytest` to catch structural mismatches.

## Data Normalization Pipeline

### Step 1: Filter records
- JSON snapshots: filter by `approved=true` AND `row_kind=detail` (or equivalent status flags)
- Exclude unapproved, summary-type, or inactive records

### Step 2: Deduplicate
- Group by unique identifier (`case_id`, `row_id`, etc.)
- Keep highest `version` number when duplicates exist
- Example: ER-100 v2 supersedes ER-100 v1

### Step 3: Apply CSV overrides
- CSV adjustments with `action=override` modify existing records
- Match by `row_id` or equivalent key
- Override specific fields (e.g., `nov_adds`, `comments`) while preserving other fields
- **CRITICAL**: Override values may target nested structures (e.g., `flow_months.nov.accrued`). Map CSV columns to the correct nested path.

### Step 4: Insert new rows
- CSV adjustments with `action=insert` add new records
- Place in the correct bucket/sheet based on `target_bucket` or `account_number`
- Convert CSV string values to appropriate types (float for amounts, int for versions)

## GL Balance Column Mapping

| Month | GL Column | Purpose |
|-------|-----------|---------|
| Month 1 | E | July ending |
| Month 2 | H | August ending |
| Month 3 | K | September ending |
| Month 4 | N | October ending |

GL Balance row writes **static values** to E, H, K, N—not formulas.

## Summary Sheet Construction

### Row Alignment (CRITICAL)
Label column (A) and formula column (B) must align to same row.

```python
# CORRECT: Each label row has its formula in same row
def build_summary_section(ws, start_row, section_title, sheet_refs):
    """Build a summary section with aligned label/formula rows.

    sheet_refs: dict with 'period_totals_row', 'ending_balance_row', 'gl_balance_row'
    """
    ws[f'A{start_row}'] = section_title
    ws[f'A{start_row}'].font = Font(bold=True)

    # Row+2: Period Totals
    ws[f'A{start_row+2}'] = 'Period Totals'
    ws[f'B{start_row+2}'] = f"='{section_title}'!O{sheet_refs['period_totals_row']}"

    # Row+3: Ending Balance
    ws[f'A{start_row+3}'] = 'Ending Balance'
    ws[f'B{start_row+3}'] = f"='{section_title}'!O{sheet_refs['ending_balance_row']}"

    # Row+4: GL Balance (COLUMN N, NOT O)
    ws[f'A{start_row+4}'] = 'GL Balance'
    ws[f'B{start_row+4}'] = f"='{section_title}'!N{sheet_refs['gl_balance_row']}"

    return start_row + 4  # Return last row used
```

**Row spacing rule**: Leave blank row after section title (start_row+1 is spacer).

### Multi-section summary layout
```
Row 1:  Company Name (title)
Row 2:  Report Title
Row 3:  Period Ending
Row 5:  Section 1 Title (bold)
Row 7:  Period Totals      B7=Sheet1!O{pt_row}
Row 8:  Ending Balance     B8=Sheet1!O{eb_row}
Row 9:  GL Balance         B9=Sheet1!N{gl_row}  <- N not O
Row 11: Section 2 Title (bold)
Row 12: Period Totals      B12=Sheet2!O{pt_row}
Row 13: Ending Balance     B13=Sheet2!O{eb_row}
Row 14: GL Balance         B14=Sheet2!N{gl_row}  <- N not O
Row 16: Total GL Balance   B16=B9+B14
```

## Template Preservation Rules

- **Never** recreate headers that exist in the template
- **Never** modify template formatting, column widths, or frozen panes
- **Only** write to data cells and formula cells that need population
- **Preserve** template cell positions for summary links (e.g., B7, B8, B9 are spec-given, not inferred)
- **Check** for placeholder text like "OLD TEMPLATE" in A1 - this indicates the template was loaded correctly

## Control Row Formula Patterns

Reuse patterns from `financial-rollforward-workbook` skill. Key invariants:
- Variance formula MUST use column N for both operands: `=N{gl_row}-N{ending_row}`
- Ending Balance Beginning cell MUST reference Period Totals row, not self
- Sheet names with spaces need single quotes in cross-sheet references

## Validation Strategy

### Quick validation (MANDATORY)
Run `scripts/verify_template_rollforward.py <workbook_path>` before declaring success.
This catches:
- GL Balance links using column O instead of N
- Summary label/formula row misalignment
- Cross-sheet reference errors

### Test suite (MANDATORY)
- **ALWAYS run the actual test suite** before declaring success
- Self-verification passing does NOT guarantee test suite passing
- Common test failures: wrong cell positions, missing formulas, incorrect sheet names, structural mismatches with expected output
- If tests fail, inspect the test file to understand exact expectations (cell positions, formula patterns, sheet structure)

## Anti-patterns (DO NOT DO)

| Wrong | Right | Why |
|-------|-------|-----|
| `='Sheet'!O{gl_row}` | `='Sheet'!N{gl_row}` | GL Balance lives in column N |
| Label in A12, formula in B13 | Same row | Misalignment breaks readability |
| `ws['A12'] = title; ws['A13'] = 'Period Totals'` | `ws['A11']=title; ws['A12']='Period Totals'` | Off-by-one errors |
| `B16 = B8+B13` | `B16 = B9+B14` | Wrong rows for GL Balance |
| Rebuilding template from scratch | Loading and modifying | Loses client formatting |
| Creating a new workbook instead of loading template | `load_workbook(template_path)` | Must preserve template structure |
| Ignoring CSV override columns | Map to nested JSON paths | Override values may be nested |
| Assuming cell positions are dynamic | Check spec/template for exact positions | Template defines positions |
| Relying on self-verification | Run actual test suite | Self-verification can miss structural bugs |
| Not checking `action` field in CSV | Override vs insert distinction | Different handling for each |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Tests fail on cell positions | Summary links at wrong rows | Check spec/template for exact cell positions (B7, B8, etc.) |
| Tests fail on formulas | Wrong column references | Use Variance column-N rule; check Ending Balance references Period Totals |
| Tests fail on sheet names | Missing spaces or wrong format | Match template sheet names exactly; use single quotes in formulas |
| Override not applied | CSV column not mapped to nested path | Map `nov_adds` to `flow_months.nov.accrued`, etc. |
| Duplicate records in output | Deduplication not applied | Group by ID, keep highest version |
| GL Balance mismatch | Wrong column in cross-sheet refs | Summary GL links must use column N |
| Summary formulas show #REF! | Sheet name mismatch | Confirm exact sheet names; use single quotes for spaces |

## References

- `financial-rollforward-workbook` skill for control row formula patterns
- `scripts/verify_template_rollforward.py` - Validation script

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.
