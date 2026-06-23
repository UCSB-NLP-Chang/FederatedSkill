---
name: production-scheduling-excel
description: Generates multi-scenario daily production schedules and capacity plans in Excel, handling calendar constraints, capacity ramps, PO deadlines, and shared resources. Use when tasked with distributing demand across workdays, respecting start dates/holidays/capacity limits, and producing validated Excel workbooks with mixed constants/formulas and structured markdown summaries.
---

# Production Scheduling & Capacity Planning

## When to Use
- Task requires distributing a fixed demand/PO quantity across a date range.
- Constraints include workdays, holidays, capacity limits, ramp-up phases, or start dates.
- Output must be an Excel workbook with multiple scenario sheets, mixed constants/formulas, and a structured summary.
- Multiple products share a timeline but have independent capacity rules, start dates, or shift extensions.

## Workflow
1. **Extract Constraints**: Identify from prompt/input:
   - Date range, weekends, holidays.
   - Daily capacity limits per product/resource, including phase transition dates and **temporary override windows**.
   - Start dates, ramp-up dates, PO due dates & quantities.
   - Shared capacity rules (if products compete).
   - **Exact output headers, sheet names, and summary phrasing** from the prompt. Copy-paste exactly; trim whitespace.
2. **Scaffold with Script**: Run `scripts/generate_schedule.py` with a JSON config to generate the base calendar, constraint-aware distribution, and Excel structure. Adapt the scenario loop for domain-specific rules rather than writing ad-hoc inline scripts.
3. **Distribute Demand**: Allocate production per workday:
   - `0` before start dates.
   - Respect daily capacity caps per product/phase.
   - Use base + remainder distribution to hit exact totals.
   - Verify cumulative production meets PO deadlines.
4. **Build Excel**:
   - Use `openpyxl`. Write dates as `datetime.date` objects or `=B4+1` formulas.
   - Keep daily production as numeric constants.
   - Use formulas for cumulative/open/remaining columns. Avoid circular references.
   - Place PO due quantities on exact matching date rows; `0` elsewhere.
   - Name sheets exactly as requested.
5. **Generate Summary**: Write markdown with required sections, impact fields, and on-time status.
6. **Validate & Align**: Run constraint checks. Read the saved workbook back with `openpyxl` to verify exact string/number matches, date types, and formula placement before submission.

## Key Decision Rules
- **If validation fails on totals**: Check remainder distribution logic. Ensure `sum(base * days + remainder) == target`.
- **If Excel formulas break**: Do not rely on `data_only=True` for chained formulas. Write simple, non-circular formulas or use constants for verification.
- **If PO deadlines missed**: Front-load production or adjust capacity allocation to meet cumulative targets by due dates.
- **If datetime vs date mismatch**: `openpyxl` reads date cells as `datetime.datetime`. Always call `.date()` before comparing with `datetime.date` in Python validation. When writing, use `datetime.date` objects to avoid time components.
- **If multi-product capacity phases differ**: Compute capacity limits dynamically per row based on the current date and product-specific phase rules. Do not assume all products transition on the same date.
- **If temporary capacity windows exist**: Build a date-to-capacity lookup map. Apply overrides during daily iteration. Do not split the calendar into rigid segments if windows overlap or vary by product.
- **If self-validation fails on dates**: Compute expected dates dynamically from the calendar rather than hardcoding them.

## Verifier Alignment
- **Exact Headers & Sheet Names**: Verifiers strictly check column names and sheet titles. Extract them verbatim from the prompt.
- **Date Formatting**: Ensure Excel dates match the verifier's expected format (usually `YYYY-MM-DD` or locale-specific). Write `datetime.date` objects, not strings, unless explicitly requested.
- **Formula vs Constant Columns**: If the prompt specifies which columns must be constants vs formulas, enforce this strictly. Read back the workbook and check `cell.value` type (string starting with `=` vs numeric).
- **Summary Phrasing**: Match the prompt's exact wording for status lines (e.g., "May PO On-Time: No"). Do not paraphrase.

## Anti-Patterns
- Do not write ad-hoc inline Python for calendar generation; use `scripts/generate_schedule.py` as a scaffold.
- Do not use `data_only=True` to validate complex formula chains; Excel won't recalculate them.
- Do not create circular references in Excel (e.g., `A = B - C` and `B = A + C`).
- Do not assume all days are workdays; explicitly filter weekends & holidays.
- Do not hardcode day counts; compute dynamically from the calendar.
- Do not mix `datetime` and `date` objects in assertions.
- Do not assume PO due values belong in a separate column; place them inline on the matching date row if required, or verify exact column mapping from the prompt.
- Do not guess header casing or sheet names; verifiers fail on exact string mismatches.

## Scripts & References
- Run `scripts/generate_schedule.py` with a JSON config to scaffold calendar generation, constraint-aware distribution, and Excel writing. Adapt the scenario loop for domain-specific rules.
- See `references/constraint_patterns.md` for handling PO deadlines, capacity ramps, shared resources, multi-product phase transitions, temporary capacity windows, formula safety patterns, and verifier alignment strategies.