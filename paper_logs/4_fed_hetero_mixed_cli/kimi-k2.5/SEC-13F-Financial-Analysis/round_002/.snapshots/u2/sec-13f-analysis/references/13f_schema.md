# 13F Filing Schema

## COVERPAGE.tsv Columns

- `ACCESSION_NUMBER`: Unique filing identifier (format: `XXXXXXXX-XX-XXXXXX`). Used to join with INFOTABLE.
- `REPORTCALENDARORQUARTER`: Date string (e.g., `30-SEP-2025`). Filter by this for quarterly tasks.
- `FILINGMANAGER_NAME`: Manager name to match. Normalize before comparing.

## INFOTABLE.tsv Columns

- `ACCESSION_NUMBER`: Links to COVERPAGE.
- `NAMEOFISSUER`: Company name.
- `TITLEOFCLASS`: Security class. Critical for stock filtering.
- `CUSIP`: 9-character alphanumeric identifier.
- `VALUE`: Market value (typically in thousands). Sum for AUM.
- `SSHPRNAMT`: Share/Principal amount.
- `SSHPRNAMTTYPE`: "SH" for shares.

## Join Pattern

```python
manager = coverpage_row  # filtered by quarter and matched name
accession = manager['ACCESSION_NUMBER']
holdings = [h for h in infotable_rows if h['ACCESSION_NUMBER'] == accession]
```

## Data Type Handling

- VALUE and SSHPRNAMT may be floats — convert with `int(float(value))` for integer output.
- CUSIP may have leading zeros — preserve as string.
- Manager names have variations (LLC, Inc, Corp suffixes, spacing differences).
