# Price Tier Calculation Patterns

## Standard Tier Logic

```python
def price_tier(amount):
    """
    Categorize registration fee into tiers.
    
    Adjust thresholds based on actual fee distribution in data.
    """
    if amount == 0:
        return 'Free'
    elif amount < 150:
        return 'Budget'
    elif amount < 400:
        return 'Standard'
    else:
        return 'Premium'
```

## Variant: Percentile-Based Tiers

When fee structure varies significantly between events:

```python
def price_tier_percentile(df, amount_col='AMOUNT_PAID'):
    """Assign tiers based on data distribution."""
    p33 = df[amount_col].quantile(0.33)
    p67 = df[amount_col].quantile(0.67)
    
    def tier(amount):
        if amount == 0: return 'Free'
        elif amount < p33: return 'Budget'
        elif amount < p67: return 'Standard'
        else: return 'Premium'
    
    return df[amount_col].apply(tier)
```

## Variant: Registration-Type Based

When tiers directly map to registration types:

```python
def price_tier_by_regtype(reg_type, amount):
    """Derive tier from registration type with amount validation."""
    tier_map = {
        'Speaker': 'Free',
        'Student': 'Budget',
        'Standard': 'Standard',
        'VIP': 'Premium'
    }
    expected = tier_map.get(reg_type, 'Standard')
    # Optional: flag if amount doesn't match expected range
    return expected
```

## Verification

```python
# Check tier distribution
tier_dist = df['PRICE_TIER'].value_counts()
print(tier_dist)

# Validate: Premium should have highest amounts
print(df.groupby('PRICE_TIER')['AMOUNT_PAID'].agg(['min', 'max', 'mean']))
```
