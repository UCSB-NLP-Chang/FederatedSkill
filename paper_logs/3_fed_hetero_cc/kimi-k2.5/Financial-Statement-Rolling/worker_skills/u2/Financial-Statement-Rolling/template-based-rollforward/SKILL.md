---
name: template-based-rollforward
description: Build rollforward workbooks starting from an existing Excel template file. Use when the task provides a template.xlsx to populate rather than building from scratch, or when GL balances must be mapped to specific month-ending columns (E, H, K, N).
---

# Template-Based Rollforward Builder

## When to use
- Task provides `template.xlsx` or similar starter file to populate
- Must preserve existing template structure, headers, or styling
- GL balances map to alternating columns (E, H, K, N for month endings)
- Building summary sheets that link to multiple detail sheet control rows

## Core workflow

### 1. Load and inspect template
```python
from openpyxl import load_workbook
wb = load_workbook('/root/template.xlsx')
print(f"Sheets: {wb.sheetnames}")
```
Check existing sheet names, headers, and any pre-positioned formulas.

### 2. Build detail sheets from template base
- Use template sheet as base, or create new sheets preserving template order
- Sheet order: Summary first, then detail sheets by account number ascending
- Preserve any existing headers/formatting from template rows 1-5

### 3. Map GL balances to month-ending columns
| Month | GL Column | Purpose |
|-------|-----------|---------|
| Month 1 | E | July ending |
| Month 2 | H | August ending |
| Month 3 | K | September ending |
| Month 4 | N | October ending |

GL Balance row writes **static values** to E, H, K, N—not formulas.

### 4. Build Summary sheet with aligned rows
CRITICAL: Label column (A) and formula column (B) must align to same row.

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

### 5. GL Balance column verification (CRITICAL)
- Detail sheet GL Balance is in columns E, H, K, N (monthly endings)
- Summary sheet links to GL Balance must use **column N**
- Cross-sheet reference: `='Sheet Name'!N{gl_row}` NOT `!O{gl_row}`

### 6. Multi-section summary layout
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

### 7. Validate before saving
- Run `scripts/verify_template_rollforward.py` if available
- Manual checks:
  - `grep "!O.*gl"` should return nothing (wrong column for GL)
  - `grep "!N.*gl"` should find GL Balance links
  - All cross-sheet refs with spaces use single quotes

## Anti-patterns (DO NOT DO)

| Wrong | Right | Why |
|-------|-------|-----|
| `='Sheet'!O{gl_row}` | `='Sheet'!N{gl_row}` | GL Balance lives in column N |
| Label in A12, formula in B13 | Same row | Misalignment breaks readability |
| `ws['A12'] = title; ws['A13'] = 'Period Totals'` | `ws['A11']=title; ws['A12']='Period Totals'` | Off-by-one errors |
| `B16 = B8+B13` | `B16 = B9+B14` | Wrong rows for GL Balance |
| Rebuilding template from scratch | Loading and modifying | Loses client formatting |

## Troubleshooting

**Verifier fails on GL Balance mismatch**
- Check detail sheet GL row writes to columns E, H, K, N
- Check summary links reference column N for GL Balance
- Verify row numbers in cross-sheet refs match actual control rows

**Summary sheet formulas show #REF!**
- Confirm sheet names match exactly (case-sensitive)
- Confirm sheet names with spaces wrapped in single quotes
- Check that detail sheets exist before summary formulas evaluated

**Off-by-one in row alignment**
- Use explicit row variables: `pt_row = data_end + 1`
- Print final layout: `for r in range(1,20): print(f"Row {r}: A={ws[f'A{r}'].value}, B={ws[f'B{r}'].value}")`

## Migration from scratch build
If familiar with `financial-rollforward-workbook` skill:
- Formulas identical for Period Totals, Ending Balance, Variance
- Difference: GL Balance column selection (N not O in cross-sheet refs)
- Difference: Template load vs `Workbook()` creation
- Add: Summary sheet row alignment discipline

## References
- `scripts/verify_template_rollforward.py` - Validation script
- `../financial-rollforward-workbook/scripts/quick_validate.py` - **BLOCKING pre-submit check** (MUST pass before test suite)
- Use `../financial-rollforward-workbook/references/formula-templates.md` for detail sheet formulas

## BLOCKING Pre-Submit Validation

**Run quick_validate.py BEFORE test suite:**

```bash
python ../financial-rollforward-workbook/scripts/quick_validate.py <workbook_path>
```

This catches the two most common fatal bugs:
1. Variance formula uses column N for BOTH operands
2. Ending Balance references Period Totals (not self)
