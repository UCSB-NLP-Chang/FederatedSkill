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

Match these in `TITLEOFCLASS` or `NAMEOFISSUER`:
- `ETF`, `FUND`, `TR`, `UNIT`, `UTSER`
- `NOTE`, `DEB`, `BOND`, `PFD`, `PRFD`
- `PUT`, `CALL`, `WTS`, `RIGHT`
- `ADR`, `SPONSORED ADS`
- Issuer names containing: `TR`, `FUND`, `ETF`, `EXCHANGE-TRADED`, `ISHARES`, `SPDR`, `INVESCO`, `VANGUARD`, `FIDELITY`

## Classification rule

1. **Primary**: Check `TITLEOFCLASS` against stock-like patterns first
2. **Secondary**: If `TITLEOFCLASS` is ambiguous, check `NAMEOFISSUER` for fund/ETF indicators
3. **Never**: Classify based solely on `NAMEOFISSUER` containing stock-like words (e.g., "NETFLIX INC" is stock, not fund, even if issuer name contains "INC")
4. **Exclude**: Any row where `TITLEOFCLASS` contains fund/ETF keywords, regardless of issuer name

## Edge cases

- `SPONSORED ADS`: ADR (American Depositary Receipt) - exclude from stock count
- `SHS BEN INT`: Beneficial interest in trust - exclude
- `UNIT SER 1`: Unit series - exclude
- `G` (Gold): Commodity trust - exclude
- `COM CL A`: Common stock class A - include
- `CAP STK CL C`: Capital stock class C - include