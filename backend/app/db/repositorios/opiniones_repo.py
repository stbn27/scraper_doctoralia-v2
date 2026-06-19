"""Repositorio async para la coleccion ``doctor_opinions``.

Gestiona el acceso a la coleccion ``doctor_opinions`` de la BD Doctoralia (27017).
Los documentos se identifican con un ``_id`` de tipo cadena:

- ``"opinion:{opinion_id}"`` si la opinion tiene ID numerico conocido.
- ``"opinion-hash:{doctor_id}:{sha1}"`` cuando el ID no esta disponible.

## Esquema de cada documento

Campos principales: ``opinion_id``, ``autor``, ``doctor_id``,
``fecha_publicacion``, ``rating``, ``servicio_consultado``,
``consultorio``, ``texto``, ``tipo_verificacion``, ``scraping_meta``.
"""

import hashlib
from datetime import datetime

from pymongo import ASCENDING, DESCENDING, ReplaceOne

from app.db.mongo import get_doctoralia_async_db


_COLECCION = "doctor_opinions"
_indices_creados = False


def _get_opinion_id(opinion: dict) -> str:
    """Devuelve el ``_id`` canonico para una opinion.

    Si la opinion tiene ``opinion_id`` numerico usa ``"opinion:{id}"``.
    De lo contrario construye un hash SHA-1 a partir de campos clave.

    Args:
        opinion: Diccionario con los datos de la opinion.

    Returns:
        Cadena identificadora unica.
    """
    opinion_id = opinion.get("opinion_id")
    if opinion_id:
        return f"opinion:{opinion_id}"

    digest = hashlib.sha1(
        "|".join([
            str(opinion.get("doctor_id", "")),
            opinion.get("autor") or "",
            opinion.get("fecha_publicacion") or "",
            opinion.get("texto") or "",
            opinion.get("consultorio") or "",
        ]).encode()
    ).hexdigest()
    return f"opinion-hash:{opinion.get('doctor_id', '')}:{digest}"


async def _obtener_coleccion():
    """Retorna la coleccion ``doctor_opinions`` de la BD Doctoralia.

    Returns:
        Coleccion Motor ``doctor_opinions``.
    """
    db = get_doctoralia_async_db()
    return db[_COLECCION]


async def _asegurar_indices() -> None:
    """Crea los indices necesarios en ``doctor_opinions`` (idempotente).

    Crea:
    - Indice sobre ``doctor_id`` (filtrar por medico).
    - Indice sobre ``fecha_publicacion`` descendente (orden cronologico).
    - Indice sobre ``opinion_id`` (deduplicacion rapida).
    """
    global _indices_creados
    if _indices_creados:
        return

    coleccion = await _obtener_coleccion()
    await coleccion.create_index([("doctor_id", ASCENDING), ("fecha_publicacion", DESCENDING)])
    await coleccion.create_index([("opinion_id", ASCENDING)])
    _indices_creados = True


async def obtener_opiniones_por_doctor(
    doctor_id: int,
    limite: int | None = None,
) -> list[dict]:
    """Retorna las opiniones de un medico ordenadas de mas reciente a mas antigua.

    Args:
        doctor_id: ID numerico del doctor en Doctoralia.
        limite: Numero maximo de opiniones a retornar. ``None`` = sin limite.

    Returns:
        Lista de opiniones ordenadas por ``fecha_publicacion`` descendente.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    cursor = coleccion.find({"doctor_id": doctor_id}).sort("fecha_publicacion", -1)
    if limite:
        cursor = cursor.limit(limite)
    return [doc async for doc in cursor]


async def contar_opiniones_por_doctor(doctor_id: int) -> int:
    """Retorna cuantas opiniones existen en Mongo para un medico.

    Args:
        doctor_id: ID numerico del doctor en Doctoralia.

    Returns:
        Cantidad de documentos de opinion existentes.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    return await coleccion.count_documents({"doctor_id": doctor_id})


async def insertar_opiniones_masivo(opiniones: list[dict]) -> int:
    """Inserta o reemplaza opiniones usando upsert por ``_id``.

    Cada opinion se guarda con un ``_id`` canonico derivado de ``opinion_id``
    o de un hash de sus campos clave. Se usa ``ReplaceOne`` para poder
    actualizar opiniones ya existentes sin duplicarlas.

    Args:
        opiniones: Lista de diccionarios de opinion. Cada uno puede tener los
            campos: ``opinion_id``, ``autor``, ``doctor_id``,
            ``fecha_publicacion``, ``rating``, ``texto``, etc.

    Returns:
        Cantidad de documentos insertados o modificados.

    Ejemplo::

        guardadas = await insertar_opiniones_masivo(lista_de_opiniones)
        print(f"{guardadas} opiniones guardadas")
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()

    operaciones = []
    for opinion in opiniones:
        doc_id = _get_opinion_id(opinion)
        doc = {**opinion, "_id": doc_id}
        # Normalizar nombre del campo de fecha si viene como "fecha"
        if "fecha" in doc and "fecha_publicacion" not in doc:
            doc["fecha_publicacion"] = doc.pop("fecha")
        operaciones.append(
            ReplaceOne({"_id": doc_id}, doc, upsert=True)
        )

    if not operaciones:
        return 0

    resultado = await coleccion.bulk_write(operaciones, ordered=False)
    return resultado.upserted_count + resultado.modified_count


async def eliminar_opiniones_por_doctor(doctor_id: int) -> int:
    """Elimina todas las opiniones de un medico. Retorna cantidad eliminada.

    Args:
        doctor_id: ID numerico del doctor en Doctoralia.

    Returns:
        Numero de documentos eliminados.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    resultado = await coleccion.delete_many({"doctor_id": doctor_id})
    return resultado.deleted_count
