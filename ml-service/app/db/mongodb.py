from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

_client: AsyncIOMotorClient | None = None


async def get_database():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)
    return _client[settings.mongo_db_name]


async def close_database():
    global _client
    if _client is not None:
        _client.close()
        _client = None
