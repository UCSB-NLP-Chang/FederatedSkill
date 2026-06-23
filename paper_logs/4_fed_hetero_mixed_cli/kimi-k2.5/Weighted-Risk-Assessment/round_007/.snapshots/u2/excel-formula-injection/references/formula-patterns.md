# Excel Formula Patterns

## INDEX/MATCH 2D Lookup

Use when looking up values from a table using row and column identifiers.

```excel
=INDEX(Data!$H$21:$L$38,MATCH(D12,Data!$D$21:$D$38,0),MATCH(H$10,Data!$H$4:$L$4,0))
```

**Components:**
- `INDEX(array, row_num, col_num)`: Returns value at intersection
- `MATCH(lookup_value, lookup_array, match_type)`: 
  - `0` = exact match (required for text codes)
  - `1` = approximate (for sorted numeric ranges)
  - `-1` = approximate descending

**Reference Types:**
- Absolute (`$A$1`): Use for table arrays and headers that don't change when copying
- Mixed (`A$1`, `$A1`): Use when copying across rows or down columns
- Relative (`A1`): Use when formula should adjust relative to position

## Cross-Sheet References

```excel
=SheetName!A1
='Sheet Name With Spaces'!A1
=Data!$H$21:$L$38
```

**Rules:**
- Sheet names with spaces or special characters must be single-quoted
- Exclamation mark `!` separates sheet name from cell reference
- openpyxl preserves sheet names exactly as written

## Statistical Functions

### Central Tendency
```excel
=AVERAGE(H35:H40)
=MEDIAN(H35:H40)
```

### Dispersion
```excel
=MIN(H35:H40)
=MAX(H35:H40)
=PERCENTILE.INC(H35:H40,0.25)  ' 25th percentile
=PERCENTILE.INC(H35:H40,0.75)  ' 75th percentile
```

### Weighted Calculations
```excel
=SUMPRODUCT(H35:H40,H26:H31)/SUM(H26:H31)
```
- Multiplies arrays element-wise, sums result
- Divide by sum of weights to get weighted average

## Weighted Mean Reference Patterns

When creating weighted mean formulas that copy across columns, carefully consider whether weights should be fixed or vary:

### Pattern 1: Weights Vary by Column (e.g., Year-Specific)
```excel
H50: =SUMPRODUCT(H$35:H$40,H26:H31)/SUM(H26:H31)
```
- Values: `H$35:H$40` - row locked, column relative (adjusts when copied)
- Weights: `H26:H31` - fully relative (both row and column adjust)
- When copied to I50: `=SUMPRODUCT(I$35:I$40,I26:I31)/SUM(I26:I31)`

### Pattern 2: Weights Fixed to Single Column
```excel
H50: =SUMPRODUCT(H$35:H$40,$H$26:$H$31)/SUM($H$26:$H$31)
```
- Weights: `$H$26:$H$31` - fully absolute (never changes)
- When copied to I50: `=SUMPRODUCT(I$35:I$40,$H$26:$H$31)/SUM($H$26:$H$31)`

### Decision Checklist

Before writing weighted mean formulas:
1. **Identify weight source**: Where is the weight data located?
2. **Check weight dimensions**: Does weight data exist for each column (year) or just one column?
3. **Match reference style**: 
   - If weights vary by column → use relative column reference (no `$` before column)
   - If weights are fixed → use absolute column reference (`$` before column)
4. **Verify with sample**: Write formula in first cell, then check what it becomes when copied

## Common Errors

| Error | Meaning | Fix |
|-------|---------|-----|
| #N/A | MATCH didn't find value | Check exact match flag (0) and lookup values exist |
| #REF! | Invalid reference | Verify sheet names and ranges exist |
| #VALUE! | Wrong argument type | Ensure ranges same size for SUMPRODUCT |
| #DIV/0! | Division by zero | Add IF check: `IF(SUM(...)=0,0,...)` |
| Wrong weighted mean across columns | Weight reference style incorrect | Check if weights should vary by column; adjust `$` in reference |