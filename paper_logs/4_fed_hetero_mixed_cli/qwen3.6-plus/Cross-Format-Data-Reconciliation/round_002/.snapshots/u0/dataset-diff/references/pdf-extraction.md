# PDF Extraction Patterns

## Pre-requisites

If working in externally-managed Python environments (PEP 668):
```bash
pip install --break-system-packages pdfplumber pandas openpyxl
```

## From PDF (Archive/Baseline)

**Use `pdfplumber`**, not `csvkit in2csv` or `pdftotext`.

```python
import pdfplumber
import pandas as pd

with pdfplumber.open('/path/to/archive.pdf') as pdf:
    page = pdf.pages[0]
    table = page.extract_tables()[0]  # Assumes first table on first page
    df_old = pd.DataFrame(table[1:], columns=table[0])
```

**Anti-pattern**: `csvkit in2csv` requires Java dependencies for PDFs and typically fails with "direct conversion failed" or extracts unstructured text.

## From Excel (Current)

```python
df_new = pd.read_excel('/path/to/current.xlsx')
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `in2csv` fails on PDF | Missing Java deps or text-based PDF | Use `pdfplumber` instead |
| `pip install` fails with "externally managed" | PEP 668 restriction | Add `--break-system-packages` or use venv |
| Column mismatch after extraction | Hidden whitespace | `df.columns = df.columns.str.strip()` |
| False positives in comparison | Mixed types ("4.09" vs 4.09) | Normalize to numeric before comparing |
| Empty table extraction | Multi-page tables or images | Iterate all pages: `for page in pdf.pages:` |