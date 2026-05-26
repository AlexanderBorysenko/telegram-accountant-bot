# Accounter Telegram Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that accepts natural language prompts and uses Claude's tool_use API to manage financial transactions in MongoDB.

**Architecture:** Single async Python process running Telegram long-polling and Claude agent. MongoDB stores transactions scoped by Telegram chat ID. Claude (sonnet-4-6) receives user prompts with 5 tool definitions, decides which operations to perform, and returns human-readable responses.

**Tech Stack:** Python 3.12, python-telegram-bot 20+, anthropic SDK, motor (async MongoDB), pydantic v2, pydantic-settings, Docker Compose, MongoDB 7.

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | Python dependencies |
| `src/__init__.py` | Package marker |
| `src/config.py` | Load and validate env vars via Pydantic Settings |
| `src/db.py` | Motor client singleton, get_collection helper, index creation |
| `src/models.py` | Pydantic models for Transaction (create input, update input, DB document) |
| `src/services.py` | 5 async CRUD functions operating on MongoDB |
| `src/agent.py` | Claude tool definitions, system prompt, agent execution loop |
| `src/bot.py` | Telegram bot setup, /accounter command handler |
| `src/main.py` | Entry point: init DB, start bot polling |
| `tests/conftest.py` | Pytest fixtures: mock DB, mock Claude client |
| `tests/test_models.py` | Model validation tests |
| `tests/test_services.py` | Service function tests (mocked MongoDB) |
| `tests/test_agent.py` | Agent loop tests (mocked Claude API) |
| `Dockerfile` | Python 3.12 slim container |
| `docker-compose.yml` | bot + mongo services |
| `.env.example` | Template for required env vars |
| `.gitignore` | Python + Docker + .env ignores |
| `scripts/start.sh` | Start infrastructure |
| `scripts/stop.sh` | Stop infrastructure |
| `scripts/restart.sh` | Restart infrastructure |
| `scripts/update.sh` | Pull + rebuild + restart |
| `DEPLOYMENT.md` | Ubuntu + CloudPanel deployment guide |

---

### Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
python-telegram-bot==21.12
anthropic==0.52.0
motor==3.7.0
pydantic==2.11.4
pydantic-settings==2.9.1
pymongo==4.13.0
pytest==8.4.1
pytest-asyncio==1.0.0
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.env
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
```

- [ ] **Step 3: Create .env.example**

```
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
ANTHROPIC_API_KEY=your-anthropic-api-key
MONGODB_URI=mongodb://mongo:27017
MONGODB_DB_NAME=buhalter
```

- [ ] **Step 4: Create src/__init__.py**

Empty file.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore .env.example src/__init__.py
git commit -m "chore: project scaffold with dependencies and config template"
```

---

### Task 2: Config Module

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import os
import pytest
from unittest.mock import patch


def test_config_loads_from_env():
    env = {
        "TELEGRAM_BOT_TOKEN": "test-token",
        "ANTHROPIC_API_KEY": "test-key",
        "MONGODB_URI": "mongodb://localhost:27017",
        "MONGODB_DB_NAME": "testdb",
    }
    with patch.dict(os.environ, env, clear=False):
        from importlib import reload
        import src.config as config_module
        reload(config_module)
        config = config_module.Settings()
        assert config.telegram_bot_token == "test-token"
        assert config.anthropic_api_key == "test-key"
        assert config.mongodb_uri == "mongodb://localhost:27017"
        assert config.mongodb_db_name == "testdb"


def test_config_defaults():
    env = {
        "TELEGRAM_BOT_TOKEN": "test-token",
        "ANTHROPIC_API_KEY": "test-key",
    }
    with patch.dict(os.environ, env, clear=False):
        from importlib import reload
        import src.config as config_module
        reload(config_module)
        config = config_module.Settings()
        assert config.mongodb_uri == "mongodb://mongo:27017"
        assert config.mongodb_db_name == "buhalter"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write implementation**

```python
# src/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    anthropic_api_key: str
    mongodb_uri: str = "mongodb://mongo:27017"
    mongodb_db_name: str = "buhalter"


settings = Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: config module with env var loading"
```

---

### Task 3: Pydantic Models

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py
import pytest
from datetime import datetime, timezone


def test_create_transaction_required_fields():
    from src.models import TransactionCreate
    tx = TransactionCreate(title="Test task", money_amount=100.0)
    assert tx.title == "Test task"
    assert tx.money_amount == 100.0
    assert tx.description is None
    assert tx.payment_status == "pending"
    assert tx.job_status == "pending"


def test_create_transaction_all_fields():
    from src.models import TransactionCreate
    tx = TransactionCreate(
        title="Full task",
        description="With description",
        money_amount=250.0,
        payment_status="done",
        job_status="pending",
    )
    assert tx.description == "With description"
    assert tx.payment_status == "done"


def test_create_transaction_invalid_status():
    from src.models import TransactionCreate
    with pytest.raises(ValueError):
        TransactionCreate(title="Bad", money_amount=100.0, payment_status="invalid")


def test_update_transaction_partial():
    from src.models import TransactionUpdate
    update = TransactionUpdate(title="New title")
    assert update.title == "New title"
    assert update.money_amount is None
    assert update.payment_status is None


def test_update_transaction_to_dict_excludes_none():
    from src.models import TransactionUpdate
    update = TransactionUpdate(payment_status="done")
    d = update.to_update_dict()
    assert d == {"payment_status": "done"}
    assert "title" not in d


def test_transaction_doc_is_fulfilled():
    from src.models import TransactionDoc
    doc = TransactionDoc(
        id="abc123",
        chat_id=1,
        title="Test",
        money_amount=100.0,
        payment_status="done",
        job_status="done",
        created_at=datetime.now(timezone.utc),
    )
    assert doc.is_fulfilled is True


def test_transaction_doc_not_fulfilled():
    from src.models import TransactionDoc
    doc = TransactionDoc(
        id="abc123",
        chat_id=1,
        title="Test",
        money_amount=100.0,
        payment_status="done",
        job_status="pending",
        created_at=datetime.now(timezone.utc),
    )
    assert doc.is_fulfilled is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write implementation**

```python
# src/models.py
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


Status = Literal["pending", "done"]


class TransactionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    money_amount: float
    payment_status: Status = "pending"
    job_status: Status = "pending"


class TransactionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    money_amount: Optional[float] = None
    payment_status: Optional[Status] = None
    job_status: Optional[Status] = None

    def to_update_dict(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class TransactionDoc(BaseModel):
    id: str
    chat_id: int
    title: str
    description: Optional[str] = None
    money_amount: float
    payment_status: Status = "pending"
    job_status: Status = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_fulfilled(self) -> bool:
        return self.payment_status == "done" and self.job_status == "done"

    def to_display_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "money_amount": self.money_amount,
            "payment_status": self.payment_status,
            "job_status": self.job_status,
            "is_fulfilled": self.is_fulfilled,
            "created_at": self.created_at.isoformat(),
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: pydantic models for transaction create, update, and document"
```

---

### Task 4: Database Module

**Files:**
- Create: `src/db.py`

- [ ] **Step 1: Write implementation**

```python
# src/db.py
from motor.motor_asyncio import AsyncIOMotorClient

_client: AsyncIOMotorClient | None = None


def get_client(uri: str) -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(uri)
    return _client


async def init_db(uri: str, db_name: str):
    client = get_client(uri)
    db = client[db_name]
    collection = db["transactions"]
    await collection.create_index([("chat_id", 1), ("payment_status", 1), ("job_status", 1)])
    return collection


def get_collection(uri: str, db_name: str):
    client = get_client(uri)
    return client[db_name]["transactions"]
```

- [ ] **Step 2: Commit**

```bash
git add src/db.py
git commit -m "feat: motor database client with index initialization"
```

---

### Task 5: Transaction Services

**Files:**
- Create: `src/services.py`
- Create: `tests/conftest.py`
- Create: `tests/test_services.py`

- [ ] **Step 1: Create test fixtures**

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_collection():
    collection = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.update_one = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.find = MagicMock()
    return collection
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_services.py
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId


@pytest.fixture
def mock_collection():
    collection = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.update_one = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.find = MagicMock()
    return collection


@pytest.mark.asyncio
async def test_create_transaction(mock_collection):
    from src.services import create_transaction
    from src.models import TransactionCreate

    fake_id = ObjectId()
    mock_collection.insert_one.return_value = MagicMock(inserted_id=fake_id)
    mock_collection.find_one.return_value = {
        "_id": fake_id,
        "chat_id": 123,
        "title": "Test task",
        "description": None,
        "money_amount": 100.0,
        "payment_status": "pending",
        "job_status": "pending",
        "created_at": datetime.now(timezone.utc),
    }

    data = TransactionCreate(title="Test task", money_amount=100.0)
    result = await create_transaction(mock_collection, chat_id=123, data=data)

    mock_collection.insert_one.assert_called_once()
    assert result["title"] == "Test task"
    assert result["money_amount"] == 100.0


@pytest.mark.asyncio
async def test_update_transaction(mock_collection):
    from src.services import update_transaction
    from src.models import TransactionUpdate

    fake_id = ObjectId()
    mock_collection.update_one.return_value = MagicMock(modified_count=1)
    mock_collection.find_one.return_value = {
        "_id": fake_id,
        "chat_id": 123,
        "title": "Updated",
        "description": None,
        "money_amount": 100.0,
        "payment_status": "done",
        "job_status": "pending",
        "created_at": datetime.now(timezone.utc),
    }

    data = TransactionUpdate(payment_status="done")
    result = await update_transaction(mock_collection, chat_id=123, transaction_id=str(fake_id), data=data)

    mock_collection.update_one.assert_called_once()
    assert result["payment_status"] == "done"


@pytest.mark.asyncio
async def test_update_transaction_not_found(mock_collection):
    from src.services import update_transaction
    from src.models import TransactionUpdate

    mock_collection.update_one.return_value = MagicMock(modified_count=0)
    mock_collection.find_one.return_value = None

    data = TransactionUpdate(title="New")
    result = await update_transaction(mock_collection, chat_id=123, transaction_id="000000000000000000000000", data=data)

    assert result is None


@pytest.mark.asyncio
async def test_delete_transaction(mock_collection):
    from src.services import delete_transaction

    mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

    result = await delete_transaction(mock_collection, chat_id=123, transaction_id="000000000000000000000000")
    assert result is True


@pytest.mark.asyncio
async def test_delete_transaction_not_found(mock_collection):
    from src.services import delete_transaction

    mock_collection.delete_one.return_value = MagicMock(deleted_count=0)

    result = await delete_transaction(mock_collection, chat_id=123, transaction_id="000000000000000000000000")
    assert result is False


@pytest.mark.asyncio
async def test_get_unfulfilled_transactions(mock_collection):
    from src.services import get_unfulfilled_transactions

    fake_docs = [
        {
            "_id": ObjectId(),
            "chat_id": 123,
            "title": "Task A",
            "description": None,
            "money_amount": 50.0,
            "payment_status": "pending",
            "job_status": "done",
            "created_at": datetime.now(timezone.utc),
        },
        {
            "_id": ObjectId(),
            "chat_id": 123,
            "title": "Task B",
            "description": None,
            "money_amount": 200.0,
            "payment_status": "done",
            "job_status": "pending",
            "created_at": datetime.now(timezone.utc),
        },
    ]

    cursor = AsyncMock()
    cursor.to_list = AsyncMock(return_value=fake_docs)
    mock_collection.find.return_value = cursor

    results = await get_unfulfilled_transactions(mock_collection, chat_id=123)
    assert len(results) == 2
    assert results[0]["title"] == "Task A"


@pytest.mark.asyncio
async def test_get_historical_transactions(mock_collection):
    from src.services import get_historical_transactions

    fake_docs = [
        {
            "_id": ObjectId(),
            "chat_id": 123,
            "title": f"Task {i}",
            "description": None,
            "money_amount": 10.0 * i,
            "payment_status": "done",
            "job_status": "done",
            "created_at": datetime.now(timezone.utc),
        }
        for i in range(10)
    ]

    cursor = AsyncMock()
    cursor.to_list = AsyncMock(return_value=fake_docs)
    sort_mock = MagicMock(return_value=cursor)
    limit_mock = MagicMock()
    limit_mock.sort = sort_mock
    find_mock = MagicMock(return_value=limit_mock)
    mock_collection.find = find_mock

    results = await get_historical_transactions(mock_collection, chat_id=123)
    assert len(results) == 10
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_services.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 4: Write implementation**

```python
# src/services.py
from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from src.models import TransactionCreate, TransactionUpdate, TransactionDoc


def _doc_to_dict(doc: dict) -> dict:
    tx = TransactionDoc(
        id=str(doc["_id"]),
        chat_id=doc["chat_id"],
        title=doc["title"],
        description=doc.get("description"),
        money_amount=doc["money_amount"],
        payment_status=doc.get("payment_status", "pending"),
        job_status=doc.get("job_status", "pending"),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
    )
    return tx.to_display_dict()


async def create_transaction(
    collection: AsyncIOMotorCollection, chat_id: int, data: TransactionCreate
) -> dict:
    doc = {
        "chat_id": chat_id,
        "title": data.title,
        "description": data.description,
        "money_amount": data.money_amount,
        "payment_status": data.payment_status,
        "job_status": data.job_status,
        "created_at": datetime.now(timezone.utc),
    }
    result = await collection.insert_one(doc)
    created = await collection.find_one({"_id": result.inserted_id})
    return _doc_to_dict(created)


async def update_transaction(
    collection: AsyncIOMotorCollection,
    chat_id: int,
    transaction_id: str,
    data: TransactionUpdate,
) -> dict | None:
    update_dict = data.to_update_dict()
    if not update_dict:
        return None
    await collection.update_one(
        {"_id": ObjectId(transaction_id), "chat_id": chat_id},
        {"$set": update_dict},
    )
    updated = await collection.find_one({"_id": ObjectId(transaction_id), "chat_id": chat_id})
    if not updated:
        return None
    return _doc_to_dict(updated)


async def delete_transaction(
    collection: AsyncIOMotorCollection, chat_id: int, transaction_id: str
) -> bool:
    result = await collection.delete_one({"_id": ObjectId(transaction_id), "chat_id": chat_id})
    return result.deleted_count > 0


async def get_unfulfilled_transactions(
    collection: AsyncIOMotorCollection, chat_id: int
) -> list[dict]:
    query = {
        "chat_id": chat_id,
        "$or": [
            {"payment_status": {"$ne": "done"}},
            {"job_status": {"$ne": "done"}},
        ],
    }
    cursor = collection.find(query)
    docs = await cursor.to_list(length=100)
    return [_doc_to_dict(d) for d in docs]


async def get_historical_transactions(
    collection: AsyncIOMotorCollection, chat_id: int
) -> list[dict]:
    cursor = collection.find({"chat_id": chat_id}).limit(10).sort("created_at", -1)
    docs = await cursor.to_list(length=10)
    return [_doc_to_dict(d) for d in docs]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_services.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 6: Commit**

```bash
git add src/services.py tests/conftest.py tests/test_services.py
git commit -m "feat: transaction CRUD services with tests"
```

---

### Task 6: Claude Agent

**Files:**
- Create: `src/agent.py`
- Create: `tests/test_agent.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_agent.py
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_text_response(text):
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    response.stop_reason = "end_turn"
    return response


def _make_tool_use_response(tool_name, tool_input, tool_use_id="call_1"):
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input
    tool_block.id = tool_use_id
    response = MagicMock()
    response.content = [tool_block]
    response.stop_reason = "tool_use"
    return response


@pytest.mark.asyncio
async def test_agent_simple_create():
    from src.agent import run_agent

    mock_collection = AsyncMock()

    create_response = _make_tool_use_response(
        "create_transaction",
        {"title": "Test task", "money_amount": 100.0},
    )
    final_response = _make_text_response("Created transaction: Test task for $100")

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[create_response, final_response])

    with patch("src.agent.services") as mock_services:
        mock_services.create_transaction = AsyncMock(return_value={
            "id": "abc123",
            "title": "Test task",
            "money_amount": 100.0,
            "payment_status": "pending",
            "job_status": "pending",
            "is_fulfilled": False,
            "created_at": "2026-05-26T12:00:00",
        })

        result = await run_agent(
            client=mock_client,
            collection=mock_collection,
            chat_id=123,
            user_prompt="Create test task for $100",
        )

    assert "Test task" in result
    assert "$100" in result


@pytest.mark.asyncio
async def test_agent_list_unfulfilled():
    from src.agent import run_agent

    mock_collection = AsyncMock()

    list_response = _make_tool_use_response("get_unfulfilled_transactions", {})
    final_response = _make_text_response("You have 2 unfulfilled transactions.")

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[list_response, final_response])

    with patch("src.agent.services") as mock_services:
        mock_services.get_unfulfilled_transactions = AsyncMock(return_value=[
            {"id": "1", "title": "Task A", "money_amount": 50.0, "payment_status": "pending", "job_status": "done", "is_fulfilled": False, "created_at": "2026-05-26T12:00:00"},
            {"id": "2", "title": "Task B", "money_amount": 200.0, "payment_status": "done", "job_status": "pending", "is_fulfilled": False, "created_at": "2026-05-26T12:00:00"},
        ])

        result = await run_agent(
            client=mock_client,
            collection=mock_collection,
            chat_id=123,
            user_prompt="What tasks are not done?",
        )

    assert "2" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_agent.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write implementation**

```python
# src/agent.py
import json

import anthropic
from motor.motor_asyncio import AsyncIOMotorCollection

from src import services
from src.models import TransactionCreate, TransactionUpdate

SYSTEM_PROMPT = """You are a financial transaction assistant for a Telegram bot. You manage transactions (freelance tasks, payments, jobs).

Rules:
- Use the provided tools to perform operations. Never guess or fabricate data.
- Respond in the same language the user writes in.
- A transaction is "fulfilled" when both payment_status and job_status are "done".
- To fulfill a transaction, use update_transaction to set both statuses to "done".
- When the user refers to transactions by name, use get_unfulfilled_transactions or get_historical_transactions to find them, then match by title using your judgment.
- After performing operations, confirm what was done with a clear summary.
- Format monetary amounts with $ sign.
- Keep responses concise and informative."""

TOOLS = [
    {
        "name": "create_transaction",
        "description": "Create a new transaction. Use when the user wants to add a new task, job, or payment record.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title for the transaction"},
                "description": {"type": "string", "description": "Optional longer description"},
                "money_amount": {"type": "number", "description": "Amount in USD"},
                "payment_status": {"type": "string", "enum": ["pending", "done"], "description": "Payment status, defaults to pending"},
                "job_status": {"type": "string", "enum": ["pending", "done"], "description": "Job/work status, defaults to pending"},
            },
            "required": ["title", "money_amount"],
        },
    },
    {
        "name": "update_transaction",
        "description": "Update an existing transaction. Use to change title, description, amount, or statuses. To fulfill a transaction, set both payment_status and job_status to 'done'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string", "description": "The transaction ID to update"},
                "title": {"type": "string", "description": "New title"},
                "description": {"type": "string", "description": "New description"},
                "money_amount": {"type": "number", "description": "New amount in USD"},
                "payment_status": {"type": "string", "enum": ["pending", "done"], "description": "New payment status"},
                "job_status": {"type": "string", "enum": ["pending", "done"], "description": "New job status"},
            },
            "required": ["transaction_id"],
        },
    },
    {
        "name": "delete_transaction",
        "description": "Delete a transaction. Use when the user wants to remove a transaction entirely.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string", "description": "The transaction ID to delete"},
            },
            "required": ["transaction_id"],
        },
    },
    {
        "name": "get_unfulfilled_transactions",
        "description": "Get all transactions that are not yet fulfilled (where payment or job is still pending). Use to list open/active tasks.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_historical_transactions",
        "description": "Get the 10 most recent transactions regardless of status. Use for history, overview, or when the user asks about past transactions.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


async def _execute_tool(
    collection: AsyncIOMotorCollection, chat_id: int, tool_name: str, tool_input: dict
) -> str:
    if tool_name == "create_transaction":
        data = TransactionCreate(**tool_input)
        result = await services.create_transaction(collection, chat_id, data)
        return json.dumps(result, ensure_ascii=False)

    elif tool_name == "update_transaction":
        transaction_id = tool_input.pop("transaction_id")
        data = TransactionUpdate(**tool_input)
        result = await services.update_transaction(collection, chat_id, transaction_id, data)
        if result is None:
            return json.dumps({"error": "Transaction not found"})
        return json.dumps(result, ensure_ascii=False)

    elif tool_name == "delete_transaction":
        success = await services.delete_transaction(collection, chat_id, tool_input["transaction_id"])
        return json.dumps({"success": success})

    elif tool_name == "get_unfulfilled_transactions":
        results = await services.get_unfulfilled_transactions(collection, chat_id)
        return json.dumps(results, ensure_ascii=False)

    elif tool_name == "get_historical_transactions":
        results = await services.get_historical_transactions(collection, chat_id)
        return json.dumps(results, ensure_ascii=False)

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


async def run_agent(
    client: anthropic.AsyncAnthropic,
    collection: AsyncIOMotorCollection,
    chat_id: int,
    user_prompt: str,
) -> str:
    messages = [{"role": "user", "content": user_prompt}]

    while True:
        response = await client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    return block.text
            return "Done."

        tool_results = []
        text_parts = []

        for block in response.content:
            if block.type == "tool_use":
                result = await _execute_tool(collection, chat_id, block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
            elif block.type == "text":
                text_parts.append(block.text)

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agent.py -v`
Expected: PASS (all 2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/agent.py tests/test_agent.py
git commit -m "feat: claude agent with tool definitions and execution loop"
```

---

### Task 7: Telegram Bot Handler

**Files:**
- Create: `src/bot.py`

- [ ] **Step 1: Write implementation**

```python
# src/bot.py
import anthropic
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.agent import run_agent
from src.config import settings
from src.db import get_collection

USAGE_HINT = (
    "Usage: /accounter <your request>\n\n"
    "Examples:\n"
    "• /accounter Заряди 100$ за оновлення блоків\n"
    "• /accounter Які є незавершені задачі?\n"
    "• /accounter Mark payment as done for documentation task"
)


async def accounter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(USAGE_HINT)
        return

    user_prompt = " ".join(context.args)
    chat_id = update.effective_chat.id

    await update.effective_chat.send_action("typing")

    collection = get_collection(settings.mongodb_uri, settings.mongodb_db_name)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        response = await run_agent(
            client=client,
            collection=collection,
            chat_id=chat_id,
            user_prompt=user_prompt,
        )
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


def create_bot() -> Application:
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("accounter", accounter_handler))
    return app
```

- [ ] **Step 2: Commit**

```bash
git add src/bot.py
git commit -m "feat: telegram bot with /accounter command handler"
```

---

### Task 8: Entry Point

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: Write implementation**

```python
# src/main.py
import asyncio
import logging

from src.bot import create_bot
from src.config import settings
from src.db import init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application):
    await init_db(settings.mongodb_uri, settings.mongodb_db_name)
    logger.info("Database initialized")


def main():
    logger.info("Starting Accounter Bot")
    app = create_bot()
    app.post_init = post_init
    app.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: application entry point with db init and bot polling"
```

---

### Task 9: Docker Setup

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python", "-m", "src.main"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
services:
  bot:
    build: .
    env_file: .env
    depends_on:
      - mongo
    restart: unless-stopped

  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

volumes:
  mongo_data:
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: docker setup with bot and mongodb services"
```

---

### Task 10: Deployment Scripts

**Files:**
- Create: `scripts/start.sh`
- Create: `scripts/stop.sh`
- Create: `scripts/restart.sh`
- Create: `scripts/update.sh`

- [ ] **Step 1: Create scripts/start.sh**

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
docker compose up -d --build
echo "Accounter Bot started."
```

- [ ] **Step 2: Create scripts/stop.sh**

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
docker compose down
echo "Accounter Bot stopped."
```

- [ ] **Step 3: Create scripts/restart.sh**

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
bash scripts/stop.sh
bash scripts/start.sh
```

- [ ] **Step 4: Create scripts/update.sh**

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "Pulling latest changes..."
git pull
echo "Rebuilding and restarting..."
docker compose up -d --build
echo "Accounter Bot updated and restarted."
```

- [ ] **Step 5: Make scripts executable**

```bash
chmod +x scripts/*.sh
```

- [ ] **Step 6: Commit**

```bash
git add scripts/
git commit -m "feat: deployment scripts for start, stop, restart, update"
```

---

### Task 11: Deployment Documentation

**Files:**
- Create: `DEPLOYMENT.md`

- [ ] **Step 1: Create DEPLOYMENT.md**

```markdown
# Accounter Telegram Bot — Deployment Guide

## Prerequisites

- Ubuntu 22.04+ with Docker and Docker Compose installed
- CloudPanel installed and configured
- A domain name pointed to your server's IP
- Telegram Bot token (from @BotFather)
- Anthropic API key

## 1. Install Docker (if not installed)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

## 2. Clone and Configure

```bash
cd /home/your-user/htdocs
git clone <your-repo-url> buhalter
cd buhalter

cp .env.example .env
nano .env
# Fill in:
#   TELEGRAM_BOT_TOKEN=your-token-from-botfather
#   ANTHROPIC_API_KEY=your-anthropic-key
#   MONGODB_URI=mongodb://mongo:27017
#   MONGODB_DB_NAME=buhalter
```

## 3. Start the Bot

```bash
bash scripts/start.sh
```

Verify it's running:

```bash
docker compose logs -f bot
```

You should see "Starting Accounter Bot" and "Database initialized". Test by sending `/accounter test` to your bot in Telegram.

## 4. CloudPanel Reverse Proxy Setup

> **Note:** The bot uses Telegram long-polling and does NOT need a public port or reverse proxy to function. This section is only needed if you want to expose a health-check endpoint or add webhook support later.

### If you need a domain for future webhook support:

1. **Create a new site in CloudPanel:**
   - Go to CloudPanel → Sites → Add Site
   - Choose "Node.js" or "Reverse Proxy" application type
   - Set domain name (e.g., `bot.yourdomain.com`)

2. **Configure reverse proxy in Vhost:**
   - Go to the site → Vhost tab
   - Replace the Nginx config with:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name bot.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name bot.yourdomain.com;

    ssl_certificate /etc/nginx/ssl-certificates/bot.yourdomain.com.crt;
    ssl_certificate_key /etc/nginx/ssl-certificates/bot.yourdomain.com.key;

    location / {
        proxy_pass http://127.0.0.1:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Issue SSL certificate:**
   - Go to the site → SSL/TLS tab
   - Click "New Let's Encrypt Certificate"
   - Enable auto-renewal

### Current setup (long-polling, no proxy needed):

The bot runs as a Docker container and communicates with Telegram's servers directly. No incoming connections are needed, so no reverse proxy or open ports are required. Just make sure the server has outbound HTTPS access.

## 5. Updates

To deploy new changes:

```bash
cd /home/your-user/htdocs/buhalter
bash scripts/update.sh
```

This pulls the latest code, rebuilds the Docker image, and restarts the container.

## 6. Monitoring

```bash
# View bot logs
docker compose logs -f bot

# View MongoDB logs
docker compose logs -f mongo

# Check container status
docker compose ps
```

## 7. Backup MongoDB Data

```bash
# Dump the database
docker compose exec mongo mongodump --db buhalter --out /data/backup

# Copy backup from container
docker compose cp mongo:/data/backup ./backup
```
```

- [ ] **Step 2: Commit**

```bash
git add DEPLOYMENT.md
git commit -m "docs: deployment guide for Ubuntu with CloudPanel reverse proxy"
```

---

## Self-Review

**Spec coverage check:**
- [x] Transaction data model with all fields — Task 3
- [x] Derived fulfilled state (no stored field) — Task 3 (`is_fulfilled` property)
- [x] 5 CRUD operations — Task 5
- [x] Claude agent with tool_use — Task 6
- [x] System prompt with language matching — Task 6
- [x] Multi-step agent loop — Task 6
- [x] Telegram bot with /accounter command — Task 7
- [x] Stateless per-command — Task 7
- [x] Chat-scoped transactions — Task 5 (all queries filter by `chat_id`)
- [x] Typing indicator — Task 7
- [x] Docker Compose (bot + mongo) — Task 9
- [x] Environment variables — Task 2
- [x] Deployment scripts — Task 10
- [x] DEPLOYMENT.md with CloudPanel — Task 11
- [x] MongoDB index — Task 4

**Placeholder scan:** No TBDs, TODOs, or vague steps. All code is complete.

**Type consistency:** `TransactionCreate`, `TransactionUpdate`, `TransactionDoc` used consistently across models → services → agent. `_doc_to_dict` / `to_display_dict` consistent. Tool names match between `TOOLS` list and `_execute_tool` handler.
