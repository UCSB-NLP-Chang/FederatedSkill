# Domain Terminology Mappings

When tasks require domain-specific terminology instead of standard `removed_ids`/`changed_records`, map as follows:

## Standard → Domain Examples

| Standard Key | Domain Context | Mapped Key |
|-------------|----------------|------------|
| `removed_ids` | Retail categories | `dropped_categories` |
| `removed_ids` | Departments | `closed_departments` |
| `removed_ids` | Assets | `retired_assets` |
| `removed_ids` | Schools/Universities | `retired_schools` |
| `removed_ids` | Servers/Hardware | `decommissioned_servers` |
| `removed_ids` | Medications | `deleted_medications` |
| `removed_ids` | Shipping containers | `missing_containers` |
| `changed_records` | Retail categories | `adjusted_categories` |
| `changed_records` | Departments | `updated_departments` |
| `changed_records` | Assets | `modified_assets` |
| `changed_records` | Schools/Universities | `revised_schools` |
| `changed_records` | Servers/Hardware | `updated_servers` |
| `changed_records` | Medications | `modified_medications` |
| `changed_records` | Shipping containers | `changed_containers` |
| `added_ids` | Retail categories | `new_categories` |
| `added_ids` | Departments | `opened_departments` |
| `added_ids` | Schools/Universities | `new_schools` |
| `added_ids` | Servers/Hardware | `provisioned_servers` |
| `added_ids` | Medications | `added_medications` |
| `added_ids` | Shipping containers | `added_containers` |

## Determining Correct Keys

**Decision rule**: Scan the task description for clues:
- Look for verbs: "decommissioned", "retired", "dropped", "removed", "deleted", "discontinued", "missing"
- Look for nouns: "servers", "assets", "categories", "departments", "medications", "drugs", "containers"
- If the task says "list decommissioned servers", use `"decommissioned_servers"` as the key
- If the task says "generate diff report" without specifics, use standard keys

## Implementation

**Option 1**: Use `compute_diff.py` with custom keys:
```bash
python scripts/compute_diff.py old.json new.json \
  --removed-key dropped_categories \
  --changed-key adjusted_categories \
  --omit-empty
```

**Option 2**: Post-process standard output:
```python
result = json.loads(output)
mapped = {
    "dropped_categories": result.get("removed_ids", []),
    "adjusted_categories": result.get("changed_records", [])
}
```

**Option 3**: Write inline comparison (see SKILL.md workflow) for complex extractions.

## Critical Constraint

Maintain value types when remapping keys:
- Keep integers as integers (not strings)
- Keep floats as floats (unless `.0`, then convert to int)
- Sort arrays by ID for deterministic output