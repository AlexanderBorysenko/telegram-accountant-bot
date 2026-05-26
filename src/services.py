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
    cursor = collection.find({"chat_id": chat_id}).sort("created_at", -1)
    docs = await cursor.to_list(length=10)
    return [_doc_to_dict(d) for d in docs]
