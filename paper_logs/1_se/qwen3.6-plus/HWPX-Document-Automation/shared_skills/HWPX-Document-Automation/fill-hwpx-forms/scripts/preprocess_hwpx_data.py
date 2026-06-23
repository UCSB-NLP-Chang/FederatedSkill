#!/usr/bin/env python3
"""Preprocess JSON data for HWPX template filling.

Applies common transformations:
- Currency normalization (remove commas from amounts)
- Date duration calculation (start/end → duration string)
- Value appending (add suffix to existing values)

Usage: python3 preprocess_hwpx_data.py <input.json> <output.json>

For task-specific logic, modify this script or write a short inline preprocessor.
"""
import sys
import json
import re
from datetime import datetime

def normalize_currency(value):
    """Remove commas from currency strings like ₩450,000,000 → ₩450000000."""
    if isinstance(value, str) and re.search(r'[₩$€¥£]\d', value):
        return re.sub(r',', '', value)
    return value

def calculate_duration(start_str, end_str):
    """Calculate duration in months between two date strings (YYYY-MM or YYYY-MM-DD)."""
    try:
        start = datetime.strptime(start_str[:7], '%Y-%m')
        end = datetime.strptime(end_str[:7], '%Y-%m')
        months = (end.year - start.year) * 12 + (end.month - start.month)
        return f"({months}개월)"
    except (ValueError, TypeError):
        return ""

def preprocess(data):
    """Apply preprocessing rules. Override or extend for task-specific needs."""
    result = dict(data)
    
    # Normalize currency fields
    for key in result:
        if any(term in key.lower() for term in ['예산', 'budget', 'cost', 'price', 'amount']):
            result[key] = normalize_currency(result[key])
    
    # Calculate durations if start/end dates exist
    if '시작일' in result and '종료일' in result:
        duration = calculate_duration(result['시작일'], result['종료일'])
        result['총기간'] = duration
    
    # Append duration to phase fields if they contain date ranges
    for key in result:
        if key.startswith('단계') and '(' in str(result[key]) and ')' in str(result[key]):
            # Extract date range from value like "요구사항 분석 (2026-08 ~ 2026-10)"
            match = re.search(r'(\d{4}-\d{2})\s*~\s*(\d{4}-\d{2})', str(result[key]))
            if match:
                duration = calculate_duration(match.group(1), match.group(2))
                result[key] = f"{result[key]}{duration}"
    
    return result

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: preprocess_hwpx_data.py <input.json> <output.json>")
        sys.exit(1)
    
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    processed = preprocess(data)
    
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)
    
    print(f"Preprocessed {len(data)} fields → {len(processed)} fields")
    print("Keys:", list(processed.keys()))
