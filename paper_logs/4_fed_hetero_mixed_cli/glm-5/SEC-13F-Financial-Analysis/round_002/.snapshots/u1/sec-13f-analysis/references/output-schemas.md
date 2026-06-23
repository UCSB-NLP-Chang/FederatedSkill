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
