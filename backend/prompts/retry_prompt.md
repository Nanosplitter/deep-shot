# Retry Prompt

The code you generated failed with this error:

```
{{error}}
```

## ⚠️ If the error mentions "no attribute 'groupby'" or similar:

Remember: **nflreadpy uses POLARS, not pandas!**

| ❌ WRONG (pandas)     | ✅ CORRECT (Polars) |
| --------------------- | ------------------- |
| `df.groupby(...)`     | `df.group_by(...)`  |
| `df.sort_values(...)` | `df.sort(...)`      |
| `ascending=False`     | `descending=True`   |

## Common Fixes

- **Column not found**: Check the Column Reference section - use only columns that exist
- **DataFrame returned**: Convert to Python types with `.to_dicts()`, `.item()`, or aggregation
- **Missing seasons**: Always pass `seasons=[2025]` or appropriate year(s)
- **Wrong player name format**: PBP uses abbreviated names like "J.Goff", not "Jared Goff"

Fix the code and call the tool again.
