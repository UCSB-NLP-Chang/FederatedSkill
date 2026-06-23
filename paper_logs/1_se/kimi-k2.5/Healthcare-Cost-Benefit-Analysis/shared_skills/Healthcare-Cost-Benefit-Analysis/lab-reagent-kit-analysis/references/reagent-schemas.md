# Reagent Kit Schema Variants

## Standard Assay Manifest Structure

```json
{
  "regions": [
    {
      "region": "central|specialty|...",
      "assays": [
        {
          "assay_id": "CHEM-XXX",
          "assay_name": "Assay Name",
          "aliases": ["ALIAS ONE", "Alias-One"],
          "reagent_price_per_1000_tests_usd": 0.0,
          "carrier_type": "ambient_small|cold_chain|frozen",
          "tests_per_lab_per_run_small": 0,
          "tests_per_lab_per_run_bulk": 0,
          "default_active_labs": 0,
          "in_scope": true|false
        }
      ]
    }
  ]
}
```

## Common Variations

### Pricing Units
| Field | Alternative | Notes |
|-------|-------------|-------|
| `reagent_price_per_1000_tests_usd` | `price_per_1000_tests`, `cost_per_1000` | Same semantics |
| `tests_per_lab_per_run_small` | `tests_small`, `small_kit_tests` | Tests per run for small-kit policy |
| `tests_per_lab_per_run_bulk` | `tests_bulk`, `bulk_kit_tests` | Tests per run for bulk-kit policy |

### Carrier Types
| Type | Typical Cost | Use Case |
|------|-------------|----------|
| `ambient_small` | ~$18-20 | Standard temperature, small shipments |
| `cold_chain` | ~$24-26 | Refrigerated transport |
| `frozen` | ~$29-31 | Frozen reagents, dry ice |

### Scope Flags
- `in_scope: true/false` - Boolean filter (most common)
- `status: "active"` / `"inactive"` - Alternative flag pattern

## Override Structure Patterns

### Standard Lab Override
```csv
assay_id,revision,status,active_labs
CHEM-ION,1,draft,11
CHEM-ION,2,approved,13
CHEM-LIVER,1,approved,9
```

### Alternative Naming
| Standard | Alternative |
|----------|-------------|
| `revision` | `version`, `rev_no` |
| `status` | `state`, `approval_status` |
| `active_labs` | `labs`, `lab_count`, `sites` |

## Billing Structure Patterns

```csv
assay_label,effective_month,is_active,payment_per_run_per_lab_usd
ION BAL PANEL,2026-01,true,16.20
Ion Panel,2026-03,true,17.40
```

### Payment Matching Priority

When `assay_label` in billing CSV doesn't match `assay_id`:

1. Exact match: `assay_name`
2. Case-insensitive match: any element in `aliases` array
3. Normalized match: whitespace-collapsed, case-insensitive

### Multiple Active Entries
- Use latest `effective_month` where `is_active: true`
- Or use highest payment if task specifies

## Run Frequency Patterns

| Policy | Runs/Year | Tests/Run | Typical Use |
|--------|-----------|-----------|-------------|
| small-kit | 24 | Lower | Frequent restocking, lower per-lab volume |
| bulk-kit | 12 | Higher | Infrequent restocking, consolidated shipments |

## Scenario Naming Conventions

| Scenario A | Scenario B | Output Pattern |
|------------|-----------|----------------|
| small_kit | bulk_kit | `keep_small_kit` / `adopt_bulk_kit` |
| 24_run | 12_run | `keep_24_run` / `switch_to_12_run` |
| frequent | infrequent | `keep_frequent` / `switch_to_infrequent` |

## Calculation Verification

When margins are unexpectedly negative:
1. Verify reagent cost calculation: tests × runs × labs × price_per_1000 / 1000
2. Check carrier cost scales correctly: fewer runs should reduce carrier costs proportionally
3. Confirm payment scales with runs: revenue should decrease with fewer runs
4. Verify lab counts: overrides may significantly change volumes
5. Ensure `tests_per_lab_per_run_bulk` > `tests_per_lab_per_run_small` (typically 2x)
