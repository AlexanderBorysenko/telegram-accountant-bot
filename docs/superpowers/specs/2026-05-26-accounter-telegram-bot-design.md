# Accounter Telegram Bot — Design Spec

## Overview

A Docker-based Python Telegram bot that acts as an AI-powered financial transaction assistant. Users send natural language prompts via `/accounter <prompt>` (Ukrainian or English), and a Claude agent interprets the intent, executes the appropriate transaction operations against MongoDB, and responds in the user's language.

## Architecture

Single async Python process (monolith) running the Telegram bot (long-polling) and Claude agent logic. MongoDB as the data store. Two containers via Docker Compose.

```
┌─────────────────────────────────┐
│  Python Process (asyncio)       │
│  ├── Telegram Bot (polling)     │
│  ├── Claude Agent (tool_use)    │
│  └── MongoDB Client (motor)    │
└──────────────┬──────────────────┘
               │
         ┌─────┴─────┐
         │  MongoDB 7 │
         └────────────┘
```

No HTTP server, no public ports. Bot polls Telegram directly.

## Project Structure

```
buhalter/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .env                    # gitignored
├── requirements.txt
├── scripts/
│   ├── start.sh            # docker compose up -d --build
│   ├── stop.sh             # docker compose down
│   ├── restart.sh          # stop + start
│   └── update.sh           # git pull + rebuild + restart
├── src/
│   ├── __init__.py
│   ├── main.py             # Entry point: starts bot polling
│   ├── config.py           # Env var loading via Pydantic Settings
│   ├── db.py               # Motor client, connection management
│   ├── models.py           # Transaction Pydantic models
│   ├── services.py         # CRUD operations (5 functions)
│   ├── agent.py            # Claude agent: tools, system prompt, execution loop
│   └── bot.py              # Telegram /accounter command handler
└── DEPLOYMENT.md           # Ubuntu + CloudPanel reverse proxy setup
```

## Data Model

### Transaction (MongoDB document)

```json
{
    "_id": "ObjectId",
    "chat_id": 123456789,
    "title": "Оновлення блоків на Дново",
    "description": "Optional description",
    "money_amount": 100.0,
    "payment_status": "pending",
    "job_status": "pending",
    "created_at": "2026-05-26T12:00:00Z"
}
```

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `_id` | ObjectId | auto | auto | MongoDB default |
| `chat_id` | int | yes | — | Telegram chat ID, scoping key |
| `title` | string | yes | — | Transaction title |
| `description` | string | no | null | Optional details |
| `money_amount` | float | yes | — | Amount in USD |
| `payment_status` | "pending" \| "done" | no | "pending" | Payment state |
| `job_status` | "pending" \| "done" | no | "pending" | Job/work state |
| `created_at` | datetime | auto | UTC now | Set on creation |

**Collection:** `transactions`
**Index:** compound on `(chat_id, payment_status, job_status)` for efficient unfulfilled queries.

### Derived State

A transaction is "fulfilled" when `payment_status == "done"` AND `job_status == "done"`. No stored `fulfilled` field — it's always computed from the two statuses.

## Claude Agent

### Model

`claude-sonnet-4-6` — fast, cost-effective, fully capable for tool routing.

### Tools (5)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `create_transaction` | `title` (req), `description`, `money_amount` (req), `payment_status`, `job_status` | Creates a new transaction |
| `update_transaction` | `transaction_id` (req), `title`, `description`, `money_amount`, `payment_status`, `job_status` | Updates fields on an existing transaction |
| `delete_transaction` | `transaction_id` (req) | Deletes a transaction |
| `get_unfulfilled_transactions` | — | Returns all transactions where NOT both statuses are "done" |
| `get_historical_transactions` | — | Returns last 10 transactions by created_at desc |

All tools are automatically scoped to the current `chat_id` (injected by the agent, not passed by Claude).

### Agent Loop

1. User sends `/accounter <prompt>`
2. Bot extracts prompt, passes to agent with `chat_id`
3. Agent sends to Claude API: system prompt + user prompt + tool definitions
4. Claude responds with tool calls or text
5. Agent executes tool calls against `services.py`, returns results to Claude
6. Loop continues until Claude responds with final text (no more tool calls)
7. Bot sends Claude's text response to Telegram

### System Prompt Behavior

- Act as a financial transaction assistant
- Respond in the same language as the user's input
- Use tools to perform operations — never guess or fabricate data
- When the user wants to "fulfill" a task, update both statuses to "done"
- When searching by title/description, use fuzzy matching (Claude's judgment from the list)
- Always confirm what was done after executing actions
- For listing operations, format results clearly with titles, amounts, and statuses

### Multi-Step Example

User: "Заверши всі таски по дново"
1. Claude calls `get_unfulfilled_transactions()`
2. Reviews results, identifies transactions with "дново" in title
3. Calls `update_transaction(id, payment_status="done", job_status="done")` for each match
4. Responds with summary: "Завершено 2 транзакції по Дново: ..."

## Telegram Bot

- **Command:** `/accounter <prompt>`
- **No prompt:** responds with a usage hint
- **Processing:** sends typing indicator while Claude works
- **Response:** Claude's final text message
- **Scope:** ignores all messages except the `/accounter` command
- **Stateless:** each command is independent, no conversation history
- **Chat-scoped:** transactions belong to the chat where the command is sent

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token from @BotFather |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `MONGODB_URI` | MongoDB connection string (default: `mongodb://mongo:27017`) |
| `MONGODB_DB_NAME` | Database name (default: `buhalter`) |

## Docker Setup

### docker-compose.yml

Two services:
- `bot`: Python app, built from Dockerfile, env from `.env`, depends on `mongo`, restart unless-stopped
- `mongo`: `mongo:7` image, persistent volume `mongo_data`, restart unless-stopped

No ports exposed externally — bot polls Telegram, MongoDB is internal only.

### Dockerfile

Python 3.12 slim base, copy requirements, install, copy src, run `python -m src.main`.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/start.sh` | `docker compose up -d --build` |
| `scripts/stop.sh` | `docker compose down` (preserves volumes) |
| `scripts/restart.sh` | Runs stop then start |
| `scripts/update.sh` | `git pull && docker compose up -d --build` (pull + rebuild + restart) |

All scripts run from the project root directory.

## DEPLOYMENT.md

Covers:
1. Prerequisites (Docker, Docker Compose, git)
2. Clone repo, configure `.env`
3. First start via `scripts/start.sh`
4. Verify bot is running (send `/accounter test` in Telegram)
5. CloudPanel reverse proxy setup (note: bot doesn't need a public port since it uses long-polling, but guide covers the case where you want to add a health-check endpoint or future webhook support)
6. Domain + SSL configuration in CloudPanel

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Telegram | python-telegram-bot v20+ (async) |
| AI | Anthropic SDK (claude-sonnet-4-6, tool_use) |
| Database | MongoDB 7 via motor (async) |
| Validation | Pydantic v2 |
| Config | Pydantic Settings |
| Container | Docker + Docker Compose |
