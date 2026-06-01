import os
import socket
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.database import Database

_client: Optional[MongoClient] = None
_async_client: Optional[AsyncIOMotorClient] = None

def _resolver_mongo_url(url: str) -> str:
    """
    Resuelve de forma inteligente la URL de conexión a MongoDB.
    Si la URL contiene el host 'mongodb' y no se puede resolver en la red local
    (por ejemplo, al ejecutar en el host fuera de Docker), hace un fallback automático
    a 'localhost' para garantizar una experiencia de desarrollo fluida y portátil.
    """
    # Verificar si la URL contiene el nombre de host de Docker 'mongodb'
    if "://mongodb:" in url or "://mongodb/" in url:
        try:
            # Intentar resolver el host 'mongodb'
            socket.gethostbyname("mongodb")
        except socket.gaierror:
            # Si no se puede resolver, reemplazar 'mongodb' por 'localhost'
            url = url.replace("://mongodb:", "://localhost:").replace("://mongodb/", "://localhost/")
    return url

def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        raw_url = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
        resolved_url = _resolver_mongo_url(raw_url)
        _client = MongoClient(
            resolved_url,
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
        raw_url = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
        resolved_url = _resolver_mongo_url(raw_url)
        _async_client = AsyncIOMotorClient(
            resolved_url,
            serverSelectionTimeoutMS=5000,
        )
    return _async_client


def get_mongo_async_db() -> AsyncIOMotorDatabase:
    """Retorna la base de datos Motor configurada para operaciones async."""
    client = get_mongo_async_client()
    return client[os.getenv("MONGO_DB", "medicos_db")]