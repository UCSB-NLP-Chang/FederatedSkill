---
name: structured-data-diff
description: Compare two structured data snapshots to identify retired records, new records, and changed fields. Use when asked to diff, compare versions, find changes between datasets, or generate change reports across PDF tables, PDF text, Excel, CSV, or JSON sources. Common domains include medication inventories, school records, product catalogs, employee databases, server hardware, shipping container manifests, and university course catalogs. This is a documentation skill - read the SKILL.md and use the scripts directly, do not invoke as a Skill tool.
---

# Structured Data Diff

Compare two structured datasets (archive vs current) to produce a machine-readable diff with retired IDs and field-level changes.

## Quick Start

```bash
# If data is already in JSON with 'ID' field:
python3 scripts/diff_structured_data.py archive.json current.json output.json \
  --deleted-key deleted_medications --changed-key modified_medications

# Or use inline Python for full control over extraction and output format
```

## Common Source Patterns

| Archive Format | Current Format | Extraction Approach |
|---------------|----------------|---------------------|
| PDF (tables) | Excel/CSV | `pdfplumber` → JSON → `diff_structured_data.py` |
| PDF (structured text) | Excel/CSV | Regex parse text → JSON → compare |
| Excel | Excel | `pd.read_excel()` both → JSON → `diff_structured_data.py` |
| CSV | CSV | `pd.read_csv()` both → compare |
| JSON | JSON | Direct comparison |

**For PDF archive + Excel current (common pattern):**
1. Try `pdfplumber` table extraction first (see `references/pdf_extraction_patterns.md`)
2. If tables fail or PDF is text-based, use regex parsing (see `references/pdf_text_parsing.md`)
3. Extract Excel with `pd.read_excel()` (see `references/excel_extraction_patterns.md`)
4. Normalize both to JSON, run `diff_structured_data.py`

## Workflow

1. **Extract both datasets to a common format** (list of dicts with consistent keys)
   - **PDF tables**: Use `pdfplumber` (see `references/pdf_extraction_patterns.md`)
   - **PDF structured text**: Use regex patterns (see `references/pdf_text_parsing.md`)
   - **Excel**: Use `pd.read_excel()` (see `references/excel_extraction_patterns.md`)
   - **CSV**: `pd.read_csv()`
   - **JSON**: Parse directly

2. **Normalize for comparison**
   - Ensure both datasets have the same primary key field (usually `ID` or `id`)
   - Convert to dict keyed by ID: `{row['ID']: row for row in data}`
   - **Preserve numeric types**: Use `json.loads(df.to_json(orient='records'))` to avoid pandas float conversion

3. **Detect changes**
   - Retired: IDs in archive but not in current
   - New: IDs in current but not in archive (include if task asks)
   - Changed: IDs in both where any field differs

4. **Output with domain-appropriate field names**

   | Domain | Deleted Key | Changed Key |
   |--------|-------------|-------------|
   | Medications/hospital inventory | `deleted_medications` | `modified_medications` |
   | Schools/education | `retired_school_ids` | `changed_schools` |
   | University courses | `removed_courses` | `revised_courses` |
   | Products/e-commerce | `retired_product_ids` | `changed_products` |
   | Servers/hardware | `decommissioned_servers` | `updated_servers` |
   | Employees/HR | `terminated_employee_ids` | `changed_employees` |
   | Shipping/containers | `missing_containers` | `changed_containers` |
   | Generic services | `retired_service_ids` | `changed_services` |

   Output format:
   ```json
   {
     "deleted_medications": ["MED00012", "MED00044"],
     "modified_medications": [
       {"id": "MED00017", "field": "StockUnits", "old_value": 213, "new_value": 195}
     ]
   }
   ```
   - Sort deleted IDs alphabetically
   - Sort changes by `id`, then `field`
   - Preserve numeric types (integers as ints, not floats)

## Scripts

Use `scripts/diff_structured_data.py` when datasets are already extracted as JSON files:

```bash
# Default output keys (retired_service_ids, changed_services)
python3 diff_structured_data.py archive.json current.json output.json

# Custom output keys for specific domains
python3 diff_structured_data.py archive.json current.json output.json \
  --deleted-key deleted_medications \
  --changed-key modified_medications
```

**To use with PDF/Excel sources:**
1. Extract PDF tables to JSON using patterns in `references/pdf_extraction_patterns.md`
2. Extract PDF structured text using patterns in `references/pdf_text_parsing.md`
3. Extract Excel to JSON using patterns in `references/excel_extraction_patterns.md`
4. Run script with appropriate `--deleted-key` and `--changed-key`

## Anti-Patterns

- **Do not use `Read` tool on binary Excel files** - fails. Use pandas.
- **Do not use `Read` tool on PDFs expecting table extraction** - returns unstructured text or fails. Use `pdfplumber`.
- **Do not parse PDF tables with regex** - use `pdfplumber.extract_tables()` for reliable structured extraction.
- **Do not assume PDF contains extractable tables** - if `extract_tables()` returns empty, the data may be embedded as structured text; switch to regex parsing.
- **Do not hardcode generic `service_ids` naming** - match the domain terminology in the task (medications, schools, products, containers, courses, etc.).
- **Do not invoke this skill via the `Skill` tool** - this is documentation. Read SKILL.md and use scripts directly.
- Don't assume field names match exactly between versions - normalize case/spaces if needed.
- Don't include unchanged fields in output.
- Don't let pandas auto-convert integers to floats.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Read` fails on Excel | Switch to pandas: `pd.read_excel()` |
| `Read` fails on PDF or returns unstructured text | Use `pdfplumber` to extract tables |
| PDF extraction returns empty/garbled tables | Check `page.extract_tables()` vs `page.extract_text()`; see `references/pdf_extraction_patterns.md` |
| PDF has structured data but `extract_tables()` is empty | Data is likely in text format; use regex parsing per `references/pdf_text_parsing.md` |
| Type errors / floats where ints expected | Use `json.loads(df.to_json())` or `df.astype({'col': 'Int64'})` |
| Numeric fields show `.0` suffix | Convert to int: `int(val) if val == int(val) else val` |
| Script fails "Row missing ID field" | Check case - script accepts 'ID' or 'id' |
| Verifier rejects output format | Check field names match domain terminology; verify sorting |

## When to Use Script vs Inline Code

| Scenario | Approach |
|----------|----------|
| JSON files ready, standard diff logic | Use script with `--deleted-key`/`--changed-key` |
| Need custom extraction from PDF/Excel first | Extract to JSON, then use script |
| Need to include new records (not just retired/changed) | Inline Python |
| Need custom change detection (ignore certain fields) | Inline Python |
| Complex field name mapping required | Inline Python or pre-process JSON |
| PDF has structured text (not tables) | Inline Python with regex, or extract to JSON then script |
