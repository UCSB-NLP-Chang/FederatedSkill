# Name Normalization Rules for 13F Fund Matching

## Standard Suffixes to Strip

Always remove these as whole words at the end of normalized names:

```
llc, lp, ltd, inc, corp, corporation, company, co,
partners, management, advisors, capital, group, holdings,
limited, plc, sa, nv, bv, gmbh, ag, kk, pte, sarl
```

## Normalization Pipeline

1. Lowercase
2. Remove all punctuation (`[^\w\s]`)
3. Split to words
4. Pop trailing suffixes while present in suffix list
5. Rejoin with single spaces

## Edge Cases

- **Multi-word suffixes**: `asset management` → strip both words
- **Embedded suffixes**: `Corporation Capital` → only strip trailing
- **Numeric suffixes**: `Fund IV` → preserve as identifier
- **International**: `S.A.` → normalize to `sa`, then strip

## Verification

After normalization, verify by:
- Checking original vs normalized in a sample
- Ensuring no empty strings result
- Confirming Levenshtein distances make intuitive sense