---
name: case-settlement-extraction
description: Extract, classify, deduplicate, and aggregate financial/legal documents from nested case directories into an events log and net settlement summary. Use when processing case packets containing mixed document types (purchases, credits, admin pages) requiring OCR artifact repair, duplicate removal by reference ID, and net amount calculation per case.
---

# Case Settlement Packet Processing

## Workflow
1. **Recursive Discovery & Sorting**: Find all images in the case directory. Sort paths to ensure deterministic processing.
2. **OCR & Text Normalization**:
   - Run OCR on each image. Join lines into a single string.
   - **Fix Split Words**: Apply regex to rejoin common OCR splits (e.g., `CRE\s+DIT` -> `CREDIT`, `IN\s+VOICE` -> `INVOICE`).
   - **Fix ID Artifacts**: Normalize `O`/`0` confusion in reference IDs (e.g., `PUR-A-OO1` -> `PUR-A-001`).
3. **Classification & Filtering**:
   - Check normalized text against target keywords (e.g., `PURCHASE RECEIPT`, `CREDIT NOTE`).
   - **Exclude Distractors**: Explicitly skip admin pages (checklists, cover sheets, thank-you notes, route guides).
4. **Deduplication**:
   - Extract `document_ref` (e.g., `PUR-A-001`).
   - Maintain a `seen_refs` set per case/group. If a ref is already seen, skip the document to avoid double-counting.
5. **Field Extraction**:
   - **Amounts**: Use a two-stage regex.
     - Primary: `KEYWORD\s*(?::\s*)?([\d,]+\.?\d*)`
     - Fallback: `KEYWORD.*?([\d,]+\.\d{2})\b` (requires decimal point to prevent matching dates/years like `2024`).
   - **Dates**: Normalize to `YYYY-MM-DD`. Handle ambiguous `DD/MM` vs `MM/DD` by checking if day > 12.
6. **Aggregation & Export**:
   - **Events Sheet**: One row per valid, non-duplicate document. Columns: `case_id`, `relative_path`, `document_type`, `document_ref`, `date`, `amount`. Sort by `case_id`, then `relative_path`.
   - **Net Summary Sheet**: Group by `case_id`. Calculate `purchase_total` (sum of purchases), `credit_total` (sum of credits), `net_amount` (`purchase_total - credit_total`), and `latest_date` (max date). Columns: `case_id`, `purchase_total`, `credit_total`, `net_amount`, `latest_date`.
7. **Verification**: Validate row counts, schema, and aggregation math. Ensure `net_amount` matches `purchase_total - credit_total`.

## Critical Anti-Patterns
- **Do not skip OCR normalization.** Split words and `O`/`0` confusion will break classification and deduplication.
- **Do not ignore duplicates.** Case packets often contain duplicate scans. Deduplicate by reference ID *before* aggregation.
- **Do not use greedy amount regexes without decimal checks.** Fallback patterns like `.*?(\d+)` will match years or dates. Require `\.\d{2}` in fallbacks.
- **Do not mix purchase and credit totals.** Keep them separate in the summary until calculating `net_amount`.
- **Do not include admin pages.** They lack financial data and will skew counts if not filtered.

## Troubleshooting
- **Wrong amount extracted**: Check if the regex matched a date or year. Enforce decimal requirement in fallback patterns.
- **Missing documents**: Verify classification keywords cover all variants. Check OCR normalization for split keywords.
- **Duplicate rows in summary**: Ensure deduplication happens *before* aggregation. Use a `seen_refs` set per case.
- **Net amount mismatch**: Verify `net_amount = purchase_total - credit_total`. Check for sign errors (credits should be positive in `credit_total` but subtracted for net).
