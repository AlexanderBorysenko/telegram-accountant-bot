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
