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
