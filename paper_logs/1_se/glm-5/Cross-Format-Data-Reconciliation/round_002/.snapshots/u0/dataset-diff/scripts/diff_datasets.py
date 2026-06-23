#!/usr/bin/env python3
"""Compare two datasets and generate a structured diff."""

import json
import argparse
import pandas as pd
import base64
import io
from pathlib import Path

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


def load_excel(path: str) -> list[dict]:
    """Load records from an Excel file."""
    df = pd.read_excel(path)
    return df.to_dict('records')


def load_csv(path: str) -> list[dict]:
    """Load records from a CSV file."""
    df = pd.read_csv(path)
    return df.to_dict('records')


def load_json(path: str) -> list[dict]:
    """Load records from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        # If wrapped in a key, try to extract the list
        for v in data.values():
            if isinstance(v, list):
                return v
    return data if isinstance(data, list) else [data]


def load_pdf(path: str) -> list[dict]:
    """Load records from a PDF file with tabular data."""
    if not PDF_SUPPORT:
        raise ImportError("pdfplumber is required for PDF support. Install with: pip install pdfplumber")
    
    records = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                # First row is header
                headers = [str(h).strip() if h else f'col_{i}' for i, h in enumerate(table[0])]
                for row in table[1:]:
                    if row and any(cell for cell in row):
                        record = {}
                        for i, cell in enumerate(row):
                            if i < len(headers):
                                record[headers[i]] = cell
                        if record:
                            records.append(record)
    return records


def load_pdf_from_base64(base64_content: str) -> list[dict]:
    """Load records from base64-encoded PDF content."""
    if not PDF_SUPPORT:
        raise ImportError("pdfplumber is required for PDF support. Install with: pip install pdfplumber")
    
    pdf_bytes = base64.b64decode(base64_content)
    records = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                headers = [str(h).strip() if h else f'col_{i}' for i, h in enumerate(table[0])]
                for row in table[1:]:
                    if row and any(cell for cell in row):
                        record = {}
                        for i, cell in enumerate(row):
                            if i < len(headers):
                                record[headers[i]] = cell
                        if record:
                            records.append(record)
    return records


def diff_datasets(old_records: list[dict], new_records: list[dict], key_field: str = 'id') -> dict:
    """
    Compare two datasets and return differences.
    
    Returns:
        dict with keys: retired_ids, new_ids, changed_records
    """
    old_by_key = {r[key_field]: r for r in old_records if key_field in r}
    new_by_key = {r[key_field]: r for r in new_records if key_field in r}
    
    old_keys = set(old_by_key.keys())
    new_keys = set(new_by_key.keys())
    
    retired_ids = sorted(old_keys - new_keys)
    new_ids = sorted(new_keys - old_keys)
    
    changed_records = []
    for shared_key in sorted(old_keys & new_keys):
        old_rec = old_by_key[shared_key]
        new_rec = new_by_key[shared_key]
        for field in set(old_rec.keys()) | set(new_rec.keys()):
            old_val = old_rec.get(field)
            new_val = new_rec.get(field)
            if old_val != new_val:
                changed_records.append({
                    'id': shared_key,
                    'field': field,
                    'old_value': old_val,
                    'new_value': new_val
                })
    
    return {
        'retired_ids': retired_ids,
        'new_ids': new_ids,
        'changed_records': changed_records
    }


def main():
    parser = argparse.ArgumentParser(description='Compare two datasets')
    parser.add_argument('old_file', help='Path to old/baseline file')
    parser.add_argument('new_file', help='Path to new/current file')
    parser.add_argument('--key', default='id', help='Primary key field name')
    parser.add_argument('--output', '-o', help='Output JSON file path')
    args = parser.parse_args()
    
    loaders = {
        '.xlsx': load_excel,
        '.xls': load_excel,
        '.csv': load_csv,
        '.json': load_json,
        '.pdf': load_pdf,
    }
    
    old_ext = Path(args.old_file).suffix.lower()
    new_ext = Path(args.new_file).suffix.lower()
    
    old_records = loaders.get(old_ext, load_json)(args.old_file)
    new_records = loaders.get(new_ext, load_json)(args.new_file)
    
    result = diff_datasets(old_records, new_records, args.key)
    
    output_json = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        print(f'Diff written to {args.output}')
    else:
        print(output_json)


if __name__ == '__main__':
    main()
