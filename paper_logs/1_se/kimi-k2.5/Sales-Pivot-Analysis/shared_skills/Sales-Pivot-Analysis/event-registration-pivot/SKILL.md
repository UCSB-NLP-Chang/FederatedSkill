---
name: event-registration-pivot
description: Generate multi-sheet Excel reports from event registration data combining multiple sources (online registrations, walk-in CSV, event catalog). Enriches with SOURCE tracking, VIP flagging, price tiering, and produces standard event analytics by track, venue, registration type, and revenue. Use when tasks require consolidating registration data from heterogeneous formats (XLSX, CSV, PDF catalog), calculating revenue summaries, attendance counts, or cross-tabulated pivot matrices by event dimensions.
---

# Event Registration Pivot Report Generation

Create consolidated event registration reports by joining attendee records with event catalogs, computing revenue and attendance metrics, and generating multi-dimensional summaries.

## When to Use

- Combining registration data from multiple sources: online (Excel), walk-in (CSV), event details (PDF catalog)
- Computing derived fields: SOURCE (Online/Walk-in), IS_VIP (Yes/No), PRICE_TIER (Free/Budget/Standard/Premium)
- Generating revenue summaries by track, attendance by venue, registration cross-tabs
- Event analytics: registration counts, fee aggregation, capacity analysis

## Standard Workflow

### 1. Parse Event Catalog (PDF)

Extract structured event data from PDF catalogs using regex patterns:

```python
import re

# Read PDF text, then extract: EVENT_ID, EVENT_NAME, TRACK, VENUE, MAX_CAPACITY
pattern = r'(\d{4})\s+(.*?)\s+(AI/ML|Cloud Infrastructure|Data Science|Security|Web Development)\s+(Auditorium|Main Hall|Room [AB]|Workshop Lab)\s+(\d+)'
matches = re.findall(pattern, pdf_text)
catalog_df = pd.DataFrame(matches, columns=['EVENT_ID', 'EVENT_NAME', 'TRACK', 'VENUE', 'MAX_CAPACITY'])
catalog_df['MAX_CAPACITY'] = catalog_df['MAX_CAPACITY'].astype(int)
```

**Common PDF patterns:** See `references/pdf-catalog-patterns.md` for regex variants.

### 2. Load Registration Sources

**Online registrations (XLSX):** Use pandas, NOT `Read` tool:
```python
online = pd.read_excel('/path/to/online_registrations.xlsx')
# Expected: REG_ID, EVENT_ID, ATTENDEE_NAME, REG_TYPE, AMOUNT_PAID
```

**Walk-in registrations (CSV):**
```python
walkin = pd.read_csv('/path/to/walkin_registrations.csv')
# Align columns to match online schema before combining
walkin = walkin.rename(columns={
    'walk_in_id': 'REG_ID',
    'event_code': 'EVENT_ID',
    'guest_name': 'ATTENDEE_NAME',
    'registration_type': 'REG_TYPE',
    'fee_paid': 'AMOUNT_PAID'
})
walkin['REG_ID'] = walkin['REG_ID'].astype(str)
```

### 3. Combine and Enrich

```python
# Tag source before combining
online['SOURCE'] = 'Online'
walkin['SOURCE'] = 'Walk-in'

# Concatenate
combined = pd.concat([online, walkin], ignore_index=True)

# Enrichment calculations
combined['IS_VIP'] = combined['REG_TYPE'].apply(lambda x: 'Yes' if x == 'VIP' else 'No')

def price_tier(amount):
    if amount == 0: return 'Free'
    elif amount < 150: return 'Budget'
    elif amount < 400: return 'Standard'
    else: return 'Premium'

combined['PRICE_TIER'] = combined['AMOUNT_PAID'].apply(price_tier)
```

### 4. Join with Catalog

```python
# Ensure EVENT_ID types match
combined['EVENT_ID'] = combined['EVENT_ID'].astype(str)
catalog_df['EVENT_ID'] = catalog_df['EVENT_ID'].astype(str)

# Left join - registrations may have invalid EVENT_IDs
merged = combined.merge(catalog_df, on='EVENT_ID', how='left')

# Verify and report unmatched
unmatched = merged[merged['TRACK'].isna()]['EVENT_ID'].nunique()
if unmatched > 0:
    print(f"WARNING: {unmatched} registrations with invalid EVENT_IDs (dropped)")
    merged = merged[merged['TRACK'].notna()]
```

### 5. Generate Pivot Summary Sheets

```python
with pd.ExcelWriter('/path/to/output.xlsx', engine='openpyxl') as writer:
    # Sheet 1: Full enriched data
    merged.to_excel(writer, sheet_name='SourceData', index=False)
    
    # Sheet 2: Revenue by Track
    rev_by_track = merged.groupby('TRACK')['AMOUNT_PAID'].sum().reset_index()
    rev_by_track.columns = ['TRACK', 'Total Revenue']
    rev_by_track.to_excel(writer, sheet_name='Revenue by Track', index=False)
    
    # Sheet 3: Attendance by Venue
    venue_count = merged.groupby('VENUE').size().reset_index(name='Registration Count')
    venue_count.to_excel(writer, sheet_name='Attendance by Venue', index=False)
    
    # Sheet 4: Track × Registration Type Matrix (revenue)
    matrix = merged.pivot_table(
        values='AMOUNT_PAID',
        index='TRACK',
        columns='REG_TYPE',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    matrix.to_excel(writer, sheet_name='Track RegType Matrix', index=False)
    
    # Sheet 5: Registration count by Track
    track_count = merged.groupby('TRACK').size().reset_index(name='Registration Count')
    track_count.to_excel(writer, sheet_name='Events by Track', index=False)
```

### 6. Verification

```python
xls = pd.ExcelFile('/path/to/output.xlsx')
print(f"Sheets: {xls.sheet_names}")

# Required sheets check
required = ['SourceData', 'Revenue by Track', 'Attendance by Venue',
            'Track RegType Matrix', 'Events by Track']
missing = [s for s in required if s not in xls.sheet_names]
assert not missing, f"Missing sheets: {missing}"

# Enrichment columns check
source = pd.read_excel(xls, sheet_name='SourceData')
required_cols = ['SOURCE', 'IS_VIP', 'PRICE_TIER']
missing_cols = [c for c in required_cols if c not in source.columns]
assert not missing_cols, f"Missing enrichment: {missing_cols}"

# Distribution checks
print(source['SOURCE'].value_counts())
print(source['IS_VIP'].value_counts())
print(source['PRICE_TIER'].value_counts())
```

## Common Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|--------------|--------------|------------------|
| Using `Read` tool on .xlsx | Binary file rejection | Use `pd.read_excel()` |
| Concatenating before adding SOURCE tag | Lose origin tracking | Add SOURCE column before `pd.concat()` |
| Integer EVENT_ID comparison | 8001 != "8001" type mismatch | Cast to string before join |
| Ignoring unmatched EVENT_IDs | Silent data quality issues | Report count, filter or investigate |
| Hardcoding price tier thresholds | Brittle to fee changes | Use parameterized function or reference file |
| Default `index=True` in to_excel | Adds unwanted index | Always `index=False` |

## Troubleshooting

**PDF catalog parsing fails**
- Try `pdfplumber` for table extraction if text extraction is garbled
- Check for multi-column layouts that confuse line-based extraction
- See `references/pdf-catalog-patterns.md` for regex variants

**EVENT_ID join produces unexpected matches**
- Verify types: `df['EVENT_ID'].dtype` should match across frames
- Check for whitespace: `strip()` before join
- Look for leading zeros or formatting differences

**Price tier distribution unexpected**
- Review actual fee ranges in data: `df['AMOUNT_PAID'].describe()`
- Check for currency formatting ($ prefix) that prevents numeric conversion
- Adjust tier thresholds if fee structure changed

**Verifier fails on sheet names or columns**
- Sheet names are case-sensitive and space-sensitive
- Common issues: "RegType" vs "Registration Type", "Events by Track" vs "Events By Track"
- Verify exact column names in pivot tables match expected schema

## References

- `references/pdf-catalog-patterns.md` — Regex patterns for event catalog extraction
- `references/price-tier-patterns.md` — Tier calculation variants and threshold tuning

## Relationship to Other Skills

This skill specializes the `excel-report-generation` pattern for event/registration data. For general multi-source Excel reporting with inventory, quality control, or HR data, use `excel-report-generation` instead. For library or academic domains, use `library-circulation-pivot` or `student-performance-pivot`.
