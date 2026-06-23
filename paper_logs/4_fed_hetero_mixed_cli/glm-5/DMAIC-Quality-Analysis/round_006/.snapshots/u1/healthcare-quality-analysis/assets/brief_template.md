# [Hospital Name] — Patient Safety Brief

## Summary of Findings

This report presents a deterministic performance and risk assessment based on three key patient safety metrics.

### Wait Times
- **Mean Wait Time:** [mean] minutes
- **Sample Std Dev:** [std] minutes
- **Coefficient of Variation (CV):** [cv]
- **Trend:** [stability] (slope = [slope], t-stat = [t_stat])

### Medication Errors
- **Mean Proportion (Errors / Prescriptions Filled):** [mean_prop]
- **Overall Error Rate:** [rate]%
- **Wilson 95% CI:** [ci_low]%, [ci_high]%
- **Target Rate:** [target]%
- **Capability:** [capable]
- **Trend:** [stability] (slope = [slope], t-stat = [t_stat])
- **Varying Denominators:** Yes

### Readmission Rates
- **Mean Readmission Rate:** [mean]
- **Sample Std Dev:** [std]
- **Coefficient of Variation (CV):** [cv]
- **Trend:** [stability] (slope = [slope], t-stat = [t_stat])

### Variability Ranking (Highest to Lowest CV)
| Rank | Process | CV |
|------|---------|----|
| 1 | [Process 1] | [cv1] |
| 2 | [Process 2] | [cv2] |
| 3 | [Process 3] | [cv3] |

## Most Significant Risks

[highest_risk_statement]

The variability ranking shows **[highest_process]** has the highest coefficient of variation ([cv]), indicating the greatest relative variability in performance.

Key risk indicators:
- Wait times process is [wt_stability], with a trend slope of [wt_slope]
- Medication errors process is [me_stability], with overall rate at [me_rate]% (target: [target]%)
- Readmission rates process is **[rr_stability]**, with CV of [rr_cv]

## Prioritized Corrective Actions

| Priority | Action | Owner | Timeline |
|----------|--------|-------|----------|
| 1 | Investigate root causes of high [highest_process] variability | Quality Improvement Manager | 30 days |
| 2 | Implement protocol review and staff training | Department Heads | 45 days |
| 3 | Establish real-time tracking dashboard | Data Analyst | 60 days |

## Monitoring Plan

### Process to be Monitored

[highest_process]

### Inputs

- Monthly counts
- Total denominators
- Department breakdowns
- Risk factors

### Outputs

- Monthly rate (%)
- Trend analysis
- Variability assessment (CV)
- Stability classification

### Key Performance Indicators (KPIs)

- Rate (%)
- Coefficient of Variation (CV)
- Trend slope & significance
- Confidence interval bounds

### Frequency of Monitoring

Monthly

### Observation Format

Tabular data collection with department-level aggregation

### Roles

- Quality Improvement Manager
- Department Heads
- Data Analyst
- Chief Medical Officer

### Reporting Format

Monthly dashboard report with trend charts and statistical summaries

### Corrective Action Process

PDCA cycle (Plan-Do-Check-Act) with root cause analysis for out-of-control points

### Benchmarks

- **target_readmission_rate_pct:** [target_rr]
- **max_acceptable_cv:** 0.15
- **stability_threshold_t_stat:** 2.0

---

*Report generated for [Hospital Name]. All metrics computed using sample standard deviation (ddof=1) and standard trend analysis.*