#!/usr/bin/env python3
"""
Template for generating multi-sheet Excel reports from joined data sources.

Demonstrates:
- Joining transactional data with lookup/reference tables
- Calculated columns using vectorized pandas operations
- Pivot aggregations using pd.pivot_table() (NOT openpyxl pivot API)
- Multi-sheet Excel output with exact sheet/column names
"""

import pandas as pd
import sys


def normalize_key(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
    """Normalize join key for reliable merging."""
    df[key_col] = df[key_col].astype(str).str.strip()
    return df


def create_report(
    source_csv: str,
    lookup_csv: str,
    output_xlsx: str,
    source_key: str,
    lookup_key: str,
    derived_cols: dict,
    pivots_config: list,
    sheet_names: dict
):
    """
    Generate multi-sheet Excel report from joined data.

    Args:
        source_csv: Path to main transactional data CSV
        lookup_csv: Path to lookup/reference data CSV (extracted from PDF)
        output_xlsx: Path for output Excel file
        source_key: Column name in source_df for join
        lookup_key: Column name in lookup_df for join
        derived_cols: Dict mapping new column names to calculation expressions
        pivots_config: List of pivot specs (index, values, aggfunc, sheet_name)
        sheet_names: Dict mapping sheet roles to exact names from spec
    """
    # Load data
    df_source = pd.read_csv(source_csv)
    df_lookup = pd.read_csv(lookup_csv)

    # Normalize join keys
    df_source = normalize_key(df_source, source_key)
    df_lookup = normalize_key(df_lookup, lookup_key)

    # Join with suffixes to prevent duplicate columns
    df_joined = df_source.merge(
        df_lookup,
        left_on=source_key,
        right_on=lookup_key,
        how="left",
        suffixes=("_src", "_lk")
    )

    # Validate merge
    if len(df_joined) == 0:
        raise ValueError(f"Merge produced 0 rows. Check key alignment: {source_key} vs {lookup_key}")

    # Add derived columns
    for col_name, expr in derived_cols.items():
        df_joined[col_name] = expr(df_joined)

    # Write multi-sheet Excel
    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        # Source data sheet
        source_cols = list(df_source.columns) + [c for c in derived_cols.keys() if c not in df_source.columns]
        df_joined[source_cols].to_excel(
            writer,
            sheet_name=sheet_names.get("source", "SourceData"),
            index=False
        )

        # Pivot sheets
        for pivot_spec in pivots_config:
            pivot_df = pd.pivot_table(
                df_joined,
                index=pivot_spec["index"],
                values=pivot_spec["values"],
                columns=pivot_spec.get("columns"),
                aggfunc=pivot_spec["aggfunc"]
            ).reset_index()

            # Rename columns to match expected format
            if pivot_spec.get("columns"):
                pivot_df.columns = [pivot_spec["index"]] + [
                    f"{pivot_spec['values']}_{c}" for c in pivot_df.columns[1:]
                ]
            else:
                pivot_df.columns = [pivot_spec["index"], pivot_spec["values"]]

            pivot_df.to_excel(
                writer,
                sheet_name=pivot_spec["sheet_name"],
                index=False
            )

    print(f"Report created: {output_xlsx}")
    return output_xlsx


def verify_report(xlsx_path: str, expected_sheets: list = None):
    """Verify generated Excel file structure."""
    xl = pd.ExcelFile(xlsx_path)
    print(f"Sheets: {xl.sheet_names}")

    if expected_sheets:
        for s in expected_sheets:
            if s not in xl.sheet_names:
                print(f"WARNING: Missing expected sheet '{s}'")

    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        print(f"  {sheet}: {df.shape}")
        print(f"    Columns: {list(df.columns)}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python generate_compensation_report.py <source.csv> <lookup.csv> <output.xlsx>")
        print("\nExample pivots_config structure:")
        print([
            {"index": "DEPT_NAME", "values": "REVENUE", "aggfunc": "sum", "sheet_name": "Revenue by Dept"},
            {"index": "REGION", "values": "UNITS", "aggfunc": "sum", "sheet_name": "Units by Region"},
        ])
        sys.exit(1)

    # This is a template — adapt for actual task
    source_path, lookup_path, out_path = sys.argv[1:4]
    print(f"Source: {source_path}")
    print(f"Lookup: {lookup_path}")
    print(f"Output: {out_path}")