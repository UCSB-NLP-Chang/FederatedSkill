# Logistics Dispatch Schema Variants

## Standard Program/Campaign Structure

```json
{
  "service_groups": [
    {
      "group_name": "antiemetic|supportive|...",
      "programs": [
        {
          "program_code": "ONC-XXX",
          "program_name": "ProgramName",
          "known_labels": ["LABEL ONE", "Label-One"],
          "acquisition_cost_per_1000_units_usd": 0.0,
          "units_per_day": 0,
          "cooler_type": "small_cold|large_cold|portable|secure",
          "default_active_sites": 0,
          "analysis_flag": "review|archive"
        }
      ]
    }
  ]
}
```

## Campaign Variant (Vaccination/Outreach)

```json
{
  "regions": [
    {
      "region": "north|south|...",
      "campaigns": [
        {
          "campaign_id": "VAX-XXX",
          "campaign_name": "Campaign Name",
          "alias_labels": ["ALIAS ONE", "Alias-One"],
          "drug_cost_per_1000_doses_usd": 0.0,
          "doses_per_day": 0,
          "crate_tier": "portable|secure",
          "default_active_clinics": 0,
          "analysis_flag": "review|archive"
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
| `program_code` | `campaign_id` | Same semantics |
| `program_name` | `campaign_name` | Same semantics |
| `known_labels` | `alias_labels` | Same semantics |
| `units_per_day` | `doses_per_day` | Consumption rate |
| `cooler_type` | `crate_tier`, `container_type` | Join key for cost lookup |
| `default_active_sites` | `default_active_clinics` | Same semantics |
| `analysis_flag` | `review_flag` | Scope filter |

### Scope Flags
- `analysis_flag: "review"` / `review_flag: "review"` - Include in analysis
- `analysis_flag: "archive"` / `review_flag: "archive"` - Exclude from analysis
- `status: "active"` / `"inactive"` - Alternative flag pattern

## Suspension Exclusions

### suspensions.csv Structure
```csv
campaign_id,suspension_status
VAX-ZETA,hold
VAX-ARCH,clear
```

### Exclusion Rules
- `suspension_status: "hold"` → Exclude from analysis
- `suspension_status: "clear"` / missing → Include normally
- Only exclude if suspensions.csv file exists

## Override Structure Patterns

### Standard Site Override
```csv
program_code,version_no,approval_state,active_sites
ONC-ALFA,1,draft,13
ONC-ALFA,2,approved,15
ONC-BETA,1,approved,12
```

### Alternative Naming
| Standard | Alternative |
|----------|-------------|
| `version_no` | `revision`, `version` |
| `approval_state` | `status`, `approval_status` |
| `active_sites` | `active_clinics`, `sites`, `site_count` |

### Handling Empty Values
If `active_sites` is blank/null:
1. Fall back to `default_active_sites` from catalog
2. Log warning if no default available

## Payment/Billing Structure Patterns

```csv
campaign_label,status,cycle_tag,payment_per_dispatch_per_clinic_usd
ALPHA FLU,active,2026-Q2,13.10
Gamma Lane,inactive,2026-Q4,12.00
Gamma Lane,active,2026-Q2,12.80
```

### Payment Matching Priority

When `campaign_label` in billing CSV doesn't match `campaign_id`:

1. Exact match: `campaign_name`/`program_name`
2. Case-insensitive match: any element in `alias_labels`/`known_labels` array
3. Normalized match: whitespace-collapsed, case-insensitive

### Multiple Active Entries
- Filter to `status: "active"` entries only
- Use latest `cycle_tag`/`effective_month` (lexicographic or date parse)
- Or use highest payment if task specifies

## Container/Cooler Cost Patterns

| Type | Typical Cost | Use Case |
|------|-------------|----------|
| small_cold | ~$8-11 | Standard cold chain |
| large_cold | ~$10-13 | High-volume cold chain |
| portable | ~$7-8 | Mobile/vaccination outreach |
| secure | ~$11-12 | Controlled substances, high-value |

## Dispatch Frequency Calculations

| Days | Dispatches/Year | Formula | Common Use |
|------|-----------------|---------|------------|
| 6 | 60 | 365/6 ≈ 60.8→60 | Frequent vaccination outreach |
| 7 | 52 | 365/7 ≈ 52 | Weekly |
| 10 | 36 | 365/10 = 36.5→36 | Bi-weekly approx |
| 12 | 30 | 365/12 ≈ 30 | Bi-weekly vaccination |
| 14 | 26 | 365/14 ≈ 26 | Bi-weekly |
| 20 | 18 | 365/20 = 18.25→18 | ~3/week |
| 30 | 12 | 365/30 ≈ 12 | Monthly |

**Rounding**: Check task for explicit rounding rules; common patterns are floor (36.5→36) or nearest (36.5→37).

## Scenario Naming Conventions

| Scenario A | Scenario B | Output Pattern | Notes |
|------------|-----------|----------------|-------|
| 6_day | 12_day | `keep_6_day` / `switch_to_12_day` | Vaccination dispatch |
| 10_day | 20_day | `keep_10_day` / `switch_to_20_day` | Oncology cooler |
| 7_day | 14_day | `keep_7_day` / `switch_to_14_day` | Weekly logistics |

May include `_dispatch` suffix: `keep_6_day_dispatch` / `switch_to_12_day_dispatch`

**Critical**: Verify exact enum values from task schema - `switch_to` vs `move_to` vs `adopt`.

## Calculation Verification

When margins are unexpectedly negative:
1. Verify drug cost calculation: units_per_day × 365 × sites × cost_per_1000 / 1000
2. Check container cost scales correctly: fewer dispatches should reduce costs proportionally
3. Confirm payment covers both container costs and contributes to margin
4. Verify site counts: overrides (including empty value handling) and defaults
5. Check suspension exclusions didn't remove wrong campaigns
