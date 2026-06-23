# Domain Variant Patterns

Reference for domain-specific patterns in queue recovery simulations (B1) and daily production recovery (B2).

## B1 Domain Variants

### SOC (Service Operations Center)
- **Weeks**: 40 weeks
- **Daily capacity**: 28 hours/day
- **Step-down threshold**: 4-day threshold (transition from 6→5→4 days)
- **Output format**: Excel with SOC-specific headers

### Radiology
- **Weeks**: 49 weeks (weeks 6-54)
- **Daily capacity**: 26 hours/day
- **Start offset**: Week 6 (not week 1)
- **Output format**: Excel with Radiology headers

### Harbor GDP (Gross Domestic Product)
- **Weeks**: 36 weeks
- **Daily capacity**: Variable (check input)
- **Output format**: Excel with Harbor headers

### Returns Center
- **Weeks**: weeks 3-45 (not starting at week 1)
- **Daily capacity**: 32 hours/day
- **Start offset**: Week 3
- **Output format**: Excel with Returns Center headers

## Step-Down Policy Implementation

```python
def step_down_simulation(initial_queue: float, demand_weeks, daily_capacity, threshold=4):
    """
    Step-down policy: 6 days → 5 days → 4 days per week.
    Trigger: queue < threshold
    """
    step_days = [6, 5, 4]  # days per week at each step
    current_step = 0
    queue = initial_queue
    milestones = {}

    for week_num, demand in demand_weeks:
        days_this_week = step_days[current_step]
        production = days_this_week * daily_capacity
        queue = queue + demand - production

        # Check step-down trigger
        if queue < threshold and current_step < len(step_days) - 1:
            current_step += 1

        # Track milestone
        if queue <= 0 and 'cleared' not in milestones:
            milestones['cleared'] = week_num

    return queue, milestones, current_step
```

## B2 Domain Variants

### Harbor DC Scenario
- **Date range**: Jan 22 – May 1, 2018 (100 days)
- **Holidays**: Feb 19 (Presidents Day/Louis Riel Day), Mar 30 (Good Friday)
- **Capacity transition**: Feb 5 (120 → 135)
- **High-capacity shift**: 22 days on/after Feb 1 (up to 170)

**Categories**:
- **Web**: Start immediately (Jan 22), total 5520
- **DB**: Start Mar 1, total 4035
- **Network**: Distributed across all days, minimum ≥ 1200

### Harvest/Ag Recovery Scenario
- **Date range**: Jan 22 – May 1, 2018 (100 days)
- **Holidays**: Feb 19 (Louis Riel Day), Mar 30 (Good Friday)
- **Capacity transition**: Feb 5 (120 → 135)
- **High-capacity shift**: 20-24 days on/after Feb 1 (up to 170)

**Category Mapping** (maps to Harbor DC pattern):
- **Wheat** = Web: Start immediately (Jan 22), total 5520, PO due dates same as Web
- **Canola** = DB: Start Mar 1 (Scenario 1), Feb 20 (Scenario 2), or immediate (Scenario 3), total 4035
- **Flax** = Network: Variable constraints:
  - Scenario 1: Minimum 1200 total, distributed across all working days
  - Scenario 2: Minimum 100 before Feb 1, 0 after (front-loaded cutoff)
  - Scenario 3: Eliminated (0 units), trade-off for high-capacity window

**Scenario Outcomes**:
- Scenario 1 (Current Equipment): Both Wheat and Canola NOT on-time (cumulative open > 0)
- Scenario 2 (Relocated Flax): Wheat on-time, Canola NOT on-time
- Scenario 3 (10hr Shift): Both on-time with 22 shift days at 170 capacity

**Summary Requirements**:
- **Actions**: Bullet list of operational changes
- **Wheat Bin Loads Impact**: Production total vs PO, on-time status
- **Canola Bin Loads Impact**: Production total vs PO, start date impact
- **Flax Processing Impact**: Total units and distribution strategy
- **May PO On-Time**: No / Wheat Yes Canola No / Yes

## Column Mapping Reference

### B1 Weekly Simulation
| Column | Content |
|--------|---------|
| A | Labels (Week, Demand, Production, Queue, etc.) |
| B-N | Weekly data (week 1, week 2, ...) |

### B2 Daily Simulation (Harbor DC & Harvest/Ag)
| Column | Content | Type |
|--------|---------|------|
| B | Date | Formula (B4 literal, B5+ =B(prev)+1) |
| C | Web/Wheat Production | Constant |
| D | Web/Wheat PO Due | Constant |
| E | Web/Wheat Cumulative Open | Formula (=D4-C4, =E(prev)+D(curr)-C(curr)) |
| F | DB/Canola Production | Constant |
| G | DB/Canola PO Due | Constant |
| H | DB/Canola Cumulative Open | Formula |
| I | Network/Flax Production | Constant |
| J | Total Production | Formula (=C+F+I) |

## Output Constraints

### Excel Output Rules
- No extra None rows at end
- Weeks/dates ascending (verify sorting)
- Raw float values (no rounding)
- Domain-specific headers exactly matching expected format

### summary.txt Rules (B1)
- Milestone week when queue cleared
- Domain-specific narrative
- Word/sentence limits (check domain requirements)

### summary.md Rules (B2)
- Sections with **bold** field labels
- Scenario comparison summary
- "On-Time" outcome validation (cumulative open ≤ 0)
- For Harvest: Include 30-day notification mention for shift scenarios