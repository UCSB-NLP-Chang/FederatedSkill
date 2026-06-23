---
name: nested-document-extraction
description: Extract structured data from images in nested directories, classify/filter by document type, derive metadata from paths, normalize OCR artifacts in IDs, and export to Excel. Use when tasked with processing batched folders of mixed documents (receipts, forms, notes) where only specific types should be kept, and path structure implies metadata like batch or region.
---

# Nested Document Extraction & Classification

## Workflow
1. **Recursive Discovery**: Use `glob("**/*.jpg")` or `os.walk` to find all images. Compute `relative_path` relative to the dataset root immediately using `os.path.relpath()`.
2. **OCR & Classification**:
   - Run OCR on each image.
   - Check for target keywords (e.g., `FUEL RECEIPT`, `TAX INVOICE`, `PUMP SALE`).
   - **Filter**: Discard non-target documents (e.g., cover sheets, promos, loyalty forms, route notes). Do not include them in the output.
3. **Field Extraction & Normalization**:
   - Extract `txn_ref`, `date`, `amount`.
   - **OCR Artifact Fix**: Transaction IDs frequently suffer `O`/`0` confusion. If the ID format implies digits (e.g., `FUEL-N-001`), replace `O` with `0`. Validate against expected patterns.
   - **Dates**: Normalize to `YYYY-MM-DD`. Handle `DD/MM/YYYY`, `MM/DD/YYYY` (day > 12 implies month), `DD-MM-YYYY`, and ISO.
   - **Amounts**: Strip symbols, format to exactly 2 decimal places.
4. **Path Metadata**: Derive `batch_name` from the immediate parent directory or top-level folder name as specified by the task.
5. **Export**: Write to a single Excel sheet. Columns typically: `batch_name`, `relative_path`, `txn_ref`, `date`, `total_amount`. Sort by `relative_path` or `batch_name` if required.
6. **Verify**: Run `scripts/verify_nested.py <output.xlsx> [col1,col2,...]` to validate schema, date formats, and path consistency.

## Critical Anti-Patterns
- **NEVER hardcode extracted values.** Always loop over discovered files.
- **Do not skip classification.** Mixed batches contain distractors. Include only documents matching the target type.
- **Do not trust raw OCR for IDs.** `O` vs `0` and `I` vs `1` are common. Apply deterministic normalization (e.g., `re.sub(r'O', '0', ref)` if pattern matches).
- **Do miscalculate relative paths.** Use `os.path.relpath(img, root_dir)` to ensure consistency across environments.
- **Do not assume uniform date formats.** Apply disambiguation rules (day > 12 -> MM/DD).

## Troubleshooting
- **Verifier fails on IDs**: Check for `O`/`0` or `I`/`1` substitutions. Normalize before writing.
- **Missing rows**: Ensure classification keywords are broad enough to catch variants (`PUMP SALE`, `TAX INVOICE`, `RECEIPT`).
- **Path mismatch**: Verify `relative_path` does not include leading `./` or absolute prefixes.
