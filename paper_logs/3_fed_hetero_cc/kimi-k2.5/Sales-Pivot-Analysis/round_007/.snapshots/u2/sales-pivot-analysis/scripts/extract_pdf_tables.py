#!/usr/bin/env python3
"""
Extract tables from PDF files using tabula-py, camelot, or pdfplumber.
Returns pandas DataFrames for downstream processing.

Usage:
    python extract_pdf_tables.py /path/to/input.pdf [--method tabula|camelot|pdfplumber] [--pages all|1,2,3]
"""

import sys
import argparse
import pandas as pd


def extract_with_tabula(pdf_path: str, pages: str = "all") -> list:
    """Extract tables using tabula-py. Requires Java runtime."""
    try:
        import tabula
        tables = tabula.read_pdf(pdf_path, pages=pages, multiple_tables=True)
        return tables
    except ImportError:
        raise ImportError("tabula-py not installed. Run: pip install tabula-py")
    except Exception as e:
        raise RuntimeError(f"tabula extraction failed: {e}")


def extract_with_camelot(pdf_path: str, pages: str = "all") -> list:
    """Extract tables using camelot-py. More robust for complex/merged cells."""
    try:
        import camelot
        tables = camelot.read_pdf(pdf_path, pages=pages)
        return [t.df for t in tables]
    except ImportError:
        raise ImportError("camelot not installed. Run: pip install camelot-py[cv]")
    except Exception as e:
        raise RuntimeError(f"camelot extraction failed: {e}")


def extract_with_pdfplumber(pdf_path: str, pages: str = "all") -> list:
    """Extract tables using pdfplumber. No Java dependency."""
    try:
        import pdfplumber
        dfs = []
        page_nums = pages if pages == "all" else [int(p) for p in pages.split(",")]
        with pdfplumber.open(pdf_path) as pdf:
            for idx, page in enumerate(pdf.pages):
                if pages != "all" and idx + 1 not in page_nums:
                    continue
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        dfs.append(df)
        return dfs
    except ImportError:
        raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")
    except Exception as e:
        raise RuntimeError(f"pdfplumber extraction failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Extract tables from PDF")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("--method", choices=["tabula", "camelot", "pdfplumber"], default="tabula")
    parser.add_argument("--pages", default="all", help="Page numbers: 'all' or '1,2,3'")
    parser.add_argument("--output", help="Output CSV path for first table (optional)")
    args = parser.parse_args()

    if args.method == "tabula":
        tables = extract_with_tabula(args.pdf_path, args.pages)
    elif args.method == "camelot":
        tables = extract_with_camelot(args.pdf_path, args.pages)
    else:
        tables = extract_with_pdfplumber(args.pdf_path, args.pages)

    print(f"Extracted {len(tables)} table(s)")
    for i, df in enumerate(tables):
        print(f"\n--- Table {i} ---")
        print(f"Shape: {df.shape}")
        print(df.head())
        if args.output and i == 0:
            df.to_csv(args.output, index=False)
            print(f"Saved to {args.output}")

    return tables


if __name__ == "__main__":
    main()