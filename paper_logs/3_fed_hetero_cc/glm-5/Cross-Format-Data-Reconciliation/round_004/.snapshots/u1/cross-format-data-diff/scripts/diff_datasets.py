#!/usr/bin/env python3
"""
Compare two tabular datasets from different file formats and output a structured JSON diff.
Usage: python3 diff_datasets.py <old_file> <new_file> --id-col ID --output diff.json
"""
import argparse
import json
import sys
import os

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("Error: pandas not installed. Run: pip install pandas openpyxl", file=sys.stderr)
    sys.exit(1)


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy and pandas types."""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super().default(obj)


def safe_equal(a, b):
    """Compare values safely across string/numeric type boundaries.

    PDF extraction returns all cells as strings; Excel preserves native types.
    Direct != checks yield false positives. This normalizes before comparing.
    """
    try:
        return float(a) == float(b)
    except (ValueError, TypeError):
        return str(a).strip() == str(b).strip()


def load_data(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        return pd.read_csv(filepath)
    elif ext in ('.xlsx', '.xls'):
        return pd.read_excel(filepath)
    elif ext == '.json':
        return pd.read_json(filepath)
    elif ext == '.pdf':
        try:
            import pdfplumber
            tables = []
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table and len(table) > 1:
                        tables.append(pd.DataFrame(table[1:], columns=table[0]))
            if not tables:
                raise ValueError("No tables found in PDF")
            return pd.concat(tables, ignore_index=True)
        except ImportError:
            print("Error: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
            sys.exit(1)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def normalize_df(df, id_col):
    df.columns = df.columns.str.strip().str.lower()
    id_col = id_col.strip().lower()
    if id_col not in df.columns:
        raise ValueError(f"ID column '{id_col}' not found in {df.columns.tolist()}")
    df[id_col] = df[id_col].astype(str).str.strip()
    df = df.set_index(id_col)
    return df, id_col


def compare_datasets(old_df, new_df, id_col):
    old_ids = set(old_df.index)
    new_ids = set(new_df.index)

    retired = sorted(list(old_ids - new_ids))
    added = sorted(list(new_ids - old_ids))
    common = old_ids & new_ids

    changed = []
    for idx in sorted(common):
        old_row = old_df.loc[idx]
        new_row = new_df.loc[idx]
        for col in old_df.columns:
            old_val = old_row[col]
            new_val = new_row[col]
            try:
                if pd.isna(old_val) and pd.isna(new_val):
                    continue
                if not safe_equal(old_val, new_val):
                    changed.append({
                        "id": idx,
                        "field": col,
                        "old_value": None if pd.isna(old_val) else old_val,
                        "new_value": None if pd.isna(new_val) else new_val
                    })
            except Exception:
                if str(old_val) != str(new_val):
                    changed.append({
                        "id": idx,
                        "field": col,
                        "old_value": str(old_val),
                        "new_value": str(new_val)
                    })

    return {
        "retired_ids": retired,
        "added_ids": added,
        "changed_records": changed
    }


def main():
    parser = argparse.ArgumentParser(description="Diff two tabular datasets")
    parser.add_argument("old_file", help="Path to the old dataset")
    parser.add_argument("new_file", help="Path to the new dataset")
    parser.add_argument("--id-col", default="id", help="Primary key column name")
    parser.add_argument("--output", default="diff.json", help="Output JSON file path")
    args = parser.parse_args()

    old_df, id_col = normalize_df(load_data(args.old_file), args.id_col)
    new_df, _ = normalize_df(load_data(args.new_file), args.id_col)

    result = compare_datasets(old_df, new_df, id_col)

    with open(args.output, 'w') as f:
        json.dump(result, f, cls=NumpyEncoder, indent=2)
    print(f"Diff written to {args.output}")


if __name__ == "__main__":
    main()
