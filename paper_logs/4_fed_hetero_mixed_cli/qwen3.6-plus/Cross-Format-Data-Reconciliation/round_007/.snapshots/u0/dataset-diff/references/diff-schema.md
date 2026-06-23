# Dataset Diff Output Schema

## JSON Structure

```json
{
  "removed_ids": ["string"],
  "added_ids": ["string"],
  "changed_records": [
    {
      "id": "string",
      "field": "string",
      "old_value": "any",
      "new_value": "any"
    }
  ]
}
```

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `removed_ids` | `string[]` | Keys present in old dataset but missing from new dataset |
| `added_ids` | `string[]` | Keys present in new dataset but missing from old dataset |
| `changed_records` | `object[]` | Records with field-level changes |
| `changed_records[].id` | `string` | Key of the changed record |
| `changed_records[].field` | `string` | Name of the changed field |
| `changed_records[].old_value` | `any` | Value in old dataset (null if was null) |
| `changed_records[].new_value` | `any` | Value in new dataset (null if is null) |

## Notes

- Each field change is a separate entry in `changed_records`
- A single record may appear multiple times if multiple fields changed
- Numeric values preserve their type (int vs float)
- Null values are represented as JSON `null`
- String values are compared case-sensitively