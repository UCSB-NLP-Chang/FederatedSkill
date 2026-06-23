# 13F Filing Schema & Classification Rules

## COVERPAGE.tsv Columns
- `ACCESSION_NUMBER`: Unique filing identifier. Used to join with INFOTABLE. Format: `XXXXXXXX-XX-XXXXXX`.
- `REPORTCALENDARORQUARTER`: Date string (e.g., `30-SEP-2025`). Filter by this for quarterly tasks.
- `FILINGMANAGER_NAME`: Manager name to match. Normalize before comparing.

## INFOTABLE.tsv Columns
- `ACCESSION_NUMBER`: Links to COVERPAGE.
- `NAMEOFISSUER`: Company name.
- `TITLEOFCLASS`: Security class. Critical for stock filtering — see classification rules below.
- `CUSIP`: Unique security identifier. Alphanumeric, may have leading zeros.
- `VALUE`: Market value. May be float (e.g., `3620781.0`). Use `float()` then `int()` if integer needed.
- `SSHPRNAMT`: Share/principal amount. May also be float.

## Stock Classification Logic

Use **tokenized matching** to avoid brand-name false positives (e.g., `ISHARES` contains "share" as substring but should NOT match):

### Include tokens (stock-like):
`common`, `com`, `ordinary`, `shares`, `shs`, `stock`, `class`, `cl`

### Exclude tokens (non-stock):
`bond`, `note`, `deb`, `etf`, `trust`, `fund`, `index`, `treas`, `muni`, `pfd`, `pref`, `adr`, `put`, `call`, `option`

### Rule:
`has_include_token AND NOT has_exclude_token`

### Examples:
- `COMMON STOCK` → tokens: `['common', 'stock']` → included ✓
- `COM` → tokens: `['com']` → included ✓ (abbreviation for Common Stock)
- `SHS` → tokens: `['shs']` → included ✓ (abbreviation for Shares)
- `CL A` → tokens: `['cl', 'a']` → included ✓ (Class A)
- `ISHARES NEW` → tokens: `['ishares', 'new']` → no include token → excluded ✓
- `U.S. REAL ES ETF` → tokens contain `etf` → excluded ✓
- `CORE S&P500 ETF` → tokens contain `etf` → excluded ✓
