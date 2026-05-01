# nano-tele

A personal fragrance concierge Telegram bot powered by [nanobot-ai](https://github.com/hkuds/nanobot) and OpenRouter. It recommends perfumes from a curated collection based on live weather data.

## What It Does

- **Weather-aware recommendations** — Fetches live weather for your city and matches it to the best fragrance from a personal collection of 14 perfumes.
- **Telegram-native** — Replies in a concise, emoji-friendly format optimised for mobile chat.
- **Collection-only** — Never suggests perfumes outside the saved collection.
- **Scheduled reminders** — Supports cron-based reminders and heartbeat tasks for recurring checks.

## Architecture

```
User (Telegram)  <--->  nanobot gateway  <--->  Agent (LLM + tools + memory)
                              |
                        + Health check server
```

- **Gateway** — Routes Telegram messages to the agent and back.
- **Agent** — Configured via markdown files in `workspace/` (SOUL, AGENTS, USER, TOOLS, HEARTBEAT).
- **Skills** — Domain knowledge lives in `workspace/skills/perfume-advisor/`.
- **Memory** — Session history and memory are persisted in `workspace/memory/` and `workspace/sessions/`.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | `nanobot-ai` (Python MCP agent framework) |
| LLM | DeepSeek V3 via OpenRouter |
| Channel | Telegram Bot API |
| Weather | wttr.in (no API key required) |
| Search | DuckDuckGo |

## Project Structure

```
.
├── main.py              # Entry point: launches nanobot gateway + health server
├── config.json          # Agent, channel, provider & tool configuration
├── requirements.txt     # Python dependencies
├── cron/                # Scheduled job definitions
├── history/             # CLI history
└── workspace/
    ├── SOUL.md          # Bot identity, personality & core rules
    ├── AGENTS.md        # Instruction workflows (perfume recommendation steps)
    ├── USER.md          # Owner profile & preferences
    ├── TOOLS.md         # Tool usage notes & safety limits
    ├── HEARTBEAT.md     # Recurring periodic tasks
    ├── skills/
    │   └── perfume-advisor/
    │       └── SKILL.md # Fragrance collection & weather pairing rules
    ├── memory/          # Persistent memory storage
    └── sessions/        # Active conversation sessions
```

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
export TELEGRAM_BOT_TOKEN="<your-bot-token>"
export OR_API_KEY="<your-openrouter-api-key>"
export ALLOW_FROM="<your-telegram-user-id>"
export ALLOW_FROM_2="<optional-second-user-id>"
```

### 3. Run the bot

```bash
python main.py
```

The gateway starts on port `18790` (override with `NANOBOT_PORT`). If a platform `PORT` is set, a health-check server also starts on that port.

## How Recommendations Work

1. **Fetch weather** via `wttr.in` for the requested city (default: Sheffield, UK).
2. **Classify** into a weather bucket (Hot & dry, Hot & humid, Mild, Cool & dry, Cold & dry, Cold & rainy/wet).
3. **Infer occasion** (office, daytime, evening) from time and keywords.
4. **Select** the top-ranked perfume from the collection that matches both weather and occasion.
5. **Reply** with two lines: a weather summary and the fragrance pick with a one-line reason.

Example output:

```
🌤️ *Sheffield: 18°C, partly cloudy, 55% humidity*
💨 Wear **Sauvage by Dior** — woody fresh bergamot and pepper, perfect for mild daytime conditions.
```

## Configuration Highlights

| Config | Value |
|--------|-------|
| Model | `deepseek/deepseek-chat` |
| Provider | `openrouter` |
| Max tokens | 4096 |
| Temperature | 0.2 |
| Timezone | Europe/London |
| Dream interval | Every 2 hours (free model batch processing) |
| Tool exec timeout | 60s |
| Web search | DuckDuckGo, max 1 result |

## Customising

- **Change city** — Edit `USER.md` default location.
- **Update collection** — Edit `workspace/skills/perfume-advisor/SKILL.md`.
- **Tweak personality** — Edit `SOUL.md`.
- **Add heartbeat tasks** — Edit `HEARTBEAT.md`.
- **Switch model** — Change `model` in `config.json` (any OpenRouter model).

## Deployment Notes

- Nanobot uses a **gateway** process that stays alive and routes Telegram webhooks/polling.
- `restrictToWorkspace: true` in `config.json` keeps file tools scoped to `./workspace/`.
- The built-in health server responds with `ok` on `PORT` for platform health checks (e.g. Railway, Render).

## Resources

- [Nanobot GitHub](https://github.com/hkuds/nanobot)
- [OpenRouter](https://openrouter.ai)
- [Telegram Bot API](https://core.telegram.org/bots)
