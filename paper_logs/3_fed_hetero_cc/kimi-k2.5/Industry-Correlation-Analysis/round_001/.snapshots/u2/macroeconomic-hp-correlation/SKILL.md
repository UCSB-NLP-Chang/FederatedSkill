---
name: macroeconomic-hp-correlation
description: Compute cyclical correlation between economic time series using HP filter. Use for tasks involving business cycle analysis, co-movement of economic indicators, or correlation of detrended macroeconomic variables. Trigger phrases include 'HP filter', 'cyclical correlation', 'business cycle', 'co-movement', 'Hodrick-Prescott'.
---

# Macroeconomic HP Filter Correlation Analysis

Compute Pearson correlation between cyclical components of two economic time series using the Hodrick-Prescott (HP) filter.

## Workflow

### 1. Data Preparation
- Extract nominal values from source files (Excel, CSV, etc.)
- For partial-year data (e.g., quarterly when annual needed), average available periods
- Ensure both series share the same time range and frequency

### 2. Deflation to Real Values
- Load price index series with base year = 1.0
- Calculate: `real_value = nominal_value / price_index`
- Verify base year shows real = nominal (index = 1.0)

### 3. HP Filter Application
- Transform: `log_real = ln(real_value)` — apply HP filter to logs, not levels
- Use `statsmodels.tsa.filters.hp_filter.hpfilter()`
- Lambda values:
  - **Annual data**: λ = 100
  - Quarterly data: λ = 1600
  - Monthly data: λ = 14400
- Extract cyclical component (second return value)
- Verify cyclical mean ≈ 0 (numerical zero check)

### 4. Correlation Calculation
- Compute Pearson correlation between cyclical components
- Report to required precision (typically 5 decimal places)
- Verify result is in valid range [-1, 1]

### 5. Output Validation
- Write result to answer file
- Verify exact format: check bytes with `xxd` if precision matters
- Ensure no extra whitespace or missing trailing digits

## Output precision
Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: write raw float values; format only at final output if verifier specifies precision
- The verifier's tolerance (often 1e-4) decides acceptable precision; the skill's job is to give it full precision and let it decide.

## Anti-Patterns

- **Do NOT** apply HP filter to nominal values or levels — always use log-transformed real values
- **Do NOT** use λ = 1600 for annual data (quarterly value)
- **Do NOT** forget to verify the cyclical component sums to ~0
- **Do NOT** trust file content at face value — verify exact bytes for precision-critical outputs

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Correlation > 1 or < -1 | Data error or wrong series | Check real value calculation |
| Cyclical mean far from 0 | Wrong lambda or frequency | Verify λ matches data frequency |
| Mismatched series lengths | Different date ranges | Align series before HP filter |
| Answer rejected for format | Trailing newline or precision | Use `xxd` to verify exact bytes |

## Example

```python
from statsmodels.tsa.filters.hp_filter import hpfilter
import numpy as np

# Real values already computed
log_dining = np.log(dining_real)
log_travel = np.log(travel_real)

# HP filter with annual lambda=100
cyclical_dining, _ = hpfilter(log_dining, lamb=100)
cyclical_travel, _ = hpfilter(log_travel, lamb=100)

# Correlation
corr = np.corrcoef(cyclical_dining, cyclical_travel)[0, 1]
print(f"{corr:.5f}")  # 0.97510
```