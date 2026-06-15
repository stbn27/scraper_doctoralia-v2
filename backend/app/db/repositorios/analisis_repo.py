"""
Repositorio async para la colección `analisis_especialistas` en MongoDB.

Proporciona acceso de solo lectura a los análisis IA generados por el pipeline NLP.
Lee de la BD Doctoralia (27017) donde el pipeline escribe los resultados.
"""

from typing import Optional

# pyrefly: ignore [missing-import]
from pymongo import ASCENDING, DESCENDING

from app.db.mongo import get_doctoralia_async_db

_indices_creados = False


async def _obtener_coleccion():
    """Retorna la colección `analisis_especialistas` de la BD Doctoralia."""
    db = get_doctoralia_async_db()
    return db["analisis_especialistas"]


async def _asegurar_indices():
    """
    Crea índices necesarios en `analisis_especialistas` si no existen.

    Usa los campos del nuevo esquema Doctoralia:
    - ``id_doctoralia`` como campo principal de búsqueda.
    - ``analisis.puntuacion`` y ``analisis.confiabilidad`` para filtros de calidad.
    - ``metadata_opiniones.sospecha_fraude`` para filtros de fraude.

    Retorna
    -------
    None
    """
    global _indices_creados
    if _indices_creados:
        return

    # pyrefly: ignore [missing-import]
    from pymongo.errors import OperationFailure

    col = await _obtener_coleccion()
    for campo, direccion in [
        ("id_doctoralia", ASCENDING),
        ("estatus_analisis", ASCENDING),
        ("analisis.puntuacion", DESCENDING),
        ("analisis.confiabilidad", ASCENDING),
        ("metadata_opiniones.sospecha_fraude", ASCENDING),
    ]:
        try:
            await col.create_index([(campo, direccion)])
        except OperationFailure:
            pass  # Índice ya existe con otra especificación; se ignora

    _indices_creados = True


async def obtener_por_doctoralia_id(doctoralia_id: int) -> Optional[dict]:
    """
    Busca el análisis IA de un especialista por su ID de Doctoralia.

    Busca primero por ``id_doctoralia`` (campo del nuevo esquema).

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
    doc = await col.find_one({"id_doctoralia": doctoralia_id})
    return doc


async def obtener_por_doctoralia_ids(ids: list[int]) -> dict[int, dict]:
    """
    Obtiene múltiples análisis por lista de id_doctoralia.

    Usado para enriquecer resultados de búsqueda paginada sin N+1 queries.

    Parámetros
    ----------
    ids : list[int]
        Lista de IDs de Doctoralia a consultar.

    Retorna
    -------
    dict[int, dict]
        Mapa de id_doctoralia → documento de análisis.
    """
    await _asegurar_indices()
    col = await _obtener_coleccion()
    cursor = col.find({"id_doctoralia": {"$in": ids}})
    resultado: dict[int, dict] = {}
    async for doc in cursor:
        did = doc.get("id_doctoralia")
        if did:
            resultado[did] = doc
    return resultado
