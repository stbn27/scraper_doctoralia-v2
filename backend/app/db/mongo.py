from pymongo import MongoClient
from pymongo.database import Database
from typing import Optional
import os

_client: Optional[MongoClient] = None

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