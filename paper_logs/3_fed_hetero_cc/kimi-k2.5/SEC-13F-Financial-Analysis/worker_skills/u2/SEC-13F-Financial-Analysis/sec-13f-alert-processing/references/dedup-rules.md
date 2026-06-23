# Alert Deduplication Rules

## Deduplication Keys by Type

| Alert Type | Deduplication Key | Example |
|------------|-------------------|---------|
| `issuer_top_holders` | `(type, issuer_query, quarter)` | `(issuer_top_holders, palantir, 2025-q3)` |
| `fund_change` | `(type, fund_query, quarter_current, quarter_baseline)` | `(fund_change, tiger global, 2025-q3, 2025-q2)` |
| `fund_holdings` | `(type, fund_query, quarter)` | `(fund_holdings, bridgewater, 2025-q3)` |
| `ignore_me` | N/A (filtered out) | — |

## Processing Order

1. Filter: Remove all `ignore_me` alerts
2. Deduplicate: Keep first occurrence of each key
3. Group: Organize by alert type for output
4. Process: Route each alert to appropriate skill

## Output Aggregation

Results are grouped by alert type in final JSON:
```json
{
  "issuer_top_holders": [...],
  "fund_change": [...],
  "fund_holdings": [...]
}
```

Types with no valid alerts after deduplication are omitted or empty arrays.