#!/usr/bin/env python3
"""
Reusable formula builders for common Excel patterns.
Import functions or copy patterns as needed.
"""

def index_match_2d(
    lookup_range: str,        # e.g., "Data!$H$21:$L$38"
    row_key_cell: str,        # e.g., "$D12" (column locked)
    row_key_range: str,       # e.g., "Data!$D$21:$D$38"
    col_header_cell: str,     # e.g., "H$10" (row locked)
    col_header_range: str,    # e.g., "Data!$H$21:$L$21"
) -> str:
    """Build INDEX/MATCH formula for two-dimensional lookup."""
    return f"=INDEX({lookup_range},MATCH({row_key_cell},{row_key_range},0),MATCH({col_header_cell},{col_header_range},0))"


def weighted_mean(values_range: str, weights_range: str) -> str:
    """SUMPRODUCT divided by SUM of weights."""
    return f"=SUMPRODUCT({values_range},{weights_range})/SUM({weights_range})"


def percentile_inc(data_range: str, percentile: float) -> str:
    """PERCENTILE.INC for Excel 2010+ compatibility. NEVER use plain PERCENTILE."""
    return f"=PERCENTILE.INC({data_range},{percentile})"


def quartile_inc(data_range: str, quartile: int) -> str:
    """QUARTILE.INC for Excel 2010+ compatibility. quartile: 1=25th, 2=50th, 3=75th, 4=100th."""
    return f"=QUARTILE.INC({data_range},{quartile})"


def stat_func(stat_name: str, data_range: str) -> str:
    """Build MIN/MAX/MEDIAN/AVERAGE formula. Range should be row-absolute: H$35:H$40."""
    return f"={stat_name}({data_range})"


def generate_year_formulas(base_formula: str, cols: list) -> dict:
    """Given base formula with {col} placeholder, generate formulas for each column."""
    return {col: base_formula.format(col=col) for col in cols}


if __name__ == "__main__":
    # Demonstration of correct patterns with $ locking
    lookup = index_match_2d(
        "Data!$H$21:$L$38",    # Fully absolute
        "$D12",                # Column locked, row dynamic
        "Data!$D$21:$D$38",    # Fully absolute
        "H$10",                # Row locked, column dynamic
        "Data!$H$21:$L$21"     # Fully absolute
    )
    print(f"Lookup: {lookup}")

    weighted = weighted_mean("H$35:H$40", "H$26:H$31")
    print(f"Weighted: {weighted}")

    p25 = percentile_inc("H$35:H$40", 0.25)
    print(f"25th percentile: {p25}")