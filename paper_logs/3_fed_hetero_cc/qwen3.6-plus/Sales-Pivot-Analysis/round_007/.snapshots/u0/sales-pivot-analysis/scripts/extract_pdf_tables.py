#!/usr/bin/env python3
"""
Extract tables from PDF files using tabula-py or pdfplumber.
Call as: python3 extract_pdf_tables.py /path/to/pdf.pdf output.csv
"""

import sys
import pandas as pd

def extract_pdf_tables(pdf_path, output_csv=None):
    """Extract tables from PDF and return as DataFrame."""
    # Try pdfplumber first (no Java required)
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            tables = []
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    tables.append(table)
            if tables:
                # First table, convert to DataFrame
                df = pd.DataFrame(tables[0][1:], columns=tables[0][0])
                if output_csv:
                    df.to_csv(output_csv, index=False)
                    print(f"Saved to {output_csv}")
                return df
    except ImportError:
        pass
    except Exception as e:
        print(f"pdfplumber failed: {e}")

    # Fallback to tabula-py (requires Java)
    try:
        import tabula
        tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        if tables:
            df = tables[0]
            if output_csv:
                df.to_csv(output_csv, index=False)
                print(f"Saved to {output_csv}")
            return df
    except ImportError:
        print("Install: pip install tabula-py (requires Java)")
    except Exception as e:
        print(f"tabula failed: {e}")

    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_pdf_tables.py <pdf_path> [output.csv]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else None

    df = extract_pdf_tables(pdf_path, output_csv)
    if df is not None:
        print(f"Extracted {len(df)} rows, {len(df.columns)} columns")
        print(df.head(3))