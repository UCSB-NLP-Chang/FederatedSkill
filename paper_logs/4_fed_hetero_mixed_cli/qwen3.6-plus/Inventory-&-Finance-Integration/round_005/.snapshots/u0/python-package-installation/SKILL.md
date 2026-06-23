---
name: python-package-installation
description: Install Python packages in externally-managed environments. Use when pip install fails with 'externally-managed-environment' error or PEP 668 message on Debian/Ubuntu systems.
---

# Python Package Installation in Externally-Managed Environments

## When to Use
Use this skill when `pip install <package>` fails with an error mentioning:
- "externally-managed-environment"
- "PEP 668"
- "This environment is externally managed"

This is common on Debian 12+, Ubuntu 23.04+, and other systems following PEP 668.

## Quick Fix
For quick one-off installs where system stability is not critical:

```bash
pip install <package> --break-system-packages
```

This bypasses the externally-managed check. Expect a warning about running as root.

## Recommended Alternatives

### Option 1: Virtual Environment (Preferred)
```bash
python3 -m venv /path/to/venv
/path/to/venv/bin/pip install <package>
# Then use: /path/to/venv/bin/python script.py
```

### Option 2: pipx for CLI Tools
```bash
pipx install <package>
```

### Option 3: System Packages
```bash
apt install python3-<package>
```

## Decision Guide
- **One-off script or quick task**: Use `--break-system-packages`
- **Project requiring isolation**: Use virtual environment
- **Installing a CLI tool**: Use pipx
- **Common library (numpy, requests, etc.)**: Check apt first

## Anti-Patterns
- Do not retry the same `pip install` command without modification
- Do not assume the package is unavailable; it's an environment policy issue
- Do not ignore the warning about root user permissions in production contexts
