# 13F Filing Schema & Classification Rules

## COVERPAGE.tsv Columns

- `ACCESSION_NUMBER`: Unique filing identifier. Used to join with INFOTABLE.
- `REPORTCALENDARORQUARTER`: Date string (e.g., `30-SEP-2025`). Filter by this for quarterly tasks.
- `FILINGMANAGER_NAME`: Manager name to match. Normalize before comparing.

## INFOTABLE.tsv Columns

- `ACCESSION_NUMBER`: Links to COVERPAGE.
- `NAMEOFISSUER`: Company name.
- `TITLEOFCLASS`: Security class. Critical for stock filtering.
- `CUSIP`: Unique security identifier.
- `VALUE`: Market value (typically in dollars). Sum for AUM.
- `SSHPRNAMT`: Share/Principal amount.

## Stock Classification Logic

Use tokenized matching to avoid brand-name false positives:

### Include tokens (stock-like):
`common`, `ordinary`, `share`, `stock`, `com`, `shs`, `cl`, `class`

### Exclude tokens (non-stock):
`bond`, `note`, `deb`, `etf`, `trust`, `fund`, `index`, `treas`, `muni`, `pfd`, `pref`, `adr`, `ads`, `put`, `call`, `option`, `warrant`, `right`

### Rule:
```python
tokens = title.lower().split()
has_include = any(t in include for t in tokens)
has_exclude = any(t in exclude for t in tokens)
return has_include and not has_exclude
```

### Examples:

| TITLEOFCLASS | Tokens | Verdict | Reason |
|--------------|--------|---------|--------|
| `COMMON STOCK` | `['common', 'stock']` | Stock | `common` in include |
| `COM` | `['com']` | Stock | `com` in include |
| `CL A` | `['cl', 'a']` | Stock | `cl` in include |
| `SHS` | `['shs']` | Stock | `shs` in include |
| `ISHARES NEW` | `['ishares', 'new']` | Non-stock | No include token (substring only) |
| `U.S. REAL ES ETF` | `['us', 'real', 'es', 'etf']` | Non-stock | `etf` in exclude |

## Manager Matching Thresholds

- Exact match: accept immediately
- Substring match: accept if query is substring of manager name or vice versa
- Fuzzy match: only accept if similarity ratio > 0.85
- If no confident match: return `null`, do NOT force closest Levenshtein match