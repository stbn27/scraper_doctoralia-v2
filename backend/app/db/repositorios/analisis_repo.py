"""
Repositorio async para la colección `analisis_especialistas` en MongoDB.

Proporciona acceso de solo lectura a los análisis IA generados por el pipeline NLP.
El pipeline NLP escribe en esta colección; este repo solo lee.
"""

from typing import Optional

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from app.db.mongo import get_mongo_async_db

_indices_creados = False


async def _obtener_coleccion():
    """Retorna la colección `analisis_especialistas` de MongoDB."""
    db = get_mongo_async_db()
    return db["analisis_especialistas"]


async def _asegurar_indices():
    """
    Crea índices necesarios en `analisis_especialistas` si no existen.

    Ignora conflictos con índices pre-existentes de versiones anteriores del pipeline.

    Retorna
    -------
    None
    """
    global _indices_creados
    if _indices_creados:
        return

    from pymongo.errors import OperationFailure

    col = await _obtener_coleccion()
    for campo, direccion in [
        ("doctoralia_id", ASCENDING),
        ("estado", ASCENDING),
        ("resultado_ia.puntuacion_recomendacion", DESCENDING),
        ("resultado_ia.confiabilidad_opiniones", ASCENDING),
        ("metricas_locales.sospecha_fraude", ASCENDING),
    ]:
        try:
            await col.create_index([(campo, direccion)])
        except OperationFailure:
            pass  # El índice ya existe con otra especificación; se ignora

    _indices_creados = True


async def obtener_por_doctoralia_id(doctoralia_id: int) -> Optional[dict]:
    """
    Busca el análisis IA de un especialista por su ID de Doctoralia.

    Parámetros
    ----------
    doctoralia_id : int
        ID numérico del especialista en Doctoralia.

    Retorna
    -------
    dict o None
        Documento de análisis o None si no existe.
    """
    await _asegurar_indices()
    col = await _obtener_coleccion()
    doc = await col.find_one({"doctoralia_id": doctoralia_id})
    if not doc:
        doc = await col.find_one({"doctor_id": doctoralia_id})
    return doc


async def obtener_por_doctoralia_ids(ids: list[int]) -> dict[int, dict]:
    """
    Obtiene múltiples análisis por lista de doctoralia_id.

    Usado para enriquecer resultados de búsqueda paginada sin N+1 queries.

    Parámetros
    ----------
    ids : list[int]
        Lista de IDs de Doctoralia a consultar.

    Retorna
    -------
    dict[int, dict]
        Mapa de doctoralia_id → documento de análisis.
    """
    await _asegurar_indices()
    col = await _obtener_coleccion()
    cursor = col.find(
        {"$or": [{"doctoralia_id": {"$in": ids}}, {"doctor_id": {"$in": ids}}]}
    )
    resultado: dict[int, dict] = {}
    async for doc in cursor:
        did = doc.get("doctoralia_id") or doc.get("doctor_id")
        if did:
            resultado[did] = doc
    return resultado
