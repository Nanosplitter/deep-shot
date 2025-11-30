# Retry Prompt

The code you generated failed with this error:

```
{{error}}
```

## Common Fixes

- **Column not found**: Check the Column Reference section - use only columns that exist
- **Pandas syntax**: Use Polars methods (e.g., `group_by` not `groupby`, `sort` with `descending=True` not `reverse=True`)
- **DataFrame returned**: Convert to Python types with `.to_dicts()`, `.item()`, or aggregation
- **Missing seasons**: Always pass `seasons=[2025]` or appropriate year(s)
- **Wrong player name format**: PBP uses abbreviated names like "J.Goff", not "Jared Goff"

Fix the code and call the tool again.
