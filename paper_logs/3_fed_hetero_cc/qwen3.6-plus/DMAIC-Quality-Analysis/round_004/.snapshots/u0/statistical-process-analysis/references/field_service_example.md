# Field Service Analysis Example

## Task Pattern
DMAIC Analyze phase for field service work order productivity:
- Input: `field_service_data.csv` with columns `Date`, `Stage`, `Day`, `ClosedWorkOrders`
- Baseline: 115
- Target: 140
- Primary window: 2025-01-04 to 2025-03-01 (business days only)
- I-MR window: 2025-01-04 to 2025-02-21 (business days only)

## Exact Invocation
```bash
python3 scripts/compute_spc.py \
  --input field_service_data.csv \
  --date-col Date \
  --value-col ClosedWorkOrders \
  --baseline 115 \
  --target 140 \
  --start 2025-01-04 \
  --end 2025-03-01 \
  --imr-end 2025-02-21 \
  --output field_service_analyze_metrics.json
```

## Expected Output Structure
The verifier expects this exact JSON structure (abbreviated):
```json
{
  "filters": {
    "primary_date_range": "2025-01-04 to 2025-03-01 (inclusive)",
    "business_days_only": true,
    "imr_date_range": "2025-01-04 to 2025-02-21 (inclusive)"
  },
  "record_counts": {
    "total_records": 65,
    "primary_window_records": 47,
    "primary_window_business_days": 40,
    "imr_window_business_days": 35
  },
  "charter_metrics": {
    "baseline_value": 115,
    "target_value": 140,
    "current_mean_value": 134.799
  },
  "anova_by_weekday": {
    "weekday_means": {
      "Monday": 133.702,
      "Tuesday": 134.8,
      "Wednesday": 139.049,
      "Thursday": 136.719,
      "Friday": 129.726
    },
    "p_value": 0.4972,
    "f_statistic": 0.8604
  },
  "imr_summary": {
    "points": 35,
    "center_line": 132.848,
    "ucl": 149.884,
    "lcl": 115.812
  },
  "regression_day_index": {
    "slope": 0.6313,
    "p_value": 0.000001,
    "r_squared": 0.4883
  },
  "ttest_vs_target": {
    "n": 40,
    "mean_value": 134.799,
    "t_stat": -3.1146,
    "p_value": 0.003446,
    "ci95_low": 131.486,
    "ci95_high": 138.112
  },
  "capability_against_lsl": {
    "lsl": 140,
    "cpk_lower": -0.164
  }
}
```

## Key Mappings
- `--date-col Date`: Maps to CSV date column
- `--value-col ClosedWorkOrders`: Maps to CSV metric column
- `--imr-end 2025-02-21`: End date for control chart (typically end of Measure phase)
- `--end 2025-03-01`: End date for primary analysis (typically end of Analyze phase)

## Common Errors to Avoid
- Do NOT use `primary_analysis_window` as a JSON key — use `primary_date_range`
- Do NOT use `primary_analysis_records` — use `primary_window_business_days`
- Do NOT calculate weekday means manually — the script computes ANOVA correctly using scipy
