# Statistical Formulas Reference

## Coefficient of Variation (CV)

```
CV = sample_standard_deviation / mean
```

For proportions with varying denominators:
1. Calculate daily proportion = count / denominator
2. Compute CV across daily proportions

## Linear Regression Trend Test

```python
# Day index as x, metric as y
n = len(values)
x = [0, 1, 2, ..., n-1]
y = values

x_mean = mean(x)
y_mean = mean(y)

slope = sum((xi - x_mean) * (yi - y_mean)) / sum((xi - x_mean)^2)

# Standard error of slope
predictions = [intercept + slope * xi for xi in x]
residuals = [yi - pi for yi, pi in zip(y, predictions)]
mse = sum(r^2 for r in residuals) / (n - 2)
se_slope = sqrt(mse / sum((xi - x_mean)^2))

t_statistic = slope / se_slope
```

**Stability rule**: |t_statistic| > 2.0 → "Unstable"

## Wilson Score Interval

For proportion p = k/n with confidence level (e.g., 95% → z=1.96):

```
denominator = 1 + z²/n
centre = (p + z²/(2n)) / denominator
margin = z * sqrt((p(1-p) + z²/(4n)) / n) / denominator

lower = centre - margin
upper = centre + margin
```

## Process Capability

```
Capability = "Capable" if observed_rate < target_rate else "Not Capable"
```

## Ranking

Sort processes by CV in descending order (highest CV = highest variability = highest risk).
