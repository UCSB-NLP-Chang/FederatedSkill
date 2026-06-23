---
name: sec-13f-issuer-rollup
description: Find top institutional managers holding a specific issuer/stock in a given SEC 13F quarter. Use when tasks ask for "top holders of [company]", "who owns [issuer]", or require aggregating fund manager positions by CUSIP.
---

# SEC 13F Issuer-to-Manager Rollup

## Workflow
1. **Resolve CUSIP**: Search `INFOTABLE.tsv` for the issuer name in `NAMEOFISSUER`. Normalize query (lowercase, strip punctuation). Match rows, extract the canonical `CUSIP`. If multiple variants exist, pick the one with the highest total `VALUE`.
2. **Aggregate by Manager**: Filter `INFOTABLE.tsv` for the target quarter and resolved `CUSIP`. Sum `VALUE` grouped by `ACCESSION_NUMBER`.
   - Note: `VALUE` is reported in thousands of USD.
3. **Join with Coverpage**: Map each `ACCESSION_NUMBER` to `FILINGMANAGER_NAME` using `COVERPAGE.tsv`.
4. **Rank & Output**: Sort managers by aggregated `VALUE` descending. Return top N as requested. Multiply by 1,000 if full dollar amounts are required.

## Anti-Patterns
- ❌ Matching manager names first. This task requires issuer → CUSIP → manager.
- ❌ Ignoring multiple rows per manager for the same CUSIP. Always sum `VALUE` by `ACCESSION_NUMBER`.
- ❌ Assuming `NAMEOFISSUER` matches exactly. Use case-insensitive substring or normalized matching.
- ❌ Forgetting `VALUE` is in thousands when reporting absolute dollars.

## Scripts & References
- Run `scripts/issuer_rollup.py <infotable.tsv> <coverpage.tsv> <issuer_query> <top_n>` to automate CUSIP resolution, aggregation, joining, and JSON output. It handles column variants and value summation automatically.
