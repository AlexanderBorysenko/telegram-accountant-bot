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
