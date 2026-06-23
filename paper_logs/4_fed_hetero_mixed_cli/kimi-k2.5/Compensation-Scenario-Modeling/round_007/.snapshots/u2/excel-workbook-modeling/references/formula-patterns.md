# Formula Patterns and Escaping Guide

## The += Trap (Critical)

**NEVER use `+=` in Excel formula strings.** Python's addition-assignment operator creates invalid Excel syntax.

```python
# WRONG - Excel cannot parse +=
f"=BaseSal/4*(1+=IF(Roster!G{row}<5,0,...))"
# Result: =BaseSal/4*(1+=IF(...))  <-- Excel ERROR

# CORRECT - simple addition only
f"=BaseSal/4*(1+IF(Roster!G{row}<5,0,...))"
# Result: =BaseSal/4*(1+IF(...))  <-- VALID
```

**Context**: This often happens when mentally translating "add 1 plus the result" into code. Type `+` not `+=`.

## Sheet Reference Rules

| Sheet Name | Reference Syntax |
|------------|-----------------|
| `Data` | `Data!A1` or `'Data'!A1` |
| `EE Calcs` | `'EE Calcs'!A1` (required quotes due to space) |
| `EE Calcs (Current)` | `'EE Calcs (Current)'!A1` (required due to spaces/parens) |

## Python String Building Patterns

### Pattern 1: Simple f-string (safe)
```python
col = 'I'
row = 107
ws['A1'] = f"='EE Calcs (Current)'!{col}{row}"
```

### Pattern 2: Building complex aggregation (avoids escape issues)
```python
columns = ['E', 'F', 'G', 'H']
parts = [f"'EE Calcs (Current)'!{c}107" for c in columns]
formula = f"={' + '.join(parts)}"
ws['A1'] = formula
```

### Pattern 3: IF statements with text (use double quotes inside)
```python
ws['F4'] = '=IF(B4="Principal",D4,0)'

# Or if using variables
role = "Principal"
ws['F4'] = f'=IF(B4="{role}",D4,0)'
```

### Pattern 4: SUMPRODUCT with conditions
```python
formula = "=SUMPRODUCT((Roster!$D$5:$D$107<>\"\")*(Roster!$D$5:$D$107)*13)"
ws['A1'] = formula
```

## Named Ranges (Modern API)

```python
from openpyxl.workbook.defined_name import DefinedName

# Workbook-scoped named range
dn = DefinedName(name='MWS_Current', attr_text='Assumptions!$E$5')
wb.defined_names.add(dn)
```

## Common Formula Templates

### Compensation Model Patterns
```python
# Y/Y Growth calculation
ws['A1'] = "=(C45/C35)-1"

# Tiered seniority pay lookup
ws['H4'] = '=IF(OR(C4="",C4<5),0,IF(C4<10,Assumptions!$E$13,IF(C4<15,Assumptions!$E$14,0)))'

# Principal pay calculation (reference EE Calcs total minus components)
ws['C31'] = "='EE Calcs (Current)'!I107-SUM(C29:C30)"

# Payroll tax with tier limits
ws['N4'] = '=IF(M4=0,0,IF(M4<=Assumptions!$E$19,M4*Assumptions!$E$18,Assumptions!$E$19*Assumptions!$E$18+(M4-Assumptions!$E$19)*Assumptions!$E$20))'
```

## Debugging Formula Construction

Always print sample formulas before bulk generation:

```python
# Build template
row = 5
formula = f"=BaseSal_Yr1/4*(1+IF(Roster!G{row}<5,0,Sr5to9_Yr1))"

# Verify
print(f"Formula: {formula}")
print(f"Starts with = : {formula.startswith('=')}")
print(f"Contains += : {'+=' in formula}")  # Should be False!

# Only proceed if valid
if not formula.startswith('=') or '+=' in formula:
    raise ValueError(f"Invalid formula: {formula}")

# Then bulk write
for row in range(5, 90):
    ws[f'K{row}'] = formula.replace('G5', f'G{row}')
```
