#!/usr/bin/env python3
"""
Template for data reconciliation and multi-sheet Excel report generation.
Adapt the data loading, merge keys, and aggregation logic to your task.
"""
import pandas as pd
import re
from io import StringIO

def parse_pdf_table(content, pattern, columns):
    """
    Parse structured table data from PDF text output.
    
    Args:
        content: Raw text from PDF
        pattern: Regex pattern with capture groups for each column
        columns: List of column names for the output DataFrame
    
    Returns:
        DataFrame with parsed data
    """
    matches = re.findall(pattern, content)
    df = pd.DataFrame(matches, columns=columns)
    # Convert numeric columns
    for col in df.columns:
        if 'ID' in col or 'YEAR' in col or 'COUNT' in col:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def load_reference_data():
    """Load reference/catalog data. Adapt source as needed (PDF, CSV, etc.)"""
    # Example: data extracted from PDF or other source
    catalog_data = """
    PRODUCT_ID,PRODUCT_NAME,CATEGORY,UNIT_COST,UNIT_PRICE
    1001,Product A,Category1,10.00,20.00
    """
    return pd.read_csv(StringIO(catalog_data.strip()))

def load_transactions(filepath):
    """Load transaction data from Excel file."""
    return pd.read_excel(filepath)

def normalize_text_fields(df, columns):
    """Normalize text columns to title case."""
    for col in columns:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].str.title()
    return df

def validate_and_clean(df, ref_df, id_col='PRODUCT_ID'):
    """Validate foreign keys and clean data. Returns cleaned df and stats."""
    original_count = len(df)
    
    # Drop missing IDs
    df = df.dropna(subset=[id_col])
    dropped_missing = original_count - len(df)
    
    # Validate against reference
    valid_ids = set(ref_df[id_col].unique())
    df = df[df[id_col].isin(valid_ids)]
    dropped_invalid = original_count - dropped_missing - len(df)
    
    # Drop duplicates
    df = df.drop_duplicates()
    
    stats = {
        'original': original_count,
        'dropped_missing_id': dropped_missing,
        'dropped_invalid_id': dropped_invalid,
        'final': len(df)
    }
    return df, stats

def merge_with_tracking(trans_df, ref_df, merge_keys, how='left'):
    """Merge dataframes and track column changes."""
    merged = trans_df.merge(ref_df, on=merge_keys, how=how, suffixes=('', '_ref'))
    
    # CRITICAL: Print columns after merge to verify names
    print(f'Columns after merge: {merged.columns.tolist()}')
    
    return merged

def add_grade_band(df, score_col='SCORE', grade_col='GRADE_BAND'):
    """Add letter grade band based on score."""
    def score_to_grade(score):
        if score >= 90: return 'A'
        elif score >= 80: return 'B'
        elif score >= 70: return 'C'
        elif score >= 60: return 'D'
        else: return 'F'
    
    df[grade_col] = df[score_col].apply(score_to_grade)
    return df

def add_weighted_column(df, value_col, weight_col, result_col):
    """Add weighted value column."""
    df[result_col] = df[value_col] * df[weight_col]
    return df

def add_flag_column(df, condition_col, threshold, flag_col, true_val='Yes', false_val='No'):
    """Add flag column based on threshold condition."""
    df[flag_col] = df[condition_col].apply(lambda x: true_val if x < threshold else false_val)
    return df

def create_pivot_report(output_path, source_df, pivot_specs):
    """
    Create multi-sheet Excel report.
    
    pivot_specs: list of dicts with keys:
        - sheet_name: str
        - df: DataFrame to write
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for spec in pivot_specs:
            spec['df'].to_excel(writer, sheet_name=spec['sheet_name'], index=False)
    print(f'Report saved to {output_path}')

if __name__ == '__main__':
    # Example usage - adapt to your data
    ref_df = load_reference_data()
    trans_df = load_transactions('/path/to/transactions.xlsx')
    
    # Normalize
    trans_df = normalize_text_fields(trans_df, ['REGION', 'MONTH', 'QUARTER'])
    
    # Validate
    trans_df, stats = validate_and_clean(trans_df, ref_df)
    print(f'Cleaning stats: {stats}')
    
    # Merge
    merged = merge_with_tracking(trans_df, ref_df, ['PRODUCT_ID'])
    
    # Verify columns before using
    assert 'QUANTITY' in merged.columns, 'QUANTITY column missing'
    assert 'UNIT_PRICE' in merged.columns or 'UNIT_PRICE_x' in merged.columns
    
    # Create report
    pivot_specs = [
        {'sheet_name': 'Summary', 'df': merged.groupby('CATEGORY').agg({'REVENUE': 'sum'}).reset_index()},
        {'sheet_name': 'SourceData', 'df': merged}
    ]
    create_pivot_report('/path/to/report.xlsx', merged, pivot_specs)
