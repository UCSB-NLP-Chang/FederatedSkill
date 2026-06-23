# [Hospital Name] — Patient Safety Brief

## Summary of Findings

This report presents a performance and risk assessment based on three key patient safety metrics.

### Wait Times
- **Mean Wait Time:** [mean_minutes] minutes
- **Sample Std Dev:** [sample_std_minutes] minutes
- **Coefficient of Variation (CV):** [cv]
- **Trend:** [stability] (slope = [trend_slope], t-stat = [trend_t_stat])

### Medication Errors
- **Mean Proportion (Errors / Prescriptions Filled):** [mean_proportion]
- **Overall Error Rate:** [overall_rate_pct]%
- **Wilson 95% CI:** [wilson_ci_lower_pct]%, [wilson_ci_upper_pct]%
- **Target Rate:** [target_rate_pct]%
- **Capability:** [capability_vs_target]
- **Trend:** [stability] (slope = [trend_slope], t-stat = [trend_t_stat])
- **Varying Denominators:** Yes

### Readmission Rates
- **Mean Readmission Rate:** [mean_rate]
- **Sample Std Dev:** [sample_std_rate]
- **Coefficient of Variation (CV):** [cv]
- **Trend:** [stability] (slope = [trend_slope], t-stat = [trend_t_stat])

### Variability Ranking (Highest to Lowest CV)
| Rank | Process | CV |
|------|---------|-----|
| 1 | [Process 1] | [cv1] |
| 2 | [Process 2] | [cv2] |
| 3 | [Process 3] | [cv3] |

## Most Significant Risks

[highest_risk_statement]

The variability ranking shows **[highest_variability_process]** has the highest coefficient of variation, indicating the greatest relative variability in performance.

Key risk indicators:
- Wait times process is [wt_stability], with a trend slope of [wt_slope]
- Medication errors process is [me_stability], with overall rate at [me_rate]% (target: [target]%)
- Readmission rates process is [rr_stability], with CV of [rr_cv]

## Prioritized Corrective Actions

| Priority | Action | Owner | Timeline |
|----------|--------|-------|----------|
| 1 | [Action for highest CV process] | [Owner] | [Timeline] |
| 2 | [Action for second priority] | [Owner] | [Timeline] |
| 3 | [Action for third priority] | [Owner] | [Timeline] |

## Monitoring Plan

### Process to be Monitored
[highest_variability_process]

### Inputs
- [Input 1]
- [Input 2]
- [Input 3]

### Outputs
- [Output 1]
- [Output 2]
- [Output 3]

### Key Performance Indicators (KPIs)
- [KPI 1]
- [KPI 2]
- [KPI 3]

### Frequency of Monitoring
[Frequency]

### Observation Format
[Format description]

### Roles
- [Role 1]
- [Role 2]
- [Role 3]

### Reporting Format
[Reporting format description]

### Corrective Action Process
[Process description]

### Benchmarks
- **target_rate_pct:** [value]
- **max_acceptable_cv:** 0.15
- **stability_threshold_t_stat:** 2.0

---
*Report generated for [Hospital Name]. All metrics computed using sample standard deviation (ddof=1) and standard trend analysis.*
