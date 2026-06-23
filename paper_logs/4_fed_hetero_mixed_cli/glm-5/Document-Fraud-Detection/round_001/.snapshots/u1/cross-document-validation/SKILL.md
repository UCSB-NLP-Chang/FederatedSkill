---
name: cross-document-validation
description: Validate and reconcile data across multiple source files in different formats (Excel, CSV, PDF). Use when tasks require cross-referencing records between datasets, identifying discrepancies, or screening claims against master records.
---

# Cross-Document Data Validation

## When to Use
- Validating expense claims against employee directories and approval records
- Reconciling transactions between systems
- Screening submitted data against master reference files
- Any task requiring data matching across Excel, CSV, or PDF sources

## File Format Handling

| Format | Tool | Notes |
|--------|------|-------|
| `.xlsx`, `.xls` | Python/pandas | Read tool fails on binary Excel files |
| `.csv` | Read tool | Works directly |
| `.pdf` | Read tool | Returns text content or base64 |

### Reading Excel Files
```bash
python3 -c "import pandas as pd; df = pd.read_excel('/path/to/file.xlsx'); print(df.to_string())"
```

## Validation Workflow

1. **Load all reference data first** - employee directories, approval lists, master records
2. **Build lookup structures** - map IDs to names, accounts, approved amounts
3. **Process each claim/record** - extract fields from PDF or input documents
4. **Run validation checks** in order:
   - Entity exists in reference (employee/customer/vendor found)
   - Account/identifier matches registered value
   - Referenced IDs exist in approval/reference tables
   - Amounts match approved limits
   - Cross-references are consistent (trip belongs to correct employee)
5. **Output flagged records** with specific reason codes

## Common Validation Checks

| Check Type | Description | Example |
|------------|-------------|----------|
| Unknown Entity | Name/ID not in master records | Employee not in directory |
| Account Mismatch | Bank/account differs from registered | Claim shows WRONG-222, directory has ACCT-002 |
| Invalid Reference | Referenced ID not found | Trip ID not in approvals |
| Amount Mismatch | Claimed differs from approved | $1,500.75 vs $1,520.75 |
| Traveler Mismatch | Reference belongs to different entity | Trip assigned to E103, claimed by E104 |

## Anti-Patterns

- **Do not use Read tool on `.xlsx` files** - they are binary and will fail
- **Do not assume exact name matching** - watch for typos ("Dana Kapor" vs "Dana Kapoor")
- **Do not skip building lookup tables** - repeated linear searches are slow and error-prone

## Output Format

Return flagged records as structured JSON with fields:
- `claim_page_number` or record identifier
- `employee_name` or entity name
- `claimed_amount` or relevant values
- `reason` - specific discrepancy description

## Scripts

Use `scripts/validate_claims.py` as a template for expense claim validation tasks.

## References

- `references/fuzzy-matching-guide.md` - Algorithm details for name matching with typo tolerance
