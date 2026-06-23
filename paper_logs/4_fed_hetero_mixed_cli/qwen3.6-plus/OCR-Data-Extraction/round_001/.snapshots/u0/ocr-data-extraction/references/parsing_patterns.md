# Date & Price Parsing Patterns

## Date Disambiguation
- `DD/MM/YYYY` vs `MM/DD/YYYY`: Check the first number. If `> 12`, it is the day. If both `<= 12`, context or locale dictates. Default to `DD/MM` for international/Malaysian/European contexts.
- `MM/YYYY`: Implies first day of month. Normalize to `YYYY-MM-01`.
- `DD-MM-YYYY` vs `DD/MM/YYYY`: Treat separators interchangeably.

## Price Extraction
- Strip currency prefixes/suffixes: `$`, `RM`, `MYR`, `€`, `£`, `EACH`, `PER`.
- Handle thousands separators: Remove commas before parsing.
- Regex: `(?:RM|MYR|\$|€)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)`
- Always format output to exactly 2 decimal places.

## Common OCR Artifacts
- `0` ↔ `O`, `1` ↔ `I` or `l`, `5` ↔ `S`, `8` ↔ `B`.
- Dashes vs slashes: `-` vs `/` vs `.`. Normalize to `-` for ISO dates.
- Missing spaces: `RM10.99` vs `RM 10.99`. Regex should allow optional whitespace.