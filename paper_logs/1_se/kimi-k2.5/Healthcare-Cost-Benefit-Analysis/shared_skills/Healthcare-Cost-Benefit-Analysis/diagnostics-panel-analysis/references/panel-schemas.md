# Diagnostics Panel Schema Variants

## Standard Panel Manifest Structure

```json
{
  "service_clusters": [
    {
      "cluster_name": "core|specialty|regional|...",
      "panels": [
        {
          "panel_code": "DP-XXX",
          "panel_name": "Panel Display Name",
          "alias_labels": ["ALIAS ONE", "Alias-One"],
          "reagent_cost_per_1000_tests_usd": 0.0,
          "network_tier": "metro|regional|rural",
          "shipper_class": "ambient_lab|cold_lab|frozen_lab",
          "tests_per_lab_per_run_14_day": 0,
          "tests_per_lab_per_run_28_day": 0,
          "default_active_labs": 0,
          "analysis_mode": "review|archive"
        }
      ]
    }
  ]
}
```

## Common Variations

### Field Name Alternatives
| Standard | Alternative | Notes |
|----------|-------------|-------|
| `panel_code` | `test_id`, `assay_id` | Same semantics |
| `panel_name` | `test_name`, `display_name` | Same semantics |
| `alias_labels` | `aliases`, `known_as` | Same semantics |
| `analysis_mode` | `review_flag`, `status` | `review`/`archive` or `active`/`inactive` |
| `network_tier` | `tier`, `region_type` | metro/regional/rural |

### Network Tier Adjustments
| Tier | Typical Adjustment | Characteristics |
|------|-------------------|-----------------|
| metro | ~$1.40 | Dense, low transport cost, higher negotiated rates |
| regional | ~$2.10 | Medium density, moderate transport |
| rural | ~$0.80 | Sparse, high transport cost, lower rates |

### Shipper Classes
| Class | Typical Cost | Use Case |
|-------|-------------|----------|
| ambient_lab | ~$14-15 | Standard reagents, room temperature |
| cold_lab | ~$19-20 | Refrigerated transport, 2-8°C |
| frozen_lab | ~$24-25 | Frozen, -20°C or dry ice |

## Holdouts Structure

```json
{
  "holdouts": [
    {
      "panel_code": "DP-XXX",
      "holdout_state": "exclude|clear"
    }
  ]
}
```

### Exclusion Rules
- `holdout_state: "exclude"` → Remove from analysis entirely
- `holdout_state: "clear"` or missing → Include normally
- Holdouts are by `panel_code`, not `panel_name`

## Contract Terms Structure

```csv
panel_ref,status_flag,effective_week,base_payment_per_run_per_lab_usd
ALIAS NAME,current,2026-W10,18.20
ALIAS NAME,current,2026-W22,19.10
OTHER ALIAS,superseded,2026-W05,15.00
```

### Matching Priority
1. Normalize `panel_ref` (lowercase, remove hyphens/spaces)
2. Match against normalized `panel_name` or `alias_labels` entries
3. Filter to `status_flag: "current"` only
4. Select latest `effective_week` (lexicographic works for ISO week format)

### Payment Calculation
```
total_payment = base_payment_per_run_per_lab_usd + network_adjustment_per_run_per_lab_usd
```

## Override Structure Patterns

### Standard Lab Override
```csv
panel_code,rev,approval,active_labs
DP-ALPHA,1,approved,16
DP-ALPHA,2,approved,17
DP-BETA,1,approved,
DP-GAMMA,1,draft,9
```

### Empty Value Handling
If `active_labs` is blank/null:
- Fall back to `default_active_labs` from manifest
- Do NOT treat as 0 or error

## Run Frequency Calculations

| Cadence | Runs/Year | Calculation |
|---------|-----------|-------------|
| 14-day | 26 | 365/14 ≈ 26.07 |
| 28-day | 13 | 365/28 ≈ 13.04 |

Rounding: Typically floor or nearest integer; verify task requirements.

## Scenario Naming Conventions

| Scenario A | Scenario B | Output Pattern |
|------------|-----------|----------------|
| 14_day | 28_day | `adopt_14_day` / `adopt_28_day` |

**Critical**: This domain consistently uses `adopt_X_day` rather than `keep_X_day`/`switch_to_X_day`.

## Calculation Verification

When margins are unexpectedly negative:
1. Verify network adjustment is ADDED to base payment
2. Check shipper_cost lookup by `shipper_class`
3. Confirm reagent cost: tests × runs × labs × cost_per_1000 / 1000
4. Verify runs_per_year: 26 for 14-day, 13 for 28-day
5. Check lab counts: overrides with empty value handling
6. Ensure holdout exclusions removed wrong panels, not right ones
