# AGENTS.md

Project-specific instructions for coding agents working on `nano-tele`.

## Project Overview

`nano-tele` is a Python Telegram fragrance concierge powered by `nanobot-ai` and OpenRouter. It recommends perfumes from a local collection using deterministic tool logic plus live weather data.

Core files:

- `main.py` — process entry point; starts the Nanobot gateway and optional platform health server.
- `config.json` — Nanobot agent/channel/provider/tool configuration.
- `workspace/AGENTS.md`, `workspace/SOUL.md`, `workspace/USER.md`, `workspace/TOOLS.md`, `workspace/HEARTBEAT.md` — runtime prompt/instruction files consumed by Nanobot. Do not confuse these with this coding-agent file.
- `workspace/tools/perfume_tool.py` — canonical Python implementation for recommendation, weather lookup, routing, feedback, stats, travel mode, and collection management.
- `workspace/tools/perfume` — shell wrapper used from inside the Nanobot workspace; it includes deployment/runtime fallbacks and delegates to `perfume_tool.py` when possible.
- `workspace/data/fragrances.json` — fragrance collection source of truth.
- `workspace/data/ranking.json` — weather/occasion ranking source of truth.
- `workspace/data/preferences.json` — mutable user preference/travel/feedback data.
- `workspace/memory/RECENT_PICKS.md` and `workspace/memory/FEEDBACK.md` — mutable runtime logs.
- `tests/test_perfume_tool.py` — unit tests for deterministic selection/routing/persistence behavior.

## Environment

- Language: Python 3.10+.
- Dependencies: `nanobot-ai`, `requests` from `requirements.txt`.
- Runtime environment variables:
  - `TELEGRAM_BOT_TOKEN`
  - `OR_API_KEY`
  - `ALLOW_FROM`
  - `ALLOW_FROM_2` optional
  - `NANOBOT_PORT` optional, defaults to `18790`
  - `PORT` optional platform health-check port

Never add secrets to source files. Keep tokens and API keys in the environment only.

## Development Commands

Install only when explicitly requested:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python main.py
```

Run tests:

```bash
python -m unittest discover -s tests
```

Exercise the local helper:

```bash
sh workspace/tools/perfume route --text "/today"
sh workspace/tools/perfume route --text "/history"
sh workspace/tools/perfume route --text "show my collection"
sh workspace/tools/perfume stats
sh workspace/tools/perfume __diag
```

## Coding Guidelines

- Prefer targeted, minimal changes. Do not refactor unrelated prompt files, wrapper shell logic, or data files.
- Use `pathlib.Path` for filesystem access in Python.
- Keep Python type annotations on new functions and avoid unnecessary `Any`.
- Preserve existing `unittest` style unless the project explicitly moves to another test framework.
- Keep user-facing Telegram output concise and Markdown-safe.
- For weather-based recommendations, do not invent weather data. If live weather is unavailable, preserve the existing explicit unavailable response.
- Recommendation behavior must remain collection-only: never suggest perfumes not present in `workspace/data/fragrances.json`.

## Perfume Tool Rules

`workspace/tools/perfume_tool.py` is the canonical deterministic tool. It handles:

- Open-Meteo geocoding and weather lookup.
- Weather bucket classification.
- Occasion inference.
- Same-day/history rotation.
- Feedback-weighted ranking.
- Travel mode.
- Collection list/add/remove.
- Markdown history and feedback logs.

When changing recommendation logic:

1. Update `workspace/tools/perfume_tool.py` first.
2. Keep `workspace/tools/perfume` compatible with Nanobot/Railway execution if wrapper behavior is affected.
3. Keep `workspace/data/ranking.json` and `workspace/data/fragrances.json` consistent if fragrance names, weather buckets, or occasions change.
4. Add or update tests in `tests/test_perfume_tool.py` for routing, selection, rotation, persistence, or data changes.

Known weather buckets:

- `Hot & dry`
- `Hot & humid`
- `Mild`
- `Cool & dry`
- `Cold & dry`
- `Cold & rainy`

Known primary occasions:

- `Daytime`
- `Office`
- `Evening`
- `Date`

## Runtime Prompt Files

The files in `workspace/` are bot runtime instructions and user profile data. Edit them carefully:

- `workspace/AGENTS.md` controls how the Nanobot agent routes fragrance requests. Preserve the tool-first rule for perfume requests.
- `workspace/SOUL.md` controls persona and output style.
- `workspace/TOOLS.md` documents Nanobot tool usage.
- `workspace/HEARTBEAT.md` controls periodic tasks. Do not add proactive messages unless explicitly requested.
- `workspace/USER.md` may contain personal preference/profile information; avoid unnecessary edits.

## Mutable Data And Logs

Treat these as runtime state, not code:

- `workspace/data/preferences.json`
- `workspace/memory/RECENT_PICKS.md`
- `workspace/memory/FEEDBACK.md`
- `workspace/memory/history.jsonl`
- `workspace/sessions/*.jsonl`
- `history/cli_history`

Do not clear or rewrite runtime history/session files unless explicitly asked. If tests need state, use temporary directories as existing tests do.

## Validation Requirements

After any code or data-schema change, run:

```bash
python -m unittest discover -s tests
```

If changing app startup or config, also sanity-check:

```bash
python -m py_compile main.py workspace/tools/perfume_tool.py
sh workspace/tools/perfume __diag
```

If changing shell wrapper behavior, run at least one wrapper route command that does not require private secrets, for example:

```bash
sh workspace/tools/perfume route --text "show my collection"
```

Report exact failures rather than hiding them.

## Deployment Notes

- `config.json` has `tools.restrictToWorkspace: true`; Nanobot tool calls operate from `./workspace`.
- The Telegram channel is configured in `config.json` and requires environment-provided credentials.
- `main.py` runs the Nanobot gateway on `NANOBOT_PORT` and starts a simple `ok` health server only when platform `PORT` is set.
- Do not install or update dependencies, alter lock files, or change deployment ports unless requested.
