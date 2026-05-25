"""Repositorio async para la coleccion de especialistas."""

import re

from bson import ObjectId
from pymongo import ASCENDING

from app.db.mongo import get_mongo_async_db


_indices_creados = False


def _normalizar_regex(valor: str) -> dict:
    return {"$regex": re.escape(valor), "$options": "i"}


async def _obtener_coleccion():
    db = get_mongo_async_db()
    return db["especialistas"]


async def _asegurar_indices():
    global _indices_creados
    if _indices_creados:
        return

    coleccion = await _obtener_coleccion()
    await coleccion.create_index([("doctoralia_id", ASCENDING)], unique=True, sparse=True)
    await coleccion.create_index(
        [("especialidad", ASCENDING), ("ciudad", ASCENDING)]
    )
    _indices_creados = True


async def obtener_por_especialidad_y_ciudad(
    especialidad: str, ciudad: str
) -> list[dict]:
    """Obtiene especialistas filtrando por especialidad y ciudad."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    filtro = {
        "especialidad": _normalizar_regex(especialidad),
        "ciudad": _normalizar_regex(ciudad),
    }
    cursor = coleccion.find(filtro)
    return [doc async for doc in cursor]


async def insertar_especialista(doc: dict) -> str:
    """Inserta o actualiza un especialista usando upsert por doctoralia_id."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()

    doctoralia_id = doc.get("doctoralia_id")
    if doctoralia_id is None:
        resultado = await coleccion.insert_one(doc)
        return str(resultado.inserted_id)

    resultado = await coleccion.update_one(
        {"doctoralia_id": doctoralia_id}, {"$set": doc}, upsert=True
    )
    if resultado.upserted_id:
        return str(resultado.upserted_id)

    existente = await coleccion.find_one({"doctoralia_id": doctoralia_id})
    return str(existente.get("_id")) if existente else ""


async def actualizar_especialista(doctoralia_id: int, doc: dict) -> bool:
    """Actualiza un especialista por doctoralia_id."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    resultado = await coleccion.update_one(
        {"doctoralia_id": doctoralia_id}, {"$set": doc}
    )
    return resultado.modified_count > 0


async def buscar_por_doctoralia_id(doctoralia_id: int) -> dict | None:
    """Busca un especialista por doctoralia_id."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    return await coleccion.find_one({"doctoralia_id": doctoralia_id})


async def buscar_por_id(id: str) -> dict | None:
    """Busca un especialista por ObjectId."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    try:
        oid = ObjectId(id)
    except Exception:
        return None
    return await coleccion.find_one({"_id": oid})


async def eliminar_especialista(id: str) -> bool:
    """Elimina un especialista por ObjectId."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    try:
        oid = ObjectId(id)
    except Exception:
        return False
    resultado = await coleccion.delete_one({"_id": oid})
    return resultado.deleted_count > 0


async def listar_especialistas(filtros: dict, limite: int = 50) -> list[dict]:
    """Lista especialistas aplicando filtros y limite."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    cursor = coleccion.find(filtros).limit(limite)
    return [doc async for doc in cursor]
