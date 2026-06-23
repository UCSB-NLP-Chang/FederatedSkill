---
name: sec-13f-issuer-rollup
description: Aggregate 13F holdings by issuer/CUSIP to identify top institutional managers for a specific quarter. Use when asked for "top holders of [Company]", "who owns [Ticker/CUSIP]", or "issuer ownership rollup".
---

# SEC 13F Issuer Ownership Rollup

Find the top institutional managers holding a specific issuer (identified by CUSIP) in a given quarter.

## Workflow

1. **Resolve CUSIP**: If only a company name or ticker is provided, determine the 9-digit CUSIP first.
2. **Run aggregation script**:
   ```bash
   python3 scripts/rollup_issuer.py <infotable.tsv> <coverpage.tsv> <cusip> [top_n]
   ```
   - The script filters `INFOTABLE.tsv` by CUSIP, aggregates `VALUE` by `ACCESSION_NUMBER`, and maps accessions to `FILINGMANAGER_NAME` using `COVERPAGE.tsv`.
   - Outputs JSON with `top_managers`, `top_accessions`, and `top_values`.
3. **Format output**: Wrap script output in the required task schema if specified.

## Anti-patterns & Pitfalls

- **Do NOT use fixed awk column indices for VALUE**: TSV column positions can shift or contain empty fields (e.g., FIGI column may be empty, pushing VALUE to a different index). Always use header-aware parsing (`csv.DictReader` or pandas).
- **VALUE scaling**: SEC 13F `VALUE` is typically reported in thousands of USD. If the task requires actual dollar amounts, multiply aggregated values by 1000. For ranking purposes, raw sums are sufficient.
- **Multiple rows per accession**: A single manager may hold the same CUSIP across multiple share classes or voting authorities. The script automatically aggregates these.
- **CUSIP padding**: Ensure CUSIP is exactly 9 characters. Pad with leading zeros if necessary (e.g., `12345678` -> `012345678`).

## Output Schema

```json
{
  "issuer_query": "palantir",
  "quarter": "2025-q3",
  "cusip": "69608A108",
  "top5_managers": ["VANGUARD GROUP INC", "BlackRock, Inc.", "..."],
  "top5_accessions": ["0000102909-25-000353", "..."]
}
```

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.