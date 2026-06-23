# Event Registration Data Patterns

Patterns for consolidating event registration data from multiple sources (online XLSX, walk-in CSV) with event catalog lookups.

## Column Name Alignment

Walk-in data often uses different column names than online data:

| Walk-in Column | Online Column | Purpose |
|----------------|---------------|---------|
| `walk_in_id` | `REG_ID` | Registration identifier |
| `event_code` | `EVENT_ID` | Event reference key |
| `guest_name` | `ATTENDEE_NAME` | Person name |
| `registration_type` | `REG_TYPE` | VIP/Standard/Student/Speaker |
| `fee_paid` | `AMOUNT_PAID` | Numeric payment amount |

Always normalize before concat/merge:
```python
walkin_df = walkin_df.rename(columns={
    "walk_in_id": "REG_ID",
    "event_code": "EVENT_ID",
    "guest_name": "ATTENDEE_NAME",
    "registration_type": "REG_TYPE",
    "fee_paid": "AMOUNT_PAID"
})
```

## Source Tracking

Add source column before combining:
```python
online_df["SOURCE"] = "Online"
walkin_df["SOURCE"] = "Walk-in"
combined = pd.concat([online_df, walkin_df], ignore_index=True)
```

## Derived Columns for Event Data

### IS_VIP Flag
```python
combined["IS_VIP"] = combined["REG_TYPE"].apply(
    lambda x: "Yes" if x == "VIP" else "No"
)
# Categorical values: 'Yes', 'No' (case-sensitive)
```

### PRICE_TIER from Payment Amount
```python
def get_price_tier(amount):
    if amount == 0:
        return "Free"
    elif amount < 100:
        return "Budget"
    elif amount < 200:
        return "Standard"
    else:
        return "Premium"

combined["PRICE_TIER"] = combined["AMOUNT_PAID"].apply(get_price_tier)
# Categorical values: 'Free', 'Budget', 'Standard', 'Premium'
```

## Event Catalog Join

Join on `EVENT_ID` (normalized as string):
```python
# Event catalog from PDF extraction
event_df = extract_from_pdf("event_catalog.pdf")  # Use scripts/extract_pdf_tables.py

# Normalize keys
combined["EVENT_ID"] = combined["EVENT_ID"].astype(str).str.strip()
event_df["EVENT_ID"] = event_df["EVENT_ID"].astype(str).str.strip()

# Join
merged = combined.merge(
    event_df,
    on="EVENT_ID",
    how="inner"  # Drops registrations for non-existent events
)
```

## Common Pivot Configurations

### Revenue by Track
```python
pd.pivot_table(
    merged,
    index="TRACK",
    values="AMOUNT_PAID",
    aggfunc="sum"
).reset_index()
# Sheet name: "Revenue by Track"
```

### Attendance by Venue
```python
merged.groupby("VENUE").size().reset_index(name="Registration Count")
# Sheet name: "Attendance by Venue"
```

### Track-RegType Matrix
```python
pd.pivot_table(
    merged,
    index="TRACK",
    columns="REG_TYPE",
    values="AMOUNT_PAID",
    aggfunc="sum",
    fill_value=0
).reset_index()
# Sheet name: "Track RegType Matrix"
```

### Events by Track (Count)
```python
merged.groupby("TRACK").size().reset_index(name="Registration Count")
# Sheet name: "Events by Track"
```

## Verification Points

1. Row count after merge should be <= sum of input rows (inner join drops invalid events)
2. Check for nulls in joined columns (TRACK, VENUE) indicating missed lookups
3. Verify categorical columns use exact expected values: 'Yes'/'No', 'Free'/'Budget'/'Standard'/'Premium'
4. Confirm all five expected sheets exist with exact names