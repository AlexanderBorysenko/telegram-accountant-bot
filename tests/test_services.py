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
