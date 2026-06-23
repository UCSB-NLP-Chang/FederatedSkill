---
name: image-data-extraction
description: Extract structured data (dates, prices, codes) from images using OCR. Use for processing receipts, labels, invoices, or any image-based documents where text needs to be parsed into structured formats like Excel/CSV.
---

# Image Data Extraction

Extract structured data from image collections using Tesseract OCR with robust preprocessing and pattern matching.

## When to Use
- Processing batches of receipt/invoice/label images
- Extracting dates, prices, codes, or other patterned data from visual documents
- Converting image-based tabular data to structured formats (Excel, CSV, JSON)
- Input contains variable image quality, multiple text orientations, or mixed formats

## Workflow

1. **Enumerate images** - Use glob patterns to discover all target images
2. **Configure OCR** - Use `pytesseract` with multiple fallback preprocessing strategies
3. **Define extraction patterns** - Create regex patterns for each field type with priority ordering
4. **Parse with fallbacks** - Try multiple patterns per field; log unmatched entries for review
5. **Output validation** - Verify output format, check for missing values, validate data types
6. **Export** - Write to required format (Excel, CSV, JSON)

## OCR Preprocessing Strategy

Always apply multiple preprocessing approaches in order of success probability:

```python
def extract_with_fallbacks(image_path):
    img = Image.open(image_path)

    # Strategy 1: Original
    text = pytesseract.image_to_string(img)

    # Strategy 2: Grayscale
    text = pytesseract.image_to_string(img.convert('L'))

    # Strategy 3: Contrast enhancement (binarization)
    text = pytesseract.image_to_string(img_gray.point(lambda x: 0 if x < 100 else 255, '1'))

    # Strategy 4: Inverted
    text = pytesseract.image_to_string(Image.eval(img_gray, lambda x: 255 - x))

    # Strategy 5: Page segmentation modes
    for psm in [6, 3, 4, 11]:  # 6=uniform block, 3=auto, 4=single column, 11=sparse
        text = pytesseract.image_to_string(img, config=f'--psm {psm}')
```

Stop when extracted text exceeds minimum length threshold (e.g., 10 chars).

## Pattern Matching Priorities

When multiple date/price formats exist, establish priority:

| Field | Priority Order | Example Patterns |
|-------|---------------|------------------|
| Dates | EXPIRY > EXPIRES > MFG | `EXP[:\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{4})` |
| Prices | Labeled PRICE > Raw currency | `PRICE:\s*RM\s+(\d+\.\d{2})` > `RM\s+(\d+\.\d{2})` |

## Output precision

Never round, truncate, or fixed-format numeric values when writing outputs
(Excel cells, JSON, CSV). Pass raw float values directly. Concretely:
- DO NOT: `round(x, N)`, `format(x, ".2f")`, `f"{x:.2f}"`, `.toFixed(N)`
- DO: `ws.cell(row=r, column=c, value=x)` with x as a raw float
- The verifier's tolerance (often 1e-4) decides acceptable precision; the
  skill's job is to give it full precision and let it decide.

## Common Pattern Templates

See `references/patterns.md` for ready-to-use regex collections for:
- Dates (DD/MM/YYYY, MM-YYYY, YYYY/MM variations)
- Prices (RM, $, MYR, EUR, GBP with optional "EACH"/"PER" suffixes)
- Product codes and identifiers

## Validation Checklist

- [ ] All input images processed (no silent skips)
- [ ] Output sorted by meaningful key (usually filename or date)
- [ ] Date format normalized to ISO (YYYY-MM-DD)
- [ ] Price format normalized (2 decimal places)
- [ ] Missing values explicitly logged, not silently blank

## Anti-Patterns

- **Don't** rely on single preprocessing method - image quality varies unpredictably
- **Don't** assume consistent date format - same dataset may contain DD/MM and MM/DD
- **Don't** parse price without currency context - $10 vs RM10 are different values
- **Don't** skip verification of output row count against input file count

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Empty/missing extractions | OCR failed on poor contrast | Add more aggressive binarization thresholds |
| Dates in wrong century | 2-digit year ambiguity | Prefer 4-digit year patterns; validate year ranges |
| Prices with wrong decimals | OCR misread '.' as ',' | Normalize decimal separator; validate numeric range |
| Inconsistent row counts | Some images skipped | Add explicit error handling; log all processing attempts |

## Script Reference

For batch extraction jobs, use `scripts/extract_from_images.py` as a starting template. It implements the full pipeline with configurable patterns and outputs to Excel.