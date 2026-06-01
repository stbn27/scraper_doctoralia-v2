"""
Repositorio para la colección `analisis_especialistas` en MongoDB.

Usa cliente síncrono (PyMongo) para el pipeline CLI.

Funciones principales:
    - guardar_analisis: Upsert por doctor_id.
    - obtener_analisis_por_doctor: Busca análisis por doctor_id.
    - analisis_existente_reciente: Verifica si hay análisis reciente.
    - listar_pendientes: Doctores que necesitan análisis.
    - marcar_error: Marca un análisis con estado de error.
"""

from datetime import datetime, timezone, timedelta

from pymongo import ASCENDING

from app.db.mongo import get_mongo_db


_indices_creados = False
_COLECCION = "analisis_especialistas"


def _obtener_coleccion():
    """
    Retorna la colección `analisis_especialistas` de MongoDB (síncrona).

    Retorna
    -------
    Collection
        Colección de PyMongo para operaciones síncronas.
    """
    db = get_mongo_db()
    return db[_COLECCION]


def _asegurar_indices():
    """
    Crea los índices necesarios en la colección si aún no se han creado.
    Índices: doctor_id (único), estado, fecha_analisis.
    """
    global _indices_creados
    if _indices_creados:
        return

    coleccion = _obtener_coleccion()
    coleccion.create_index(
        [("doctor_id", ASCENDING)], unique=True, sparse=True
    )
    coleccion.create_index([("estado", ASCENDING)])
    coleccion.create_index([("fecha_analisis", ASCENDING)])
    _indices_creados = True


def guardar_analisis(doc: dict) -> str:
    """
    Upsert de un documento de análisis por doctor_id.

    Parámetros
    ----------
    doc : dict
        Documento completo de análisis con doctor_id.

    Retorna
    -------
    str
        El _id del documento insertado o actualizado.
    """
    _asegurar_indices()
    coleccion = _obtener_coleccion()
    doctor_id = doc.get("doctor_id")

    resultado = coleccion.update_one(
        {"doctor_id": doctor_id},
        {"$set": doc},
        upsert=True,
    )

    if resultado.upserted_id:
        return str(resultado.upserted_id)

    existente = coleccion.find_one({"doctor_id": doctor_id})
    return str(existente.get("_id")) if existente else ""


def obtener_analisis_por_doctor(doctor_id: int) -> dict | None:
    """
    Obtiene el análisis de un especialista por su doctor_id.

    Parámetros
    ----------
    doctor_id : int
        Identificador único del doctor.

    Retorna
    -------
    dict | None
        Documento de análisis o None si no existe.
    """
    _asegurar_indices()
    coleccion = _obtener_coleccion()
    return coleccion.find_one({"doctor_id": doctor_id})


def analisis_existente_reciente(doctor_id: int, dias: int = 30) -> bool:
    """
    Verifica si existe un análisis completado con menos de N días.

    Parámetros
    ----------
    doctor_id : int
        Identificador único del doctor.
    dias : int
        Número máximo de días de antigüedad del análisis.

    Retorna
    -------
    bool
        True si existe análisis reciente completado.
    """
    _asegurar_indices()
    coleccion = _obtener_coleccion()
    fecha_limite = datetime.now(timezone.utc) - timedelta(days=dias)

    doc = coleccion.find_one({
        "doctor_id": doctor_id,
        "estado": "completado",
        "fecha_analisis": {"$gte": fecha_limite},
    })
    return doc is not None


def listar_pendientes(limite: int = 100) -> list[dict]:
    """
    Retorna doctores que necesitan análisis.

    Criterios:
    - No tienen documento en analisis_especialistas, O
    - Su estado es 'error' o 'pendiente', O
    - Su fecha_analisis tiene más de 30 días.

    Parámetros
    ----------
    limite : int
        Máximo de documentos a retornar.

    Retorna
    -------
    list[dict]
        Lista de documentos de análisis pendientes.
    """
    _asegurar_indices()
    coleccion = _obtener_coleccion()
    fecha_limite = datetime.now(timezone.utc) - timedelta(days=30)

    cursor = coleccion.find({
        "$or": [
            {"estado": {"$in": ["error", "pendiente"]}},
            {"fecha_analisis": {"$lt": fecha_limite}},
        ]
    }).limit(limite)

    return list(cursor)


def marcar_error(doctor_id: int, error: str) -> None:
    """
    Marca un análisis con estado de error.

    Parámetros
    ----------
    doctor_id : int
        Identificador único del doctor.
    error : str
        Descripción del error ocurrido.
    """
    _asegurar_indices()
    coleccion = _obtener_coleccion()

    coleccion.update_one(
        {"doctor_id": doctor_id},
        {"$set": {
            "estado": "error",
            "error_detalle": error,
            "fecha_analisis": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
