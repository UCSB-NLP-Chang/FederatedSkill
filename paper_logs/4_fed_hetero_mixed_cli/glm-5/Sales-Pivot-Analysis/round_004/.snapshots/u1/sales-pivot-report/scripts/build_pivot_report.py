#!/usr/bin/env python3
"""Template for building multi-sheet Excel pivot reports."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


def clean_dataframe(
    df: pd.DataFrame,
    str_cols: List[str] = None,
    title_case_cols: List[str] = None,
    upper_cols: List[str] = None,
    drop_duplicates_subset: List[str] = None
) -> pd.DataFrame:
    """Standard cleaning: trim strings, normalize case, drop duplicates."""
    df = df.copy()

    # Trim all string columns
    str_cols = str_cols or df.select_dtypes(include='object').columns.tolist()
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Title case for names/regions
    for col in (title_case_cols or []):
        if col in df.columns:
            df[col] = df[col].str.title()

    # Upper case for codes
    for col in (upper_cols or []):
        if col in df.columns:
            df[col] = df[col].str.upper()

    # Drop duplicates
    if drop_duplicates_subset:
        before = len(df)
        df = df.drop_duplicates(subset=drop_duplicates_subset)
        print(f"Dropped {before - len(df)} duplicate rows")

    return df


def validate_keys(
    df: pd.DataFrame,
    key_col: str,
    valid_keys: set,
    drop_invalid: bool = True
) -> pd.DataFrame:
    """Validate that all key values exist in reference set."""
    missing = df[key_col].isna().sum()
    unknown = set(df[key_col].dropna()) - valid_keys

    print(f"Missing {key_col}: {missing}")
    print(f"Unknown {key_col} values: {len(unknown)}")

    if drop_invalid:
        before = len(df)
        df = df[df[key_col].isin(valid_keys) & df[key_col].notna()]
        print(f"Dropped {before - len(df)} rows with invalid keys")

    return df


def create_pivot(
    df: pd.DataFrame,
    values: str,
    index: str,
    columns: Optional[str] = None,
    aggfunc: str = 'sum',
    fill_value: float = 0
) -> pd.DataFrame:
    """Create a pivot table with sensible defaults. Auto-flattens MultiIndex columns."""
    pivot = pd.pivot_table(
        df,
        values=values,
        index=index,
        columns=columns,
        aggfunc=aggfunc,
        fill_value=fill_value
    )

    # CRITICAL: Flatten column names if multi-index (prevents openpyxl ValueError)
    if isinstance(pivot.columns, pd.MultiIndex):
        pivot.columns = [' '.join(map(str, col)).strip() for col in pivot.columns]
    else:
        pivot.columns.name = None  # Remove the columns index name

    return pivot.reset_index()


def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns to prevent openpyxl ValueError."""
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[-1] if isinstance(c, tuple) else str(c) for c in df.columns]
    return df


def write_multi_sheet_excel(
    output_path: str,
    sheets: Dict[str, pd.DataFrame]
) -> None:
    """Write multiple dataframes to separate sheets in one Excel file.
    Automatically flattens MultiIndex columns before writing.
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, df in sheets.items():
            # Flatten before writing to prevent ValueError
            df_flat = flatten_columns(df)
            df_flat.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"Wrote sheet: {sheet_name} ({len(df_flat)} rows, {len(df_flat.columns)} cols)")
    print(f"Report saved to {output_path}")


if __name__ == '__main__':
    print("Import this module and use the helper functions.")
    print("Example: write_multi_sheet_excel('report.xlsx', {'Sheet1': df1, 'Sheet2': df2})")
