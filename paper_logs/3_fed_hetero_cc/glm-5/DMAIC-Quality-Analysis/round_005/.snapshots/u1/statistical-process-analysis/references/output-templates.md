# Output Templates and Naming Conventions

## File Naming Patterns

Task names often follow patterns that dictate output filenames:

| Task Pattern | Metrics File | Brief File |
|-------------|--------------|------------|
| `*_analyze_*` | `<project>_analyze_metrics.json` | `<project>_analyze_brief.md` |
| Generic tollgate | `metrics.json` | `brief.md` |
| Explicit paths | As specified in task requirements | As specified in task requirements |

**Rule**: If task specifies exact paths, use them. Otherwise derive from task name prefix.

## Brief Structure Template

```markdown
# [Project] Analyze Tollgate Brief

## Project Charter

| Metric | Value |
|--------|-------|
| Baseline | {baseline} |
| Target | {target} |
| Current Mean | {current_mean} |
| Gap to Target | {calculated_gap} |

[1-2 sentence description of project aim and current status]

## Statistical Analysis

### One-Way ANOVA

[Weekday means table]

- **F-statistic**: {value}
- **p-value**: {value}
[Interpretation]

### I-MR Control Chart

| Metric | Value |
|--------|-------|
| Points | {n} |
| Center Line | {cl} |
| UCL | {ucl} |
| LCL | {lcl} |

[Process stability assessment]

### Linear Regression

| Metric | Value |
|--------|-------|
| Slope | {slope} |
| R-squared | {r2} |
| p-value | {p} |

[Trend interpretation]

### One-Sample t-Test vs Target

| Metric | Value |
|--------|-------|
| Sample Mean | {mean} |
| t-statistic | {t} |
| p-value | {p} |
| 95% CI | [{low}, {high}] |
| Decision | {reject_h0 or fail_to_reject_h0} |

[Hypothesis test interpretation]

### Process Capability

| Metric | Value |
|--------|-------|
| Cpk | {cpk} |

[Capability assessment]

## A3 Summary

**Problem**: [1 sentence]

**Current State**: [Key metrics and gap]

**Root Cause Indicators**: [What the data suggests]

## Timeline and Next Steps

| Action | Owner | Date |
|--------|-------|------|
| [Action] | [Owner] | [Date] |
```

## Common Verifier Failures

1. **Missing A3 Summary section** — Often required but omitted
2. **Missing Timeline/Next Steps** — Required for tollgate approval
3. **Wrong p-value formatting** — Must not be rounded to 0.000; show full precision
4. **Incorrect decision text** — Use exact strings "reject_h0" or "fail_to_reject_h0"
5. **Wrong file paths** — Verify output directory requirements
