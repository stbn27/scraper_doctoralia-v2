import os
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.database import Database

_client: Optional[MongoClient] = None
_async_client: Optional[AsyncIOMotorClient] = None

def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(
            os.getenv("MONGO_URL", "mongodb://mongodb:27017"),
            serverSelectionTimeoutMS=5000
        )
    return _client

def get_mongo_db() -> Database:
    client = get_mongo_client()
    return client[os.getenv("MONGO_DB", "medicos_db")]


def get_mongo_async_client() -> AsyncIOMotorClient:
    """Retorna un cliente Motor singleton para operaciones async."""
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(
            os.getenv("MONGO_URL", "mongodb://mongodb:27017"),
            serverSelectionTimeoutMS=5000,
        )
    return _async_client


def get_mongo_async_db() -> AsyncIOMotorDatabase:
    """Retorna la base de datos Motor configurada para operaciones async."""
    client = get_mongo_async_client()
    return client[os.getenv("MONGO_DB", "medicos_db")]