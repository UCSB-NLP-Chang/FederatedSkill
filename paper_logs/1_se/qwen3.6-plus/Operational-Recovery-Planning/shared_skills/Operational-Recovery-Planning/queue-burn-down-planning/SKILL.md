---
name: queue-burn-down-planning
description: Generates a deterministic weekly staffing and queue burn-down plan from a reference Excel file containing demand loads. Use when tasked with computing capacity, overtime, backlog recovery, or staffing transitions based on demand vs. capacity thresholds across any domain (e.g., SOC alerts, radiology reads, manufacturing).
---

# Queue Burn-Down Planning

## When to Use
- Task requires generating a weekly workforce/queue recovery plan from an Excel source.
- Input contains weekly demand values, an initial backlog, and explicit capacity/threshold rules.
- Output must include a detailed weekly Excel plan and a summary text file with phase transition weeks.

## Workflow
1. **Extract Parameters**: Identify from the task prompt or Excel file:
   - Initial backlog value.
   - Demand row label(s). If demand is split across multiple rows (e.g., Standard + Exception), list all labels.
   - Capacity & OT values for 6-day, 5-day, and 4-day phases.
   - Demand threshold that triggers phase transitions.
   - **Exact output headers and summary phrasing** from the prompt.
2. **Run Deterministic Policy**: Execute `scripts/generate_plan.py` with extracted parameters. Pass exact headers via `--headers` and summary text via `--summary_line3` if they differ from defaults. Use `--demand_labels` for composite demand.
3. **Verify Outputs**:
   - Excel: Confirm worksheet name is `Plan`, contains exactly N rows (matching input weeks), and matches required headers exactly.
   - Text: Confirm 3 lines, including `First_Week_5_Days` and `First_Week_4_Days`.
   - Check for gaps, duplicates, or negative week numbers.
   - Validate `SoW = max(0, prev_EoW)` and `EoW = SoW + Demand - Capacity`.
   - Cross-check summary wording against the prompt's exact phrasing.

## Policy Rules (Deterministic)
- **Phase 1 (Backlog Burn-down)**: 6 days/week. Continues until `EoW <= 0`.
- **Phase 2 (Stabilization)**: 5 days/week. Activates when `Demand > Threshold`.
- **Phase 3 (Minimal Staffing)**: 4 days/week. Activates when `Demand <= Threshold`.
- **Spike Handling**: If `Demand > Threshold` during Phase 3, temporarily revert to 5 days/week for that week only.
- **Queue Math**: `SoW = max(0, prev_EoW)`, `EoW = SoW + Demand - Capacity`. Negative `EoW` is valid (buffer). Do not clamp.

## Verifier & Output Matching
- **Exact Headers**: Verifiers strictly check column names. Extract the exact 7 headers from the prompt and pass them as a comma-separated string to `--headers`.
- **Summary Phrasing**: The 3rd line of the summary must match the prompt's requested wording exactly. Pass it to `--summary_line3`.
- **Week Range**: Ensure the output covers exactly the weeks specified in the prompt. Do not pad or truncate.
- **Composite Demand**: If the prompt specifies demand as a sum of multiple rows, pass them as a comma-separated list to `--demand_labels`. The script will sum them automatically.

## Anti-Patterns
- Do not hardcode week numbers; compute transitions dynamically based on demand vs capacity.
- Do not clamp `EoW` to 0; negative values indicate surplus capacity.
- Do not use `pandas` if `openpyxl` is required for formatting preservation.
- Do not assume fixed capacities/thresholds or default headers; always extract them from the task context.
- Do not ignore "Do Not Use" rows in the source Excel; verify which rows constitute actual demand.

## Scripts & References
- Run `scripts/generate_plan.py` with domain-specific parameters to generate deliverables deterministically. Use `--headers`, `--summary_line3`, and `--demand_labels` to match verifier expectations.
- See `references/policy_rules.md` for formula derivations, threshold definitions, and edge-case handling.