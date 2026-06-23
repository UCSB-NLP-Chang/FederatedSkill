# Alert Pack Output Schemas

## issuer_top_holders

```json
{
  "issuer_query": "palantir",
  "quarter": "2025-q3",
  "manager_names": ["VANGUARD GROUP INC", "BlackRock, Inc.", "STATE STREET CORP"]
}
```

- `manager_names`: Ordered by holdings value descending
- Length determined by `top_n` parameter in input alert

## fund_change (B3-Single Schema)

Standard comparison (both quarters matched):
```json
{
  "fund_query_current": "tiger global",
  "quarter_current": "2025-q3",
  "fund_query_baseline": "tiger global",
  "quarter_baseline": "2025-q2",
  "largest_buy_cusip": "594918104",
  "largest_sell_cusip": "02079K305"
}
```

Missing baseline (B3-Partial):
```json
{
  "fund_query_current": "tiger global",
  "quarter_current": "2025-q3",
  "fund_query_baseline": "tiger global",
  "quarter_baseline": "2025-q2",
  "largest_buy_cusip": "594918104",
  "largest_sell_cusip": "",
  "baseline_missing": true
}
```

**CRITICAL**: Use empty string `""` for missing sell, NOT null.

## fund_change (B3-Array Schema)

When task asks for "top N increased/decreased/new":
```json
{
  "fund_query_current": "bridgewater",
  "quarter_current": "2025-q3",
  "fund_query_baseline": "bridgewater",
  "quarter_baseline": "2025-q2",
  "top4_increased_cusips": ["512807306", "00724F101", "98138H101", "75734B100"],
  "top3_decreased_cusips": ["67066G104", "02079K305", "697435105"],
  "new_positions_top2": ["75734B100", "770700102"]
}
```

**Field name rules**:
- Array schema: Use `top4_increased_cusips`, `top3_decreased_cusips`, `new_positions_top2`
- Single schema: Use `largest_buy_cusip`, `largest_sell_cusip`
- Never mix field names between schemas