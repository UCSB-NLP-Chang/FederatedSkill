---
name: tool-name-hygiene
description: Prevent and detect whitespace-prefixed tool names that cause silent failures. Use when calling tools programmatically, generating tool calls from templates, or debugging 'No such tool available' errors that mention tools with leading spaces.
---

# Tool Name Hygiene

## Core Rule

Tool names must never have leading or trailing whitespace. `' Write'` fails; `'Write'` succeeds.

## Failure Signatures

```
Error: No such tool available:  Write      # space before W
Error: No such tool available:  Bash       # space before B
Error: No such tool available:  Read       # space before R
```

## Pre-Call Checklist

Before executing any tool call:
1. Check tool name for leading/trailing spaces
2. Verify against known valid names: Write, Read, Bash, Glob, Edit, Grep
3. Never interpolate tool names from user input without `.strip()`

## Detection

If `No such tool available` error appears:
1. Immediately inspect the reported tool name for whitespace
2. Check string literals in the failing call
3. Look for copy-paste issues that introduced extra spaces

## Anti-Patterns

- Do NOT assume tool names are validated by the environment
- Do NOT use f-strings for tool names without `.strip()`
- Do NOT ignore errors mentioning tools with wrong spacing
