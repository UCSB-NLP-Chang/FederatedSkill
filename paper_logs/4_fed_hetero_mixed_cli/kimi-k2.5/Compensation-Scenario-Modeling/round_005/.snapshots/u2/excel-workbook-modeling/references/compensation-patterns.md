# Compensation Model Patterns

Detailed patterns for faculty/compensation Excel models with tiered benefits, retirement calculations, and multi-year projections.

## Retirement Match with Salary Cap

Common pattern: Match percentage of compensation up to a cap based on income tier.

### WRONG Pattern (Logic Error)
```python
# Multiplying base pay by summer rate - business nonsense
f"=MIN(G{row}*K{row}*RetRate,RetCap*(Roster!J{row}+VLOOKUP(...)))"
# G{row} is quarterly base pay
# K{row} is summer session pay
# Multiplying them creates wrong value entirely
```

### CORRECT Pattern
```python
# First, identify what compensation qualifies for retirement match
# Typically: Base Pay + Department Stipend + Sabbatical Bonus

# Build sum of qualifying components
qualifying = f"G{row}+S{row}+O{row}"  # Base + Stipend + Sabbatical

# Apply match rate with cap
formula = (
    f"=MIN(({qualifying})*RetRate,"
    f"RetCap*(Roster!J{row}+"
    f"VLOOKUP(Roster!E{row},{{'Full Professor',StipFP;'Assoc Prof',StipAP;'Asst Prof',StipAsst;'Instructor',StipInst}},2,FALSE)))"
)
```

### Alternative: Per-Employee Type Rates
```python
# If different ranks have different match rates/caps
tiered_retirement = (
    f"=IF(Roster!E{row}='Full Professor',"
    f"MIN((G{row}+S{row})*RetRate_FP,RetCap_FP),"
    f"IF(Roster!E{row}='Assoc Prof',"
    f"MIN((G{row}+S{row})*RetRate_AP,RetCap_AP),0))"
)
```

## VLOOKUP with Named Ranges

When referencing assumption parameters via named ranges in VLOOKUP:

### Pattern 1: Inline Lookup Table
```python
stipend_formula = (
    f"=VLOOKUP(Roster!E{row},"
    f"{{'Full Professor',StipFP;"
    f"'Assoc Prof',StipAP;"
    f"'Asst Prof',StipAsst;"
    f"'Instructor',StipInst}},"
    f"2,FALSE)"
)
```

### Pattern 2: External Lookup Range
If Assumptions sheet has a lookup table:
```python
# Assumptions sheet setup
# A20:A23: Rank names, B20:B23: Stipend values
f"=VLOOKUP(Roster!E{row},Assumptions!$A$20:$B$23,2,FALSE)"
```

### Pattern 3: Department-Specific Multipliers
```python
dept_multiplier = (
    f"=VLOOKUP(Roster!F{row},"  # Department column
    f"{{'Philosophy',1.0;"
    f"'Mathematics',1.05;"
    f"'Engineering',1.1}},"
    f"2,FALSE)"
)
```

## Seniority-Based Pay Tiers

Common pattern: Additional pay based on years of service brackets.

### Pattern: Tiered Lookup with Named Ranges
```python
# Named ranges: Sr5to9, Sr10to14, Sr15to19, Sr20to24, Sr25up
seniority_bonus = (
    f"=IF(Roster!G{row}<5,0,"  # Less than 5 years: no bonus
    f"IF(Roster!G{row}<10,Sr5to9,"  # 5-9 years
    f"IF(Roster!G{row}<15,Sr10to14,"  # 10-14 years
    f"IF(Roster!G{row}<20,Sr15to19,"  # 15-19 years
    f"IF(Roster!G{row}<25,Sr20to24,Sr25up)))))"  # 20-24, 25+
)
```

### Alternative: Using MATCH/INDEX for cleaner formula
```python
# If years thresholds are in a column and rates in another
seniority_formula = (
    f"=IF(Roster!G{row}<5,0,"
    f"INDEX(SrRates,MATCH(Roster!G{row},SrThresholds,1)))"
)
```

## Service Year Projections

Critical for multi-year models: Future years must use formulas referencing prior years.

### Pattern: Increment via Formula
```python
# EE Calcs (Yr+1) sheet, column F (Years of Service)
# Reference the Current sheet, add 1
ws_yr1['F4'] = "='EE Calcs (Current)'!F4+1"

# EE Calcs (Yr+2) sheet
ws_yr2['F4'] = "='EE Calcs (Yr+1)'!F4+1"
```

### Common Error: Hardcoded Increment
```python
# WRONG - tests check for formula, not value
ws_yr1['F4'] = 23  # If current is 22
ws_yr2['F4'] = 24
```

## Sabbatical Eligibility and Bonus

Pattern: Eligible if sabbatical flag is true AND years divisible by cycle (e.g., 7 years).

```python
# Check eligibility and calculate bonus
sabbatical_formula = (
    f"=IF(AND(Roster!H{row}='TRUE',MOD(Roster!G{row},7)=0),"
    f"PrevailingWage*SabbPct/4,"  # Quarterly amount
    f"0)"
)
```

Note: `MOD(Roster!G{row},7)=0` checks if years is divisible by 7 (sabbatical every 7 years).

## Quarterly Distribution Pattern

Common pattern: Annual amount divided equally across 4 quarters.

```python
# Annual base pay -> 4 quarters
for q, col in enumerate(['G', 'H', 'I', 'J'], 1):
    ws[f'{col}{row}'] = f"=AnnualBase/4"

# Or with named range for quarterly calculation
ws['G4'] = "=Roster!J4/4*MAX(1,VLOOKUP(...))"  # Prevailing wage / 4 * multiplier
```

## Year-over-Year Growth Formulas

Summary sheet pattern: Calculate percentage growth between years.

### Pattern: Referencing TOTAL Row
```python
# Summary sheet structure
# Row 5-12: Components
# Row 13: TOTAL
# Row 14: Y/Y Growth

# Year 2 vs Year 1 growth (columns C=Year1, D=Year2)
ws['D14'] = "=D13/C13-1"  # (Year2 Total / Year1 Total) - 1

# Year 3 vs Year 2 growth
ws['E14'] = "=E13/D13-1"
```

### Common Error: Wrong Reference Row
```python
# WRONG: References header row instead of TOTAL row
ws['D14'] = "=D2/C2-1"  # Label row, not total

# WRONG: References component instead of total
ws['D14'] = "=D5/C5-1"  # Just Base Pay growth, not total
```

## Cross-Sheet Aggregation

Summary sheet pulling totals from calculation sheets:

```python
# Sum quarterly totals from EE Calcs sheet
# Row 79 is the aggregation row with SUM formulas
components = {
    'Base Pay': ['G', 'H', 'I', 'J'],  # Quarterly columns
    'Summer Pay': ['K', 'L', 'M', 'N'],
    'Stipend': ['S', 'T', 'U', 'V'],
}

# Build formula summing quarterly totals for one component
col_refs = [f"'EE Calcs (Current)'!{c}79" for c in ['G', 'H', 'I', 'J']]
formula = "=SUM(" + ",".join(col_refs) + ")"
ws['C5'] = formula  # Year 1 Base Pay Total
```

## Verification Checklist for Compensation Models

Before submitting:
- [ ] Retirement formulas don't multiply unrelated compensation types
- [ ] VLOOKUP ranges include all rank/department values
- [ ] Service year projections use formulas (`=Current!F4+1`), not hardcoded values
- [ ] Quarterly totals (row 79) use SUM formulas, not hardcoded sums
- [ ] Y/Y Growth references TOTAL row (e.g., row 13), not individual components
- [ ] Named ranges for tier values (Sr5to9, etc.) are defined and referenced correctly
- [ ] MOD() function for sabbatical cycle uses correct divisor (usually 7)
- [ ] All cross-sheet references use properly quoted sheet names

## Debugging Compensation Formulas

When values look wrong:

1. **Check unit consistency**: Are you mixing annual and quarterly amounts?
2. **Verify VLOOKUP exact match**: Using `FALSE` for exact match, not `TRUE`
3. **Inspect named range targets**: `print(wb.defined_names['RetRate'].attr_text)`
4. **Test with data_only=True**: See computed values vs formulas
   ```python
   wb_data = openpyxl.load_workbook(path, data_only=True)
   wb_formula = openpyxl.load_workbook(path, data_only=False)
   print(f"Formula: {wb_formula['EE Calcs']['G4'].value}")
   print(f"Value: {wb_data['EE Calcs']['G4'].value}")
   ```
5. **Trace formula dependencies**: Check if referenced cells contain #REF! or #NAME?
