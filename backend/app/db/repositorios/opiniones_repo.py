"""Repositorio async para la coleccion de opiniones."""

from pymongo import ASCENDING, DESCENDING, UpdateOne

from app.db.mongo import get_mongo_async_db


_indices_creados = False


def _clave_opinion(opinion_id: int) -> dict:
    return {"opinion_id": opinion_id}


async def _obtener_coleccion():
    db = get_mongo_async_db()
    return db["opiniones"]


async def _asegurar_indices():
    global _indices_creados
    if _indices_creados:
        return

    coleccion = await _obtener_coleccion()
    await coleccion.create_index([("opinion_id", ASCENDING)], unique=True)
    await coleccion.create_index([("doctor_id", ASCENDING)])
    await coleccion.create_index([("fecha_publicacion", DESCENDING)])
    _indices_creados = True


async def obtener_opiniones_por_doctor(
    doctor_id: int,
    limite: int | None = None,
) -> list[dict]:
    """Retorna las opiniones de un medico ordenadas de mas reciente a mas antigua."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    cursor = coleccion.find({"doctor_id": doctor_id}).sort("fecha_publicacion", -1)
    if limite:
        cursor = cursor.limit(limite)
    return [doc async for doc in cursor]


async def contar_opiniones_por_doctor(doctor_id: int) -> int:
    """Retorna cuantas opiniones existen en Mongo para un medico."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    return await coleccion.count_documents({"doctor_id": doctor_id})


async def insertar_opiniones_masivo(opiniones: list[dict]) -> int:
    """Inserta o actualiza opiniones usando upsert por opinion_id."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()

    operaciones = []
    for opinion in opiniones:
        opinion_id = opinion.get("opinion_id")
        if not opinion_id:
            continue
        operaciones.append(UpdateOne(_clave_opinion(opinion_id), {"$set": opinion}, upsert=True))

    if not operaciones:
        return 0

    resultado = await coleccion.bulk_write(operaciones)
    return resultado.upserted_count + resultado.modified_count


async def eliminar_opiniones_por_doctor(doctor_id: int) -> int:
    """Elimina todas las opiniones de un medico. Retorna cantidad eliminada."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    resultado = await coleccion.delete_many({"doctor_id": doctor_id})
    return resultado.deleted_count
