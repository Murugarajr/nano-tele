# Tool Usage Notes

Tool signatures are provided automatically via function calling.
This file documents non-obvious constraints and usage patterns.

## exec — Safety Limits

- Commands have a configurable timeout (default 60s)
- Dangerous commands are blocked (rm -rf, format, dd, shutdown, etc.)
- Output is truncated at 10,000 characters
- `restrictToWorkspace` config can limit file access to the workspace

## perfume_tool.py — Fragrance Workflows

Use the local deterministic helper for fragrance workflows:

```bash
./tools/perfume_tool.py route --text "/today"
./tools/perfume_tool.py route --text "/history"
./tools/perfume_tool.py route --text "Show my collection"
./tools/perfume_tool.py recommend --occasion today --city "Sheffield"
./tools/perfume_tool.py stats
./tools/perfume_tool.py feedback "Sauvage" liked --notes "lasted well"
./tools/perfume_tool.py travel "Dubai"
./tools/perfume_tool.py travel --clear
./tools/perfume_tool.py collection list
```

The tool is workspace-local, uses Open-Meteo JSON weather data, and writes recommendation history and feedback into `workspace/memory/`.

## glob — File Discovery

- Use `glob` to find files by pattern before falling back to shell commands
- Simple patterns like `*.py` match recursively by filename
- Use `entry_type="dirs"` when you need matching directories instead of files
- Use `head_limit` and `offset` to page through large result sets
- Prefer this over `exec` when you only need file paths

## grep — Content Search

- Use `grep` to search file contents inside the workspace
- Default behavior returns only matching file paths (`output_mode="files_with_matches"`)
- Supports optional `glob` filtering plus `context_before` / `context_after`
- Supports `type="py"`, `type="ts"`, `type="md"` and similar shorthand filters
- Use `fixed_strings=true` for literal keywords containing regex characters
- Use `output_mode="files_with_matches"` to get only matching file paths
- Use `output_mode="count"` to size a search before reading full matches
- Use `head_limit` and `offset` to page across results
- Prefer this over `exec` for code and history searches
- Binary or oversized files may be skipped to keep results readable

## cron — Scheduled Reminders

- Please refer to cron skill for usage.
