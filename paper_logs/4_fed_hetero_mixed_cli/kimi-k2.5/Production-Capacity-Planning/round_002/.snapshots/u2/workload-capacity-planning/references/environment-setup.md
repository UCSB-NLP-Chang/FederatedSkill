# Environment Setup for Restricted Python (PEP 668)

When pip install fails with "externally-managed-environment" error.

## Quick Setup Pattern

```bash
python3 -m venv venv
source venv/bin/activate
pip install pandas openpyxl
python3 your_script.py
```

**Critical**: Chain activation with execution in the same command to persist state:
```bash
python3 -m venv venv && source venv/bin/activate && pip install pandas openpyxl && python3 your_script.py
```

## Key Points

1. **Never use** `--break-system-packages` flag on system Python
2. Create venv in a writable directory (`/root` or current working dir)
3. Install dependencies after activation, not before
4. Run the script in the same shell session as activation

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No module named pandas" | Reactivate venv: `source venv/bin/activate && python3 ...` |
| Permission errors | Create venv in writable directory |
| venv not persisting | Chain commands with `&&` in single Bash call |

## When to Use

Use this pattern when:
- System Python is managed by OS package manager
- Direct pip install is blocked by PEP 668
- Working in containerized/restricted environments
