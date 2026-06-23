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

- **Multi-word suffixes**: `asset management` → strip both words if in list
- **Embedded suffixes**: `Corporation Capital` → only strip trailing
- **Numeric suffixes**: `Fund IV` → preserve as identifier
- **International**: `S.A.` → normalize to `sa`, then strip

## Distance Thresholds

After computing Levenshtein distance on normalized names:

- Distance ≤ 2: Good match, proceed confidently
- Distance 3-4: Marginal, verify manually or flag uncertainty
- Distance > 4: **REJECT** — output `matched_manager: null`

## Semantic Sanity-Check

After finding the best match by distance, verify semantic plausibility:

1. Extract key identifying words from the query (e.g., "elliott" from "elliott associates", "tiger" from "tiger global")
2. Check if at least one key word appears in the matched manager name
3. If no key words match, the match is suspect even with marginal distance

| Query | Matched | Distance | Key Word Check | Verdict |
|-------|---------|----------|----------------|--------|
| renaissance technologies | renaissance technologies llc | 0 | ✓ | Accept |
| elliott associates | elliott management corp | 3 | ✓ "elliott" | Marginal, verify |
| elliott associates | jvl associates llc | 6 | ✗ no "elliott" | **Reject** |
| renaissance technologies | headlands technologies | 7 | ✗ no "renaissance" | **Reject** |
| tiger global | voyager global management lp | 4 | ✗ no "tiger" | **Reject** |

**Critical**: The "tiger global" → "Voyager Global Management LP" case (distance=4) demonstrates why semantic checks are mandatory. Both share "global" but are completely different entities. Always verify key identifying words appear in the matched name.

## Missing Fund Handling

When a fund is not found in a quarter:

1. **Not found in baseline, found in current**:
   - All current positions are "new" (no prior holdings)
   - Largest buy = largest current position
   - Largest sell = empty string (nothing to sell from)
   - Include `baseline_missing: true` flag in output

2. **Not found in current, found in baseline**:
   - Cannot compute comparison; output null for current
   - This is an error condition for comparison tasks

3. **Not found in either quarter**:
   - Output `matched_manager: null` for both
   - Halt comparison

4. **Snapshot check (B6) not found**:
   - Output `stock_holdings: 0`
   - This is NOT an error; fund may genuinely have no filing that quarter

## Verification

After normalization, verify by:
- Checking original vs normalized in a sample
- Ensuring no empty strings result
- Confirming Levenshtein distances make intuitive sense
- Running semantic sanity-check on key words

## Example

| Original | Normalized |
|----------|------------|
| Renaissance Technologies LLC | renaissance technologies |
| Renaissance Technologies Corp | renaissance technologies |
| Renaissance Institutional Equities Fund LP | renaissance institutional equities fund |
| Headlands Technologies LLC | headlands technologies |
| Berkshire Hathaway Inc | berkshire hathaway |
| Tiger Global Management LLC | tiger global |
| Voyager Global Management LP | voyager global |

Distance between "tiger global" and "voyager global" = 4 (marginal, but **REJECT** due to semantic check — "tiger" not in matched name).