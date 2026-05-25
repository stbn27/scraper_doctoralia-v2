"""Repositorio async para la coleccion de catalogos."""

from pymongo import ASCENDING, UpdateOne

from app.db.mongo import get_mongo_async_db


_indices_creados = False


def _clave_compuesta(especialidad_slug: str, ciudad_slug: str) -> dict:
    return {"especialidad_slug": especialidad_slug, "ciudad_slug": ciudad_slug}


async def _obtener_coleccion():
    db = get_mongo_async_db()
    return db["catalogos"]


async def _asegurar_indices():
    global _indices_creados
    if _indices_creados:
        return

    coleccion = await _obtener_coleccion()
    await coleccion.create_index(
        [("especialidad_slug", ASCENDING), ("ciudad_slug", ASCENDING)], unique=True
    )
    _indices_creados = True


async def obtener_catalogo_por_especialidad_ciudad(
    especialidad_slug: str, ciudad_slug: str
) -> dict | None:
    """Obtiene un catalogo por especialidad y ciudad."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    return await coleccion.find_one(_clave_compuesta(especialidad_slug, ciudad_slug))


async def insertar_catalogo(doc: dict) -> str:
    """Inserta un nuevo catalogo y retorna su id."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    resultado = await coleccion.insert_one(doc)
    return str(resultado.inserted_id)


async def listar_catalogos() -> list[dict]:
    """Lista todos los catalogos almacenados."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    cursor = coleccion.find({})
    return [doc async for doc in cursor]


async def actualizar_catalogo(
    especialidad_slug: str, ciudad_slug: str, doc: dict
) -> bool:
    """Actualiza un catalogo por especialidad y ciudad."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    resultado = await coleccion.update_one(
        _clave_compuesta(especialidad_slug, ciudad_slug), {"$set": doc}
    )
    return resultado.modified_count > 0


async def upsert_catalogos(documentos: list[dict]) -> dict:
    """Inserta o actualiza multiples catalogos en una sola operacion."""
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()

    operaciones = []
    for doc in documentos:
        clave = _clave_compuesta(doc.get("especialidad_slug"), doc.get("ciudad_slug"))
        operaciones.append(UpdateOne(clave, {"$set": doc}, upsert=True))

    if not operaciones:
        return {"insertados": 0, "actualizados": 0, "procesados": 0}

    resultado = await coleccion.bulk_write(operaciones)
    return {
        "insertados": resultado.upserted_count,
        "actualizados": resultado.modified_count,
        "procesados": len(operaciones),
    }
