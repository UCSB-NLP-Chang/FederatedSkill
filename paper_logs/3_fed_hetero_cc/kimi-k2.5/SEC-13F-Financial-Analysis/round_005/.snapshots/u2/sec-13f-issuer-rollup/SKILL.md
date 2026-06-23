---
name: sec-13f-issuer-rollup
description: Roll up 13F holdings by issuer to find top institutional holders. Use when given an issuer/company name (e.g., 'palantir', 'apple') and asked to find top managers, largest holders, ownership concentration, or 'who owns X'. Outputs CUSIP resolution, aggregated holdings by manager, and top N holders.
---

# SEC 13F Issuer Ownership Rollup

Given an issuer query, resolve to CUSIP, aggregate holdings across all 13F filers, and identify top institutional holders.

## Output Schema

```json
{
  "issuer_query": "palantir",
  "quarter": "2025-q3",
  "cusip": "69608A108",
  "top5_managers": ["VANGUARD GROUP INC", "BlackRock, Inc.", "STATE STREET CORP", "SUSQUEHANNA INTERNATIONAL GROUP, LLP", "GEODE CAPITAL MANAGEMENT, LLC"],
  "top5_accessions": ["0000102909-25-000353", "0002012383-25-002949", "0000093751-25-000651", "0001446194-25-000027", "0001214717-25-000016"]
}
```

## Workflow

### 1. Resolve Issuer to CUSIP

Search INFOTABLE.tsv for the issuer query:
```bash
grep -i "palantir" /root/2025-q3/INFOTABLE.tsv | head -20
```

- Extract the consistent CUSIP from matching rows
- Verify multiple rows share the same CUSIP (confirms correct issuer)
- Note: Same issuer may have multiple TITLEOFCLASS values (COM, CL A, etc.) — all share CUSIP

### 2. Aggregate Holdings by ACCESSION_NUMBER

Sum VALUE column (in thousands USD) for all rows with target CUSIP:
```bash
awk -F'\t' 'NR>1 && $5=="69608A108" {sum[$1]+=$7} END {for(acc in sum) print acc "\t" sum[acc]}' \
  /root/2025-q3/INFOTABLE.tsv | sort -t$'\t' -k2 -nr | head -5
```

- Field positions: $1=ACCESSION_NUMBER, $5=CUSIP, $7=VALUE
- Sort numerically descending by aggregated value
- Keep top N accessions as specified by task

### 3. Resolve ACCESSION_NUMBER to Manager Names

Join with COVERPAGE.tsv to get FILINGMANAGER_NAME:
```bash
awk -F'\t' 'NR==FNR{a[$1]=$2;next} $1 in a{print $1 "\t" a[$1]}' \
  <(awk -F'\t' 'NR>1 && $5=="CUSIP" {sum[$1]+=$7} END {for(acc in sum) print acc "\t" sum[acc]}' INFOTABLE.tsv | sort -k2 -nr | head -5) \
  <(awk -F'\t' 'NR>1 {print $1 "\t" $10}' COVERPAGE.tsv)
```

Or use the provided script: `scripts/issuer_rollup.py`

### 4. Format Output

- `cusip`: The resolved 9-character CUSIP
- `top5_managers`: Manager names ordered by holdings value (descending)
- `top5_accessions`: Corresponding ACCESSION_NUMBERs in same order
- Do NOT round VALUE figures — pass raw floats
- Multiply by 1000 for display only (filings report in thousands USD)

## Scripts

- `scripts/issuer_rollup.py <issuer_query> <infotable.tsv> <coverpage.tsv> [top_n]`: Full pipeline from query to ranked output

## Anti-patterns

- **Do NOT filter by NAMEOFISSUER alone** — issuer names vary ("PALANTIR TECHNOLOGIES INC", "PALANTIR TECHNOLOGIES INC CL A"). Use CUSIP as the stable identifier.
- **Do NOT assume one row per manager** — large managers may have multiple INFOTABLE rows for the same CUSIP (different share classes, accounts). Aggregate by ACCESSION_NUMBER first.
- **Do NOT forget VALUE scaling** — values are in thousands USD; multiply by 1000 for actual dollar amounts in display.
- **Do NOT sort managers alphabetically** — order must be by holdings value descending.

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(JSON, Excel, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: pass raw floats directly to output
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Known Invariants

- CUSIP is the only reliable issuer identifier across filings
- Same ACCESSION_NUMBER may have multiple rows for same CUSIP (different TITLEOFCLASS or voting authority) — sum them
- COVERPAGE.FILINGMANAGER_NAME is the canonical manager name for display
- VALUE field is numeric string, may contain decimals