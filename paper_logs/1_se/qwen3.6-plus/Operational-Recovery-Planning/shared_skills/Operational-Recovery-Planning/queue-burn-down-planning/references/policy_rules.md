# Queue Burn-Down Policy Rules

## Capacity & Overtime Thresholds
- **6-Day Phase**: Used exclusively for backlog burn-down. Continues until `EoW <= 0`.
- **5-Day Phase**: Used when weekly demand exceeds the configured threshold.
- **4-Day Phase**: Used when weekly demand is ≤ the configured threshold.
- Capacities and OT hours are fixed per phase and defined by task context.

## Queue Mathematics
- `Start-of-Week (SoW) = max(0, Previous End-of-Week)`
- `End-of-Week (EoW) = SoW + Demand - Capacity`
- Negative `EoW` values are valid and represent surplus capacity (buffer). Do not clamp to 0.
- Overtime is fixed per phase, not dynamically calculated from excess demand.

## Transition Logic
1. Start in 6-Day phase. Remain until `EoW <= 0`.
2. Switch to 5-Day phase. Remain while `Demand > Threshold`.
3. Switch to 4-Day phase when `Demand <= Threshold`.
4. **Exception**: If `Demand > Threshold` occurs during 4-Day phase, temporarily revert to 5-Day for that week only.

## Data Mapping
- `Demand` maps directly to the specified demand row/column from the source Excel.
- Initial backlog defaults to task-specified value.
- Week numbers are 1-indexed integers. Ensure no gaps or duplicates in output.