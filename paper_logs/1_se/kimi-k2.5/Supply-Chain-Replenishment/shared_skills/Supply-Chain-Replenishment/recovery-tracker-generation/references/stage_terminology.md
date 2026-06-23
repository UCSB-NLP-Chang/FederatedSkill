# Stage Terminology for Recovery Tracking

## Industry-Specific Stage Values

### Retail/Food Recovery
| Stage | Meaning | Include? |
|-------|---------|----------|
| Booked | Scheduled, firm commitment | ✓ |
| Loaded | Physically prepared/staged | ✓ |
| In Transit | Shipped, en route | ✓ (treat as Loaded) |
| Received | Arrived at destination | ✓ (treat as Loaded) |
| Tentative | Possible, not confirmed | ✗ |
| Cancelled | Explicitly voided | ✗ |
| On Hold | Suspended | ✗ |
| Draft | Being prepared | ✗ |

### Logistics/Shipping
| Stage | Meaning | Include? |
|-------|---------|----------|
| Confirmed | Alternative for Booked | ✓ |
| Arranged | Scheduled | ✓ |
| Committed | Firm booking | ✓ |
| Pending | Awaiting confirmation | ✗ |
| Proposed | Suggested | ✗ |

### Healthcare/Pharmaceutical Transfers
| Stage | Meaning | Include? |
|-------|---------|----------|
| Confirmed | Approved transfer | ✓ |
| Scheduled | Date set | ✓ |
| Requested | Awaiting approval | ✗ |
| Cancelled | Voided | ✗ |

## Revision-Based Deduplication

### When to Use
Use revision-based deduplication when:
- Data source is a recovery log or booking system
- Multiple entries for same Load_ID with version tracking
- Revision column present (integer or version string)

### Algorithm
```python
# Keep highest revision per Load_ID
deduped = df.loc[df.groupby('Load_ID')['Revision'].idxmax()]

# Then filter stages
confirmed = deduped[deduped['Stage'].isin(['Booked', 'Loaded'])]
```

### Contrast: Date-Based Deduplication
Use date-based (keep latest) when:
- Transfer schedules with duplicate Transfer_IDs
- No revision column, only dates
- See `excel-load-planning/references/variant_patterns.md` for Transfer variant
