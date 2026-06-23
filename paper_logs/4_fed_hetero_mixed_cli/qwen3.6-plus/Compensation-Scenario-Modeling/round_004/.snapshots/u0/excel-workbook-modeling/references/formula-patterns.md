# Formula Patterns and Escaping Guide

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
# Excel formula: =IF(B4="Principal",D4,0)
# Python: Use single quotes around whole string
ws['F4'] = '=IF(B4="Principal",D4,0)'

# Or if using variables
role = "Principal"
ws['F4'] = f'=IF(B4="{role}",D4,0)'  # Double quotes inside okay here
```

### Pattern 4: SUMPRODUCT with conditions
```python
# Correct syntax for cross-sheet ranges
formula = "=SUMPRODUCT((Roster!$D$5:$D$107<>\"\")*(Roster!$D$5:$D$107)*13)"
ws['A1'] = formula
```

## Named Ranges (Modern API)

```python
from openpyxl.workbook.defined_name import DefinedName

# Workbook-scoped named range
dn = DefinedName(name='MWS_Current', attr_text='Assumptions!$E$5')
wb.defined_names.add(dn)

# Verify iteration (safe across openpyxl versions)
for dn in wb.defined_names:
    print(dn.name if hasattr(dn, 'name') else dn)
```

## Common Formula Templates

### Orchestra/Compensation Model Patterns
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

## Common Pitfalls

| Pitfall | Wrong | Right |
|---------|-------|-------|
| Unquoted sheet name with space | `EE Calcs!A1` | `'EE Calcs'!A1` |
| Backslash in f-string | `f"=IF(A1=\"x\",1,0)"` | `'="=IF(A1=""x"",1,0)"'` or build separately |
| Deprecated named range API | `wb.create_named_range(...)` | `DefinedName` + `wb.defined_names.add()` |
