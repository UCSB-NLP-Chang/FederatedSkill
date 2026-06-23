#!/usr/bin/env python3
"""
Robust template for multi-sheet Excel pivot reports.
Adapt column names, file paths, and reconciliation rules per task.
"""
import pandas as pd
import numpy as np
import openpyxl
import re
import sys

def sanitize_pivot_headers(df):
    """
    Removes pandas/excel auto-generated prefixes like 'Sum of ', 'Count of ', 'Average of ',
    and suffixes like '_sum', '_count' from column names.
    Call this on EVERY pivot DataFrame before to_excel().
    """
    df.columns = [re.sub(r'^(Sum|Count|Mean|Average|Min|Max) of\s*', '', c) for c in df.columns]
    df.columns = [re.sub(r'_(sum|count|mean|average|min|max)$', '', c) for c in df.columns]
    return df

def run_report(transaction_paths, catalog_path, output_path):
    # 1. Load & Consolidate Multi-Source
    dfs = [pd.read_excel(p) for p in transaction_paths]
    df = pd.concat(dfs, ignore_index=True)
    
    # Load Catalog (PDF/Excel/CSV)
    if catalog_path.endswith('.pdf'):
        import pdfplumber
        with pdfplumber.open(catalog_path) as pdf:
            tables = pdf.pages[0].extract_tables()
            catalog = pd.DataFrame(tables[0][1:], columns=tables[0][0])
    else:
        catalog = pd.read_excel(catalog_path)
        
    # 2. Clean & Cast
    df["ID_KEY"] = df["ID_KEY"].astype(str).str.strip()
    catalog["ID_KEY"] = catalog["ID_KEY"].astype(str).str.strip()
    for col in ["QUANTITY", "UNIT_PRICE"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
    # 3. Reconcile
    initial_rows = len(df)
    df = df[df["QUANTITY"] > 0]
    print(f"Dropped {initial_rows - len(df)} invalid rows.")
    
    df = df.merge(catalog, on="ID_KEY", how="left", suffixes=("", "_cat"))
    print(f"Unmatched IDs: {df['UNIT_PRICE'].isna().sum()}")
    df = df.dropna(subset=["UNIT_PRICE"])
    
    # 4. Compute Metrics & Flags
    df["TOTAL_VALUE"] = df["QUANTITY"] * df["UNIT_PRICE"]
    df["STATUS_FLAG"] = np.where(df["QUANTITY"] <= df["REORDER_LEVEL"], "At Risk", "Healthy")
    
    # 5. Write
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="SourceData", index=False)
        
        # Example pivots with AUTOMATIC HEADER SANITIZATION
        pivot1 = df.groupby("CATEGORY")["TOTAL_VALUE"].sum().reset_index()
        pivot1 = sanitize_pivot_headers(pivot1)
        pivot1.to_excel(writer, sheet_name="Value by Category", index=False)
        
        pivot2 = df.groupby("CATEGORY")["TOTAL_VALUE"].mean().reset_index()
        pivot2 = sanitize_pivot_headers(pivot2)
        pivot2.to_excel(writer, sheet_name="Avg Value by Category", index=False)
        
        matrix = pd.crosstab(df["CATEGORY"], df["WAREHOUSE"], values=df["TOTAL_VALUE"], aggfunc="sum").reset_index()
        matrix.columns.name = None
        matrix = sanitize_pivot_headers(matrix)
        matrix.to_excel(writer, sheet_name="Category Warehouse Matrix", index=False)
        
    print(f"Report saved to {output_path}")
    verify_report(output_path)

def verify_report(output_path):
    """Read back and print headers/counts to catch verifier mismatches early."""
    xls = pd.ExcelFile(output_path)
    for sheet in xls.sheet_names:
        df = pd.read_excel(output_path, sheet_name=sheet)
        bad_cols = [c for c in df.columns if any(x in c for x in ["Sum of", "Count of", "Average of", "Mean of"])]
        if bad_cols:
            print(f"[WARN] {sheet} has default pandas names: {bad_cols}. Rename explicitly!")
        print(f"[VERIFY] {sheet}: {len(df)} rows, cols={list(df.columns)}, dtypes={df.dtypes.to_dict()}")

if __name__ == "__main__":
    print("Adapt this template to your specific file paths and column names.")
