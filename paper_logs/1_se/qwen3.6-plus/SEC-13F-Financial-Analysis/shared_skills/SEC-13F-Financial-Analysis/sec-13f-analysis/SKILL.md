---
name: sec-13f-analysis
description: Analyze SEC 13F COVERPAGE and INFOTABLE TSV files to match fund managers, classify holdings, and compute portfolio metrics. Use when processing quarterly institutional investment manager filings.
---

# SEC 13F Filing Analysis

## Workflow
1. **Inspect Headers**: Always run `head -1 <file> | tr '\t' '\n'` first. Column names vary across datasets. Common variants:
   - Title: `TITLE`, `TITLEOFCLASS`
   - Value: `VALUE`, `VALUEUSD`
   - Shares: `SSHPRNAMT`, `SHARES`, `PRN AMT`
   - Manager: `FILINGMANAGER_NAME`, `MANAGER_NAME`
2. **Match Manager**:
   - Normalize names: lowercase, strip punctuation, remove common suffixes (`LLC`, `INC`, `LP`, `LTD`, `CO`, `CORP`, `LLP`).
   - **Step 1**: Try exact match after normalization.
   - **Step 2**: If no exact match, extract the most distinctive word(s) from the query (exclude generic financial terms listed below) and search for names containing those distinctive words.
   - **Step 3**: If still no match, the manager is **NOT FOUND**. Do not force a match. Report 0 holdings or empty strings as appropriate.
   - **NEVER use fuzzy matching** (Levenshtein, difflib, etc.) on full names. These match on shared generic terms and produce false positives.
3. **Generic Financial Terms to Exclude from Matching**:
   - These words appear in hundreds of fund names and must be ignored when computing distinctive matches:
   - `GLOBAL`, `MANAGEMENT`, `ASSET`, `CAPITAL`, `ADVISORS`, `ADVISORY`, `PARTNERS`, `ASSOCIATES`, `INVESTMENTS`, `WEALTH`, `FINANCIAL`, `GROUP`, `FUND`, `SERVICES`, `CORP`, `INC`, `LLC`, `LP`, `LTD`
   - Example: Query "Tiger Global" → distinctive word is "Tiger" (exclude "Global"). Query "Scion Asset Management" → distinctive word is "Scion" (exclude "Asset", "Management").
4. **Classify Holdings**:
   - The title column uses SEC-standard abbreviations.
   - **Equity/Stock indicators**: `COM`, `SHS`, `CL A`, `CL B`, `CL C`, `ORD`, `COM SHS`, `COMMON`, `CAP STK`, `SPONSORED ADS`, `TR UNIT`.
   - **Non-equity indicators**: `PFD`, `NOTE`, `DEB`, `BOND`, `ETF`, `RIGHT`, `WARR`, `ADS`, `PRF`.
   - Count a holding as stock-like if the title contains an equity indicator AND lacks a non-equity indicator.
   - Also check `PUTCALL` column: exclude rows where `PUTCALL` is `CALL` or `PUT`.
5. **Calculate Metrics & Verify Units**:
   - **Critical**: Verify `VALUE` unit before reporting. Sum `VALUE` for a known large fund (e.g., Vanguard, Renaissance). If the total is ~$10B–$100B, the column is in **dollars**. If ~$10M–$100M, it's in **thousands**.
   - **Do not blindly multiply by 1,000**. Apply the multiplier only if the magnitude check confirms thousands.
   - Filter by classification for stock AUM.
6. **Output**: Return JSON with exact keys requested. Validate counts against row iteration.

## Anti-Patterns
- ❌ Using Levenshtein distance or substring matching on generic terms → matches unrelated firms.
- ❌ Assuming column names are fixed → always inspect headers first.
- ❌ Blindly multiplying `VALUE` by 1,000 without magnitude verification → overreports AUM by 1000x.
- ❌ Assuming `TITLE` is human-readable → it is highly abbreviated and standardized.
- ❌ Forcing a match when the manager doesn't exist in the quarter → produces completely wrong results.

## Scripts & References
- Run `scripts/parse_13f.py` for robust TSV parsing, normalization, and classification. It automatically handles `TITLE`/`TITLEOFCLASS` and `VALUE`/`VALUEUSD` variants.
- See `references/13f-title-abbreviations.md` for a complete mapping of SEC title codes.