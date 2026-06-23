# Output Schemas

## Holdings Analysis (Default)

Use for: Top CUSIPs, holdings lists, manager AUM extraction.

```json
{
  "manager": "Manager Name LLC",
  "total_aum": 12345678.9,
  "stock_aum": 9876543.2,
  "stock_holdings_count": 45,
  "top_cusips": ["037833100", "02079K305", "594918104"]
}
```

**Null response** (manager not found):
```json
{
  "manager": null,
  "error": "No match found for 'Query Name' in 30-SEP-2025",
  "total_aum": null,
  "stock_aum": null,
  "stock_holdings_count": null,
  "top_cusips": []
}
```

## Class Breakdown Analysis

Use for: Security class distribution, TITLEOFCLASS aggregation.

```json
{
  "manager": "Manager Name LLC",
  "aum_total": 12345678.9,
  "stock_row_count": 45,
  "stock_cusip_count": 40,
  "top_class_labels": ["COM", "CLASS A", "SHS"],
  "top_class_counts": [20, 15, 10]
}
```

**Null response**: All numeric fields `null`, arrays empty.

## Shift Screening Analysis (Cross-Quarter)

Use for: Quarter-over-quarter comparison, fund shift screening.

```json
{
  "manager": "Manager Name LLC",
  "fund_query_current": "query name",
  "quarter_current": "30-SEP-2025",
  "fund_query_baseline": "query name", 
  "quarter_baseline": "30-JUN-2025",
  "current_holdings_count": 972,
  "baseline_holdings_count": 548,
  "top4_increased_cusips": ["512807306", "00724F101", "98138H101", "57636Q104"],
  "top3_decreased_cusips": ["67066G104", "02079K305", "78463V107"],
  "new_positions_top2": ["75734B100", "770700102"]
}
```

**Logic Notes**:
- "Increased" and "New" are mutually exclusive
- CUSIPs case-sensitive
- Only stock-classified holdings considered

**Null response** (manager not found in one or both quarters):
```json
{
  "manager": null,
  "error": "Manager not found in current quarter 30-SEP-2025",
  "fund_query_current": "query name",
  "quarter_current": "30-SEP-2025",
  "top4_increased_cusips": [],
  "top3_decreased_cusips": [],
  "new_positions_top2": []
}
```

## Issuer Ownership Rollup

Use for: Finding managers holding specific securities (inverse lookup).

```json
{
  "issuer_query": "PALANTIR",
  "quarter": "30-SEP-2025",
  "cusip": "69608A108",
  "top_managers": ["VANGUARD GROUP INC", "BlackRock, Inc."],
  "top_accessions": ["0000102909-25-000353", "0002012383-25-002949"],
  "total_value": 12345678.9,
  "holdings_count": 150
}
```

**Field definitions**:
- `top_managers`: Distinct manager names sorted by total VALUE descending
- `top_accessions`: Filing identifiers for top VALUE holders
- `total_value`: Aggregate VALUE across all managers for this CUSIP
- `holdings_count`: Number of ACCESSION_NUMBER entries

**Error response** (CUSIP not found):
```json
{
  "issuer_query": "query",
  "error": "No CUSIP found for issuer 'query'",
  "cusip": null
}
```

## Cross-Quarter Reconciliation (Multi-Task)

Compound schema when task requires multiple analysis types.

```json
{
  "comparison_pairs": [
    {
      "fund_query": "third_point",
      "largest_buy_cusip": "655844108",
      "largest_sell_cusip": "219948106"
    },
    {
      "fund_query": "tiger_global",
      "largest_buy_cusip": null,
      "largest_sell_cusip": null
    }
  ],
  "issuer_checks": [
    {
      "issuer_query": "microsoft",
      "top_managers": ["VANGUARD GROUP INC", "BlackRock, Inc."],
      "top_accessions": ["0000102909-25-000353", "0002012383-25-002949"]
    }
  ],
  "snapshot_check": {
    "fund_query": "scion_asset_management",
    "q3_stock_positions": null
  }
}
```

**Null semantics**:
- `largest_buy_cusip: null` → Fund exists in at most one quarter (cannot calculate change)
- `q3_stock_positions: null` → Fund not found in Q3 data
- `top_managers: []` → Issuer not found or no holders in dataset
