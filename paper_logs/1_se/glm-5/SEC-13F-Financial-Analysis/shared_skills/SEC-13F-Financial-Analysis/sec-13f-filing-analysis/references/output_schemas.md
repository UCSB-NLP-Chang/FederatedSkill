# SEC 13F Output Schemas

## Cross-Quarter Reconciliation Output

Used when task requires fund comparison across quarters combined with issuer checks and snapshot analysis.

```json
{
  "comparison_pairs": [
    {
      "fund_query_current": "third point",
      "quarter_current": "2025-q3",
      "fund_query_baseline": "third point",
      "quarter_baseline": "2025-q2",
      "largest_buy_cusip": "655844108",
      "largest_sell_cusip": "219948106"
    },
    {
      "fund_query_current": "tiger global",
      "quarter_current": "2025-q3",
      "fund_query_baseline": "tiger global",
      "quarter_baseline": "2025-q2",
      "largest_buy_cusip": "",
      "largest_sell_cusip": ""
    }
  ],
  "issuer_checks": [
    {
      "issuer_query": "microsoft",
      "quarter": "2025-q3",
      "top2_manager_names": ["VANGUARD GROUP INC", "BlackRock, Inc."]
    }
  ],
  "snapshot_check": {
    "fund_query": "scion asset management",
    "quarter": "2025-q3",
    "stock_holdings": 0
  }
}
```

### Field Semantics

- **comparison_pairs**: Array of fund comparison objects
  - `largest_buy_cusip`: CUSIP with largest positive value change (Q3 - Q2). Empty string if fund not in baseline quarter.
  - `largest_sell_cusip`: CUSIP with largest negative value change. Empty string if fund not in baseline quarter.
  - Only positions held in BOTH quarters count as buys/sells. New positions are NOT buys.

- **issuer_checks**: Array of issuer ownership rollups
  - `top2_manager_names`: Top 2 managers by aggregated value for that issuer

- **snapshot_check**: Single fund snapshot
  - `stock_holdings`: Count of distinct stock CUSIPs held, or 0 if fund not found

### Handling Missing Data

- Fund not in baseline quarter: `largest_buy_cusip` and `largest_sell_cusip` are empty strings
- Fund not in current quarter: `stock_holdings` is 0
- Issuer not found: `top2_manager_names` is empty array

---

## Alert Pack Processing Output

Used when task provides an `alerts_input.json` file to process with deduplication.

```json
{
  "issuer_top_holders": [
    {
      "issuer_query": "palantir",
      "quarter": "2025-q3",
      "manager_names": ["VANGUARD GROUP INC", "BlackRock, Inc.", "STATE STREET CORP"]
    },
    {
      "issuer_query": "microsoft",
      "quarter": "2025-q3",
      "manager_names": ["VANGUARD GROUP INC", "BlackRock, Inc.", "JPMORGAN CHASE & CO"]
    }
  ],
  "fund_change": [
    {
      "fund_query_current": "tiger global",
      "quarter_current": "2025-q3",
      "fund_query_baseline": "tiger global",
      "quarter_baseline": "2025-q2",
      "largest_buy_cusip": "594918104"
    }
  ]
}
```

### Alert Types and Deduplication Keys

| Alert Type | Deduplication Key | Output Array Key |
|------------|-------------------|------------------|
| `issuer_top_holders` | `issuer_query` + `quarter` | `issuer_top_holders` |
| `fund_change` | `fund_query_current` + `quarter_current` | `fund_change` |
| `ignore_me` | N/A (excluded) | N/A |

### Processing Rules

1. **Deduplicate**: Remove duplicate alerts based on type + deduplication key
2. **Filter**: Exclude alert types that should be ignored (e.g., `ignore_me`)
3. **Compute**: Calculate values from 13F data rather than copying from input
4. **Order**: Preserve first-seen order of deduplicated alerts
5. **Format**: Group by alert type in output object

### Computing issuer_top_holders

1. Find CUSIP for issuer in INFOTABLE.tsv
2. Aggregate VALUE by ACCESSION_NUMBER for that CUSIP
3. Join to manager names via COVERPAGE.tsv
4. Return top N managers by total VALUE

### Computing fund_change

1. Find fund's accession number in current quarter COVERPAGE.tsv
2. Find fund's accession number in baseline quarter COVERPAGE.tsv (may not exist)
3. If fund not in baseline: largest buy = highest VALUE stock holding in current quarter
4. If fund in both: largest buy = CUSIP with largest positive VALUE change
