"""Repositorio async para la coleccion ``doctor_profiles``.

Gestiona el acceso a la coleccion ``doctor_profiles`` de la BD Doctoralia (27017).
Los documentos se identifican con un ``_id`` de tipo cadena ``"doctor:{id}"``
y tienen la estructura anidada equivalente a la del ``index.ts``.

## Colecciones y esquema

- Coleccion: ``doctor_profiles``
- ``_id``: ``"doctor:{id_doctoralia}"`` (string)
- Campos principales: ``doctor``, ``total_opiniones``, ``rating_global``,
  ``metadata``, ``queue_meta``.
"""

from datetime import datetime, timezone

# pyrefly: ignore [missing-import]
from pymongo import ASCENDING, ReplaceOne

from app.db.mongo import get_doctoralia_async_db


_COLECCION = "doctor_profiles"
_indices_creados = False


def _get_doc_id(id_doctoralia: int) -> str:
    """Devuelve el _id canonico para un doctor.

    Args:
        id_doctoralia: Identificador numerico del doctor en Doctoralia.

    Returns:
        Cadena ``"doctor:{id_doctoralia}"``.
    """
    return f"doctor:{id_doctoralia}"


async def _obtener_coleccion():
    """Retorna la coleccion ``doctor_profiles`` de la BD Doctoralia.

    Returns:
        Coleccion Motor ``doctor_profiles``.
    """
    db = get_doctoralia_async_db()
    return db[_COLECCION]


async def _asegurar_indices() -> None:
    """Crea los indices necesarios en ``doctor_profiles`` (idempotente).

    Crea:
    - Indice sobre ``doctor.id_doctoralia`` (busqueda por ID numerico).
    - Indice sobre ``doctor.nombre`` (busqueda textual rapida).
    - Indice sobre ``total_opiniones`` (ordenamiento por popularidad).
    """
    global _indices_creados
    if _indices_creados:
        return

    coleccion = await _obtener_coleccion()
    await coleccion.create_index([("doctor.id_doctoralia", ASCENDING)])
    await coleccion.create_index([("doctor.nombre", ASCENDING)])
    await coleccion.create_index([("total_opiniones", ASCENDING)])
    _indices_creados = True


async def upsert_perfil(doc: dict) -> str:
    """Inserta o reemplaza el perfil de un doctor en ``doctor_profiles``.

    Usa ``replaceOne`` con ``upsert=True``. El campo ``_id`` debe existir en
    ``doc`` con formato ``"doctor:{id_doctoralia}"`` o bien debe estar
    ``doc["doctor"]["id_doctoralia"]`` definido para construirlo.

    Si el documento contiene ``queue_meta``, actualiza solo ese campo para no
    sobreescribir ``discovery_sources`` acumulados. En caso contrario hace un
    replace completo.

    Args:
        doc: Documento completo del perfil con la estructura anidada.

    Returns:
        El ``_id`` (string) del documento insertado o actualizado.

    Ejemplo::

        _id = await upsert_perfil({
            "_id": "doctor:2532",
            "doctor": {"id_doctoralia": 2532, "nombre": "Dr. Juan", ...},
            "total_opiniones": 100,
            ...
        })
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()

    # Derivar _id
    doc_id = doc.get("_id")
    if not doc_id:
        id_doctoralia = (doc.get("doctor") or {}).get("id_doctoralia")
        if id_doctoralia is None:
            raise ValueError("El documento debe tener '_id' o 'doctor.id_doctoralia'.")
        doc_id = _get_doc_id(id_doctoralia)
        doc = {**doc, "_id": doc_id}

    # Si hay queue_meta, necesitamos conservar discovery_sources acumulados
    queue_meta = doc.pop("queue_meta", None)

    await coleccion.replace_one({"_id": doc_id}, doc, upsert=True)

    if queue_meta is not None:
        discovery_sources = queue_meta.get("discovery_sources") or []
        priority_score = queue_meta.get("priority_score", 0)
        update = {
            "$set": {
                "queue_meta.priority_score": priority_score,
                "queue_meta.persistedAt": datetime.now(timezone.utc),
            },
            "$addToSet": {
                "queue_meta.discovery_sources": {
                    "$each": discovery_sources,
                }
            },
        }
        # Si no existe aun el campo queue_meta en el documento recien insertado,
        # $setOnInsert no aplica en update posterior; usamos $set para inicializar.
        await coleccion.update_one(
            {"_id": doc_id, "queue_meta": {"$exists": False}},
            {
                "$set": {
                    "queue_meta": {
                        "discovery_sources": discovery_sources,
                        "priority_score": priority_score,
                        "persistedAt": datetime.now(timezone.utc),
                    }
                }
            },
        )
        # Actualizar en caso de que ya exista
        await coleccion.update_one(
            {"_id": doc_id, "queue_meta": {"$exists": True}},
            {
                "$set": {
                    "queue_meta.priority_score": priority_score,
                    "queue_meta.persistedAt": datetime.now(timezone.utc),
                },
                "$addToSet": {
                    "queue_meta.discovery_sources": {"$each": discovery_sources}
                },
            },
        )

    return doc_id


async def upsert_perfiles_masivo(docs: list[dict]) -> dict:
    """Inserta o reemplaza multiples perfiles en ``doctor_profiles`` con bulk_write.

    Args:
        docs: Lista de documentos de perfil con estructura anidada. Cada uno
            debe tener ``_id`` o ``doctor.id_doctoralia``.

    Returns:
        Diccionario ``{"insertados": int, "actualizados": int}``.

    Ejemplo::

        resultado = await upsert_perfiles_masivo(lista_de_docs)
        print(resultado["insertados"])
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()

    operaciones = []
    for doc in docs:
        doc_id = doc.get("_id")
        if not doc_id:
            id_doctoralia = (doc.get("doctor") or {}).get("id_doctoralia")
            if id_doctoralia is None:
                continue
            doc_id = _get_doc_id(id_doctoralia)
        doc_copy = {**doc, "_id": doc_id}
        operaciones.append(ReplaceOne({"_id": doc_id}, doc_copy, upsert=True))

    if not operaciones:
        return {"insertados": 0, "actualizados": 0}

    resultado = await coleccion.bulk_write(operaciones, ordered=False)
    return {
        "insertados": resultado.upserted_count,
        "actualizados": resultado.modified_count,
    }


async def buscar_por_id_doctoralia(id_doctoralia: int) -> dict | None:
    """Busca un perfil por su ID numerico de Doctoralia.

    Args:
        id_doctoralia: ID numerico del doctor en Doctoralia.

    Returns:
        Documento del perfil o ``None`` si no existe.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    doc_id = _get_doc_id(id_doctoralia)
    return await coleccion.find_one({"_id": doc_id})


async def buscar_por_string_id(doc_id: str) -> dict | None:
    """Busca un perfil por su ``_id`` de cadena (``"doctor:{id}"``).

    Args:
        doc_id: Identificador de cadena, por ejemplo ``"doctor:2532"``.

    Returns:
        Documento del perfil o ``None`` si no existe.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    return await coleccion.find_one({"_id": doc_id})
