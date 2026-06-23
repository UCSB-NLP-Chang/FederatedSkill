# TITLEOFCLASS (TOC) Classification Patterns

## Stock-like patterns (include)

Match these in `TITLEOFCLASS` (case-insensitive):
- `COM`, `COM CL A`, `COM CL B`, `COM CL C`
- `SHS`, `SHS CLASS A`, `SHS CLASS B`, `SHS CLASS C`
- `CL A`, `CL B`, `CL C`, `CL B NEW`
- `CAP STK`, `CAP STK CL A`, `CAP STK CL B`, `CAP STK CL C`
- `ORD`, `ORD SHS`, `COMMON`, `COMMON STK`, `STK`
- `CLASS A`, `CLASS B`, `CLASS C`

## Fund/ETF/Trust patterns (exclude)

Match these in `TITLEOFCLASS`:
- `ETF`, `FUND`, `TR`, `UNIT`, `UTSER`
- `NOTE`, `DEB`, `BOND`, `PFD`, `PRFD`
- `PUT`, `CALL`, `WTS`, `RIGHT`
- `ADR`, `SPONSORED ADS`

## Classification rule

1. **Primary**: Check `TITLEOFCLASS` against stock-like patterns first
2. **Exclude**: Any row where `TITLEOFCLASS` contains fund/ETF keywords
3. **Never classify by NAMEOFISSUER**: Issuer name alone doesn't determine stock/fund status
   - "NETFLIX INC" in NAMEOFISSUER doesn't mean stock — check TITLEOFCLASS
   - Fund issuer names may contain stock-like words — TITLEOFCLASS is authoritative

## Edge cases

- `SPONSORED ADS`: ADR (American Depositary Receipt) - exclude from stock count
- `SHS BEN INT`: Beneficial interest in trust - exclude
- `UNIT SER 1`: Unit series - exclude
- `G` (Gold): Commodity trust - exclude
- `COM CL A`: Common stock class A - include
- `CAP STK CL C`: Capital stock class C - include

## Anti-patterns

- DO NOT use `"stock" in title.lower()` — misses >90% of SEC abbreviations
- DO NOT check NAMEOFISSUER for keywords like "ETF", "FUND" — false positives
- DO NOT assume COM = common stock without checking exclusions first