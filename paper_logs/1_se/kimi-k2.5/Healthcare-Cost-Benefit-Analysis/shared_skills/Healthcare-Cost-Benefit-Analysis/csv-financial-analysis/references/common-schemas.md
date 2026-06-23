# Common Schema Variants

Schema patterns encountered across financial analysis tasks.

## Therapy/Medication Naming

| Domain | Item Key | Example Values |
|--------|----------|---------------|
| Pharmacy refill cycles | `therapy` | "Albuterol", "Fluticasone" |
| Medication sync programs | `medication` | "Escitalopram 10mg", "Lamotrigine 100mg" |

**Rule:** Match the exact key name from the task schema or input files.

## Scenario Identifier Patterns

### Refill Cycles (30/90 day)
```json
{
  "recommendation": {
    "enum": ["keep_30_day", "switch_to_90_day"]
  }
}
```

### SyncPack Cycles (28/56 day)
```json
{
  "recommendation": {
    "enum": ["keep_28_day", "switch_to_56_day"]
  }
}
```

### Generic Pattern
```
keep_{scenario_a} / switch_to_{scenario_b}
```

**Critical:** Never use `convert_to` unless explicitly specified. Verifiers typically expect `switch_to`.

## Cost Column Variants

| Concept | Common Column Names |
|---------|---------------------|
| Unit acquisition cost | `price_per_1000_doses_usd`, `price_per_1000_capsules_usd`, `price_per_1000_tablets_usd` |
| Packaging cost | `packaging_cost_usd`, `card_cost_usd` |
| Reimbursement | `reimbursement_per_fill_{n}_patients_usd`, `reimbursement_per_cycle_{n}_patients_usd` |

## Calculation Constants

### Fill Frequencies
| Days | Fills/Year | Typical Use |
|------|-----------|-------------|
| 28 | 12 | Monthly medication sync |
| 30 | 12 | Standard monthly |
| 56 | 6 | Bi-monthly sync |
| 90 | 4 | Quarterly |
| 100 | 3.65→3 | Some specialty pharma |

### Formula: `fills_per_year = round(365 / days_per_fill)` or use exact fraction