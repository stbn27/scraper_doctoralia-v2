"""
Módulo de conexión a MongoDB.

Expone dos pares de clientes/DB:
- ``get_mongo_*``           → BD legacy (27018, colección ``especialistas``).
- ``get_doctoralia_*``      → BD nueva Doctoralia (27017, colecciones scrapeadas).

Usa el patrón singleton con clientes globales para evitar conexiones redundantes.
"""

import os
from typing import Optional

# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
# pyrefly: ignore [missing-import]
from pymongo import MongoClient
# pyrefly: ignore [missing-import]
from pymongo.database import Database

# ─── Clientes legacy (27018) ────────────────────────────────────────────────
_client: Optional[MongoClient] = None
_async_client: Optional[AsyncIOMotorClient] = None

# ─── Clientes nueva BD Doctoralia (27017) ───────────────────────────────────
_doctoralia_client: Optional[MongoClient] = None
_doctoralia_async_client: Optional[AsyncIOMotorClient] = None


# =============================================================================
# BD Legacy
# =============================================================================

def get_mongo_client() -> MongoClient:
    """Retorna el cliente MongoClient singleton para la BD legacy (síncrono)."""
    global _client
    if _client is None:
        _client = MongoClient(
            os.getenv("MONGO_URL", "mongodb://localhost:27018"),
            serverSelectionTimeoutMS=5000,
        )
    return _client


def get_mongo_db() -> Database:
    """Retorna la base de datos legacy (síncrona)."""
    client = get_mongo_client()
    return client[os.getenv("MONGO_DB", "medicos_db")]


def get_mongo_async_client() -> AsyncIOMotorClient:
    """Retorna el cliente Motor singleton para la BD legacy (asíncrono)."""
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(
            os.getenv("MONGO_URL", "mongodb://localhost:27018"),
            serverSelectionTimeoutMS=5000,
        )
    return _async_client


def get_mongo_async_db() -> AsyncIOMotorDatabase:
    """Retorna la base de datos Motor legacy (asíncrona)."""
    client = get_mongo_async_client()
    return client[os.getenv("MONGO_DB", "medicos_db")]


# =============================================================================
# BD Doctoralia (nueva, 27017)
# =============================================================================

def get_doctoralia_client() -> MongoClient:
    """
    Retorna el cliente MongoClient singleton para la BD Doctoralia (síncrono).

    Lee ``MONGO_URL_DOCTORALIA`` y ``MONGO_DB_DOCTORALIA`` del entorno.
    """
    global _doctoralia_client
    if _doctoralia_client is None:
        _doctoralia_client = MongoClient(
            os.getenv(
                "MONGO_URL_DOCTORALIA",
                "mongodb://admin:password123@127.0.0.1:27017/doctoralia?authSource=admin",
            ),
            serverSelectionTimeoutMS=5000,
        )
    return _doctoralia_client


def get_doctoralia_db() -> Database:
    """Retorna la base de datos Doctoralia (síncrona)."""
    client = get_doctoralia_client()
    return client[os.getenv("MONGO_DB_DOCTORALIA", "doctoralia")]


def get_doctoralia_async_client() -> AsyncIOMotorClient:
    """
    Retorna el cliente Motor singleton para la BD Doctoralia (asíncrono).

    Ejemplo
    -------
    >>> db = get_doctoralia_async_db()
    >>> docs = await db["specializations"].find({}).to_list(100)
    """
    global _doctoralia_async_client
    if _doctoralia_async_client is None:
        _doctoralia_async_client = AsyncIOMotorClient(
            os.getenv(
                "MONGO_URL_DOCTORALIA",
                "mongodb://admin:password123@127.0.0.1:27017/doctoralia?authSource=admin",
            ),
            serverSelectionTimeoutMS=5000,
        )
    return _doctoralia_async_client


def get_doctoralia_async_db() -> AsyncIOMotorDatabase:
    """Retorna la base de datos Motor Doctoralia (asíncrona)."""
    client = get_doctoralia_async_client()
    return client[os.getenv("MONGO_DB_DOCTORALIA", "doctoralia")]
