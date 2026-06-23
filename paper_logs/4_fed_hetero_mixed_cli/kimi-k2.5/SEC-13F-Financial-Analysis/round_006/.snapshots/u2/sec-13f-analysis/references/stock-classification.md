# Stock Classification Rules

Use tokenized matching to classify `TITLEOFCLASS` values as stock-like.

## Include (stock-like)

Split `TITLEOFCLASS` on whitespace and check for these tokens:

- `common`
- `ordinary`
- `share` / `shares`
- `stock`
- `com` (abbreviation for common)
- `shs` (abbreviation for shares)
- `cl` (abbreviation for class)
- `class`

## Exclude (non-stock)

Check for these tokens:

- `bond`
- `note`
- `deb` / `debt`
- `etf`
- `trust`
- `fund`
- `index`
- `treas` / `treasury`
- `muni`
- `pfd` / `pref` / `preferred`
- `adr`
- `put`
- `call`
- `option`

## Classification Logic

```python
def is_stock_like(title):
    if not title:
        return False
    tokens = title.lower().split()
    include = {'common', 'ordinary', 'share', 'shares', 'stock', 'com', 'shs', 'cl', 'class'}
    exclude = {'bond', 'note', 'deb', 'etf', 'trust', 'fund', 'index', 'treas', 'muni', 'pfd', 'pref', 'adr', 'put', 'call', 'option'}
    has_include = any(t in include for t in tokens)
    has_exclude = any(t in exclude for t in tokens)
    return has_include and not has_exclude
```

## Examples

| TITLEOFCLASS | Tokens | Stock? | Reason |
|--------------|--------|--------|--------|
| `COMMON STOCK` | `['common', 'stock']` | Yes | Contains include tokens |
| `COM` | `['com']` | Yes | `com` is in include set |
| `CL A` | `['cl', 'a']` | Yes | `cl` is in include set |
| `ISHARES NEW` | `['ishares', 'new']` | No | No include token (`share` is not `shares`, and it's a substring not token) |
| `CORE S&P500 ETF` | `['core', 's&p500', 'etf']` | No | Contains `etf` in exclude set |
| `ORDINARY SHARES` | `['ordinary', 'shares']` | Yes | Contains include tokens |

## Substring Trap

Do NOT use substring matching. `ISHARES` contains `share` as substring but `share` is not a token when split on whitespace.

Correct: `title.lower().split()` then check token membership.
Wrong: `'share' in title.lower()`
