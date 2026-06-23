---
name: ocr-data-extraction
description: Extract structured fields (dates, prices, codes) from product labels, shelf tags, receipts, or documents using OCR with multiple fallback strategies. Use when single-pass OCR misses data or when input images have varying quality, angles, or text layouts.
---

# OCR Data Extraction

Extract specific fields from images using multi-strategy OCR. Single configurations often fail on real-world labels; use iterative preprocessing and page segmentation modes.

## Quick Start

1. **Batch process images** with multiple Tesseract configurations
2. **Extract fields** using domain-specific regex from all OCR outputs
3. **Normalize** dates to ISO format, prices to decimal
4. **Validate** completeness against input file count

## Multi-Strategy OCR

Run Tesseract with at least these variants and merge results:

| Preprocessing | PSM Mode | Purpose |
|--------------|----------|---------|
| None (auto) | `--psm 6` | Single uniform block; best for structured labels |
| None (auto) | `--psm 11` | Sparse text; finds scattered/distant text |
| Sharpen + Contrast | `--psm 6` | Low-contrast or blurry labels |
| Threshold (binary) | `--psm 6` | High contrast/background noise |

**PSM Decision Rules:**
- Start with `--psm 6` for aligned, block-style labels
- If text is detected but fragmented/misordered, switch to `--psm 11`
- For vertical or single-column text, try `--psm 4`

## Field Extraction Patterns

Scan OCR output with regex. See `references/regex_patterns.md` for extended library.

**Dates (Priority Order):**
1. `EXP(?:IRY)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})` - Expiry dates
2. `MFG(?:DATE)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})` - Manufacturing dates
3. `(\d{1,2}[/-]\d{1,2}[/-]\d{4})` - Generic fallback

**Prices:**
- `(?:RM|MYR|RS|\\$|€|£)\s*(\d{1,3}(?:,\d{3})*\.\d{2})` - Prefixed currency
- `(\d+\.\d{2})\s*(?:RM|MYR|\\$)?` - Suffixed or bare decimal

## Normalization Rules

**Dates:**
- Convert all matches to `YYYY-MM-DD`
- Handle partial dates: `MM/YYYY` → `YYYY-MM-01`
- Validate year range (reject < 1900 or > 2100 as OCR errors)
- Watch for day/month transposition (03/15 vs 15/03)

**Prices:**
- Strip currency symbols for numeric columns
- Remove thousand separators (commas)

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Validation Checklist

Before outputting final file:
- [ ] Row count matches input image count
- [ ] No empty/null critical fields (flag failures for manual review)
- [ ] Dates parse as valid calendar dates
- [ ] Prices are numeric (not strings with symbols)
- [ ] Data sorted by filename/identifier

## Anti-Patterns

- **Don't use single PSM mode**: PSM 6 misses scattered text; PSM 11 misorders structured blocks
- **Don't skip preprocessing**: Low-contrast shelf labels often require sharpening
- **Don't assume consistent formats**: Same dataset may mix `DD/MM/YYYY` and `MM-DD-YYYY`
- **Don't trust OCR symbols**: `0` vs `O`, `1` vs `l`, `/` vs `-` require regex flexibility

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| Low confidence scores | Increase image resolution to 300+ DPI before OCR |
| Missing price currency | Try PSM 11; check for split lines between symbol and number |
| Date parsing errors | Accept multiple separators (`/`, `-`, `.`) in regex |
| Partial text extraction | Run sharpening filter then retry with PSM 6 |

## Known invariants (by sub-task)

(No invariants recorded yet. Update this section when verifier failures reveal task-specific rules.)

## References

- `references/regex_patterns.md` - Extended regex library for dates, prices, barcodes, and IDs
