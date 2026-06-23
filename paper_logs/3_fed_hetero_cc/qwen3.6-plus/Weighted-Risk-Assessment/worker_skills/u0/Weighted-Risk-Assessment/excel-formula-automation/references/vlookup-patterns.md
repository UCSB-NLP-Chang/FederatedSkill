# VLOOKUP with MATCH Column Selection

## Pattern for Dynamic Column Selection

When lookup data has year columns that need to align between Task and Data sheets:

```
=VLOOKUP($D{row},Data!$D$21:$L$38,MATCH({col}$10,Data!$H$4:$L$4,0)+4,FALSE)
```

### Component Breakdown

| Element | Purpose |
|---------|---------|
| `$D{row}` | Series code to find (column-absolute, row-relative) |
| `Data!$D$21:$L$38` | Full lookup table with series codes in column D |
| `MATCH({col}$10,Data!$H$4:$L$4,0)` | Find which year column (returns 1-5 for 2020-2024) |
| `+4` | Offset: D=1, E=2, F=3, G=4, so H=5=(1+4), I=6=(2+4), etc. |
| `FALSE` | Exact match required |

### Reference Locking

- `$D{row}`: Column D locked (series codes), row changes per entity
- `{col}$10`: Row 10 locked (year headers), column changes (H, I, J, K, L)
- `Data!$D$21:$L$38`: Fully absolute (table never moves)
- `Data!$H$4:$L$4`: Fully absolute (header row never moves)

### Alternative: INDEX/MATCH

If VLOOKUP column offset becomes confusing, use INDEX/MATCH/MATCH:

```python
f"=INDEX(Data!$H$21:$L$38,MATCH($D{row},Data!$D$21:$D$38,0),MATCH({col}$10,Data!$H$4:$L$4,0))"
```

Both patterns require `MATCH(...,0)` for exact match.
