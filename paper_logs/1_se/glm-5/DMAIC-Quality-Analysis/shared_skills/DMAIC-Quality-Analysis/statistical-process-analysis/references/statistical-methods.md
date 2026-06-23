# Statistical Methods Reference

## ANOVA (One-Way)

Compare means across multiple groups (e.g., weekday effects).

**Implementation:**
```python
from scipy import stats
# Group data by category
groups = [data[data['category'] == g]['value'] for g in categories]
f_stat, p_value = stats.f_oneway(*groups)
```

**Manual calculation:**
- SS_between = Σn_i(x̄_i - x̄)²
- SS_within = ΣΣ(x_ij - x̄_i)²
- F = (SS_between / df_between) / (SS_within / df_within)
- p-value from F-distribution with (k-1, N-k) degrees of freedom

**Validation:** p-value must be in [0, 1]; F-statistic ≥ 0

---

## I-MR Control Charts

Assess process stability over time.

**Moving Range (MR):**
- MR_i = |X_i - X_{i-1}| for i = 2 to n
- MR̄ = average of all MR values

**I-Chart (Individuals):**
- Center Line: X̄ (overall mean)
- UCL = X̄ + 2.66 × MR̄
- LCL = X̄ - 2.66 × MR̄
- Note: 2.66 = 3 / d2 where d2 = 1.128 for n=2

**MR-Chart:**
- Center Line: MR̄
- UCL = 3.27 × MR̄ (D4 factor for n=2)
- LCL = 0

**Out-of-control rules:**
- Points beyond control limits
- 7+ consecutive points on one side of center line
- 7+ consecutive trending up or down

---

## Linear Regression

Identify trends over time.

**Implementation:**
```python
from scipy import stats
x = np.arange(len(data))  # Time index
slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
```

**Key outputs:**
- Slope: rate of change per time unit
- R²: proportion of variance explained
- p-value: significance of slope (H0: slope = 0)

**Validation:** R² in [0, 1]; p-value in [0, 1]

---

## One-Sample t-Test

Compare sample mean against a target value.

**Implementation:**
```python
from scipy import stats
t_stat, p_value = stats.ttest_1samp(data, target)
```

**Manual calculation:**
- t = (x̄ - μ₀) / (s / √n)
- p-value from t-distribution with n-1 degrees of freedom

**Decision:**
- If p < α (typically 0.05), reject H0
- Report whether mean is significantly different from target

---

## Process Capability (Cpk)

Measure ability to meet specifications.

**Formulas:**
- Cpu = (USL - μ) / (3σ)  -- upper capability
- Cpl = (μ - LSL) / (3σ)  -- lower capability
- Cpk = min(Cpu, Cpl)

**For one-sided spec (target only):**
- If target is a minimum: Cpk = (μ - LSL) / (3σ) where LSL = target
- If target is a maximum: Cpk = (USL - μ) / (3σ) where USL = target

**Interpretation:**
- Cpk ≥ 1.33: Capable process
- 1.0 ≤ Cpk < 1.33: Marginally capable
- Cpk < 1.0: Not capable
- Cpk < 0: Mean is outside specification

**Validation:** σ > 0; Cpk is a real number (can be negative)

---

## Manual P-Value Calculation (When scipy Unavailable)

**WARNING: Manual p-value calculations are error-prone. Always prefer scipy.stats.**

If scipy is truly unavailable and you must calculate manually:

### t-distribution p-value (two-tailed)
```python
import math

def t_test_pvalue(t_stat, df):
    """Approximate two-tailed p-value for t-statistic."""
    # Use regularized incomplete beta function approximation
    x = df / (df + t_stat**2)
    # For large df, approaches normal distribution
    if df > 30:
        # Normal approximation
        p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2))))
        return p_value
    # For small df, use t-distribution tables or more complex approximation
    # This is a simplified approach - prefer scipy.stats.t.cdf
    from math import gamma
    # ... complex beta function calculation
    # STRONGLY RECOMMEND: Install scipy instead
```

### F-distribution p-value (ANOVA)
```python
# Even more complex - requires incomplete beta function
# STRONGLY RECOMMEND: Install scipy instead
```

**Validation checks for manual calculations:**
- p-value MUST be in [0, 1]
- If p-value < 0 or > 1, calculation is wrong
- For t-test: larger |t| should give smaller p-value
- For ANOVA: larger F should give smaller p-value

---

## Common Implementation Errors

1. **P-value outside [0,1]**: Usually indicates calculation error; use scipy.stats
2. **Negative variance**: Check data types and filtering logic
3. **Wrong degrees of freedom**: ANOVA uses (k-1, N-k); t-test uses n-1
4. **Control limits inverted**: UCL > LCL always; if not, check calculation
5. **Cpk sign wrong**: If mean < LSL or mean > USL, Cpk should be negative
6. **Manual p-value without scipy**: Often produces invalid results; install scipy first