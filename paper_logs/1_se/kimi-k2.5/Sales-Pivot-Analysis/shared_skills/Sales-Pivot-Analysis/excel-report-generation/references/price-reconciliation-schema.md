# Price Reconciliation Decision Schema

## Context
When transaction data contains `UNIT_PRICE` and a catalog contains reference prices, you must decide which price to use for calculations.

## Decision Matrix

| Scenario | Condition | Final Price | Status | Action | Notes |
|----------|-----------|-------------|--------|--------|-------|
| Perfect match | `abs(trans - cat) < 0.01` | Transaction | `transaction_price` | `prices_match` | Either is fine |
| Minor variance | `abs(trans - cat) < tolerance` | Transaction | `transaction_price` | `prices_match` | Within tolerance |
| Significant diff | `abs(trans - cat) >= tolerance` | Transaction* | `transaction_override` | `used_transaction_unit_price` | *Or catalog if specified |
| Missing catalog | `pd.isna(catalog)` | Transaction | `transaction_only` | `no_catalog_match` | Log unmatched IDs |
| Missing transaction | `pd.isna(transaction)` | Catalog | `catalog_only` | `filled_from_catalog` | Rare edge case |

## Policy Variants

**Variant A: Transaction-authoritative** (default for sales reports)
- Use transaction price always (what customer actually paid)
- Document when catalog differs
- Best for: revenue reporting, actual sales analysis

**Variant B: Catalog-authoritative** (for price compliance)
- Use catalog price, flag transactions outside tolerance
- Best for: checking discount compliance, price integrity

**Variant C: Hybrid** (context-dependent)
- Use catalog for standard items, transaction for overrides
- Requires explicit business rule documentation

## Audit Columns

Always add these to SourceData for traceability:

| Column | Values | Meaning |
|--------|--------|---------|
| `PRICE_STATUS` | `transaction_price`, `transaction_override`, `catalog_price`, `transaction_only`, `catalog_only` | Which source provided final price |
| `CATALOG_MATCH_STATUS` | `matched`, `unmatched` | Whether PRODUCT_ID exists in catalog |
| `RECONCILIATION_ACTION` | `prices_match`, `used_transaction_unit_price`, `used_catalog_unit_price`, `no_catalog_match`, `filled_from_catalog` | Specific resolution |

## Example Implementation

```python
def reconcile_prices(trans_df, catalog_df, price_col='UNIT_PRICE', 
                     catalog_price_col='UNIT_PRICE', prefer='transaction'):
    """
    Merge and reconcile prices between transaction and catalog.
    
    prefer: 'transaction' | 'catalog'
    """
    catalog_lookup = catalog_df.set_index('PRODUCT_ID')[catalog_price_col].to_dict()
    
    def reconcile_row(row):
        trans_price = row[price_col]
        cat_price = catalog_lookup.get(row['PRODUCT_ID'])
        
        if pd.isna(cat_price):
            return trans_price, 'transaction_only', 'no_catalog_match'
        
        if abs(trans_price - cat_price) < 0.01:
            return trans_price, 'transaction_price', 'prices_match'
        
        if prefer == 'transaction':
            return trans_price, 'transaction_override', 'used_transaction_unit_price'
        else:
            return cat_price, 'catalog_override', 'used_catalog_unit_price'
    
    results = trans_df.apply(reconcile_row, axis=1, result_type='expand')
    trans_df['UNIT_PRICE_FINAL'] = results[0]
    trans_df['PRICE_STATUS'] = results[1]
    trans_df['RECONCILIATION_ACTION'] = results[2]
    
    return trans_df
```