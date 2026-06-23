#!/usr/bin/env python3
"""
Build Excel formulas with verified syntax. Use for complex nested conditions.
"""

def nested_if(conditions_results, default, indent=False):
    """
    Build nested IF formula with guaranteed parenthesis balance.
    
    Args:
        conditions_results: List of (condition, result) tuples, evaluated in order
        default: Value if no conditions match
        indent: If True, return multi-line formula (for debugging)
    
    Returns:
        Excel formula string starting with '='
    """
    formula = str(default)
    
    for condition, result in reversed(conditions_results):
        if indent:
            inner = formula.replace('\n', '\n  ')
            formula = f"IF({condition},\n  {result},\n  {inner}\n)"
        else:
            formula = f"IF({condition},{result},{formula})"
    
    result = "=" + formula
    
    # Verify balance
    assert result.count('(') == result.count(')'), \
        f"Parenthesis mismatch: {result.count('(')} open, {result.count(')')} close"
    
    return result


def tiered_lookup(value_cell, lookup_range, result_col=2, approximate=True):
    """
    Build VLOOKUP for tiered values (seniority, tax brackets, etc.).
    More maintainable than nested IF chains.
    """
    match_type = "TRUE" if approximate else "FALSE"
    return f"=VLOOKUP({value_cell},{lookup_range},{result_col},{match_type})"


def sumproduct_tiers(value_cell, brackets, rates):
    """
    Build SUMPRODUCT formula for tiered calculations (e.g., progressive tax).
    brackets: list of lower bounds [0, 7000, 50000, ...]
    rates: list of rates for each tier
    """
    if len(brackets) != len(rates):
        raise ValueError("Brackets and rates must have same length")
    
    parts = []
    for i, (low, high, rate) in enumerate(zip(brackets, brackets[1:] + [None], rates)):
        if high is None:
            # Top tier: above last bracket
            parts.append(f"({value_cell}>{low})*({value_cell}-{low})*{rate}")
        else:
            # Middle tier: between brackets
            parts.append(f"({value_cell}>{low})*({value_cell}<={high})*({value_cell}-{low})*{rate}")
    
    return "=SUMPRODUCT(" + "+".join(parts) + ")"


if __name__ == '__main__':
    # Example: Seniority pay tiers
    seniority = nested_if([
        ("C2<5", "0"),
        ("C2<10", "Assumptions!$B$5"),
        ("C2<15", "Assumptions!$B$6"),
        ("C2<20", "Assumptions!$B$7"),
        ("C2<25", "Assumptions!$B$8"),
    ], "Assumptions!$B$9")
    
    print("Seniority formula:")
    print(seniority)
    print(f"\nParenthesis check: {seniority.count('(')} open, {seniority.count(')')} close")