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
- Keep responses concise and informative.

Response format (follow strictly, never use Markdown, tables, or bold):
- Use plain text with emojis only.
- Emojis: 📌 title, 💰 payment, 💼 job, ⏳ pending, ✅ done.

Single transaction:
✅ <short action summary>

📌 Title — $amount
💼 ⏳ pending
💰 ✅ done

Transaction list:
1. Title — $amount
   💼 ⏳ · 💰 ✅
2. Title — $amount
   💼 ⏳ · 💰 ⏳

Total: $amount

Add a one-line summary at the end if useful. Never deviate from this format."""

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
            model="claude-sonnet-4-6",
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
