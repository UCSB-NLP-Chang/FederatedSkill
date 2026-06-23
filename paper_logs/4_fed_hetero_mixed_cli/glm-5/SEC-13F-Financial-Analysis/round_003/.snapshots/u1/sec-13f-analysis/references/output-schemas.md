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

**Field definitions:**
- `aum_total`: Sum of VALUE for all holdings (including non-stock)
- `stock_row_count`: Total rows classified as stock-like
- `stock_cusip_count`: Unique CUSIP values among stock rows
- `top_class_labels`: TITLEOFCLASS values sorted by frequency (descending)
- `top_class_counts`: Row counts corresponding to top_class_labels

**Null response** (manager not found):
```json
{
  "manager": null,
  "error": "No match found for 'Query Name' in 30-SEP-2025",
  "aum_total": null,
  "stock_row_count": null,
  "stock_cusip_count": null,
  "top_class_labels": [],
  "top_class_counts": []
}
```

**Important**: When manager is not found, return `null` for numeric fields, not `0`. Zero implies the manager exists but has no holdings, while null indicates the manager was not located in the dataset.

## Shift Screening Analysis (Cross-Quarter)

Use for: Quarter-over-quarter comparison, fund shift screening, identifying increased/decreased/new positions.

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

**Field definitions:**
- `manager`: Resolved manager name from current quarter filing
- `fund_query_*`: Original query strings used for matching
- `quarter_*`: Quarter dates in DD-MMM-YYYY format
- `*_holdings_count`: Count of unique stock-classified CUSIPs in each quarter
- `top4_increased_cusips`: CUSIPs with largest value increase (present in both quarters, sorted by Q_current - Q_baseline descending)
- `top3_decreased_cusips`: CUSIPs with largest value decrease (present in both quarters, sorted by Q_baseline - Q_current descending)
- `new_positions_top2`: CUSIPs present in current quarter but not in baseline, sorted by current value descending

**Logic Notes:**
- "Increased" and "New" are mutually exclusive categories
- Increased = position existed in both quarters and grew in value
- New = position did not exist in baseline quarter (CUSIP not found)
- CUSIPs are case-sensitive and preserved as-is from filings
- Only stock-classified holdings are considered

**Null response** (manager not found in one or both quarters):
```json
{
  "manager": null,
  "error": "Manager not found in current quarter 30-SEP-2025",
  "fund_query_current": "query name",
  "quarter_current": "30-SEP-2025",
  "fund_query_baseline": "query name",
  "quarter_baseline": "30-JUN-2025",
  "top4_increased_cusips": [],
  "top3_decreased_cusips": [],
  "new_positions_top2": []
}
```
