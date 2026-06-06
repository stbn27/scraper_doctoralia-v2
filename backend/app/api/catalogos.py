"""
Router de catálogos para autocompletado de especialidades, ciudades y pares.

Todos los endpoints son públicos (sin autenticación).
Los datos provienen de la colección `catalogos` en MongoDB.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Optional

from fastapi import APIRouter, Query

from app.db.mongo import get_mongo_async_db
from app.models.schemas import (
    CiudadesListResponse,
    EspecialidadesListResponse,
    ParesListResponse,
)

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


def _slug_a_nombre(slug: str) -> str:
    """
    Convierte un slug a nombre legible con capitalización.

    Parámetros
    ----------
    slug : str
        Slug en formato 'endodoncia' o 'ciudad-de-mexico'.

    Retorna
    -------
    str
        Nombre legible: 'Endodoncia', 'Ciudad De México'.

    Ejemplo
    -------
    >>> _slug_a_nombre("ginecologo")
    'Ginecólogo'
    """
    # Mapa de slugs con acentos especiales
    _MAPA = {
        "ginecologo": "Ginecólogo",
        "psicologo": "Psicólogo",
        "oftalmologo": "Oftalmólogo",
        "otorrinolaringologo": "Otorrinolaringólogo",
        "cardiologo": "Cardiólogo",
        "dermatologo": "Dermatólogo",
        "ortopedista": "Ortopedista",
        "pediatra": "Pediatra",
        "endodoncia": "Endodoncia",
        "dentista": "Dentista",
        "psicoterapeuta": "Psicoterapeuta",
        "nutriologo": "Nutriólogo",
        "endocrinologo": "Endocrinólogo",
        "gastroenterologo": "Gastroenterólogo",
        "urologo": "Urólogo",
        "neurologo": "Neurólogo",
        "hematólogo": "Hematólogo",
        "reumatologo": "Reumatólogo",
        "nefrologo": "Nefrólogo",
        "oncologo": "Oncólogo",
        "infectologo": "Infectólogo",
        "inmunólogo": "Inmunólogo",
        "proctólogo": "Proctólogo",
        "neumólogo": "Neumólogo",
        "psiquiatra": "Psiquiatra",
        "ciudad-de-mexico": "Ciudad de México",
        "guadalajara": "Guadalajara",
        "monterrey": "Monterrey",
        "puebla": "Puebla",
        "tijuana": "Tijuana",
        "merida": "Mérida",
    }
    if slug in _MAPA:
        return _MAPA[slug]
    return slug.replace("-", " ").title()


def _limpiar_nombre_ciudad(nombre_raw: Optional[str], ciudad_slug: str) -> str:
    """
    Limpia el nombre de ciudad eliminando el sufijo de especialidad que Doctoralia adjunta.

    En Doctoralia el campo `ciudad_nombre` suele venir como 'Ciudad de México Endodoncia'.
    Se usa el slug como fuente primaria limpia.

    Parámetros
    ----------
    nombre_raw : str o None
        Nombre tal cual viene de la base de datos (puede tener especialidad adjunta).
    ciudad_slug : str
        Slug de la ciudad, usado como fuente limpia alternativa.

    Retorna
    -------
    str
        Nombre limpio de la ciudad.
    """
    return _slug_a_nombre(ciudad_slug)


async def _obtener_coleccion():
    """Retorna la colección de catálogos de MongoDB."""
    db = get_mongo_async_db()
    return db["catalogos"]


@router.get("/especialidades", response_model=EspecialidadesListResponse)
async def listar_especialidades(
    q: Optional[str] = Query(None, description="Búsqueda parcial por nombre o slug"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Lista especialidades disponibles para autocompletado.

    Agrupa los documentos del catálogo por `especialidad_slug` y devuelve
    el nombre legible de cada especialidad con el total de pares ciudad disponibles.

    Parámetros
    ----------
    q : str, opcional
        Filtro de búsqueda parcial sobre el slug de especialidad.
    limit : int
        Máximo de especialidades a devolver. Por defecto 20.

    Retorna
    -------
    EspecialidadesListResponse
        Total y lista de especialidades con nombre, slug y total de pares.
    """
    col = await _obtener_coleccion()

    filtro: dict = {}
    if q:
        filtro["especialidad_slug"] = {"$regex": re.escape(q.lower()), "$options": "i"}

    pipeline = [
        {"$match": filtro},
        {
            "$group": {
                "_id": "$especialidad_slug",
                "total_pares": {"$sum": 1},
                "especialidad_nombre": {"$first": "$especialidad_nombre"},
            }
        },
        {"$sort": {"_id": 1}},
        {"$limit": limit},
    ]

    cursor = col.aggregate(pipeline)
    especialidades = []
    async for doc in cursor:
        slug = doc["_id"] or ""
        nombre = doc.get("especialidad_nombre") or _slug_a_nombre(slug)
        especialidades.append(
            {
                "nombre": nombre,
                "slug": slug,
                "total_pares": doc.get("total_pares", 0),
            }
        )

    return {"total": len(especialidades), "especialidades": especialidades}


@router.get("/ciudades", response_model=CiudadesListResponse)
async def listar_ciudades(
    q: Optional[str] = Query(None, description="Búsqueda parcial por slug de ciudad"),
    especialidad: Optional[str] = Query(
        None, description="Filtrar ciudades por especialidad"
    ),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Lista ciudades disponibles para autocompletado, opcionalmente filtradas por especialidad.

    Parámetros
    ----------
    q : str, opcional
        Búsqueda parcial sobre el slug de ciudad.
    especialidad : str, opcional
        Slug de especialidad para filtrar solo ciudades con esa especialidad disponible.
    limit : int
        Máximo de ciudades a devolver. Por defecto 20.

    Retorna
    -------
    CiudadesListResponse
        Total y lista de ciudades con nombre, slug y total de pares.
    """
    col = await _obtener_coleccion()

    filtro: dict = {}
    if q:
        filtro["ciudad_slug"] = {"$regex": re.escape(q.lower()), "$options": "i"}
    if especialidad:
        filtro["especialidad_slug"] = {
            "$regex": re.escape(especialidad.lower()),
            "$options": "i",
        }

    pipeline = [
        {"$match": filtro},
        {
            "$group": {
                "_id": "$ciudad_slug",
                "total_pares": {"$sum": 1},
                "ciudad_nombre": {"$first": "$ciudad_nombre"},
            }
        },
        {"$sort": {"total_pares": -1, "_id": 1}},
        {"$limit": limit},
    ]

    cursor = col.aggregate(pipeline)
    ciudades = []
    async for doc in cursor:
        slug = doc["_id"] or ""
        nombre = _limpiar_nombre_ciudad(doc.get("ciudad_nombre"), slug)
        ciudades.append(
            {
                "nombre": nombre,
                "slug": slug,
                "estado": None,
                "total_pares": doc.get("total_pares", 0),
            }
        )

    return {"total": len(ciudades), "ciudades": ciudades}


@router.get("/pares", response_model=ParesListResponse)
async def listar_pares(
    especialidad: Optional[str] = Query(None),
    ciudad: Optional[str] = Query(None),
    modalidad: Optional[str] = Query(None, description="presencial | online"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Lista pares especialidad-ciudad disponibles con paginación.

    Parámetros
    ----------
    especialidad : str, opcional
        Slug de especialidad para filtrar.
    ciudad : str, opcional
        Slug de ciudad para filtrar.
    modalidad : str, opcional
        'presencial' o 'online'.
    page : int
        Página actual. Por defecto 1.
    limit : int
        Pares por página. Por defecto 50.

    Retorna
    -------
    ParesListResponse
        Paginación completa y lista de pares especialidad-ciudad.
    """
    col = await _obtener_coleccion()

    filtro: dict = {}
    if especialidad:
        filtro["especialidad_slug"] = {
            "$regex": re.escape(especialidad.lower()),
            "$options": "i",
        }
    if ciudad:
        filtro["ciudad_slug"] = {"$regex": re.escape(ciudad.lower()), "$options": "i"}
    if modalidad:
        filtro["modalidad"] = modalidad

    total = await col.count_documents(filtro)
    pages = math.ceil(total / limit) if limit and total else 0
    skip = (page - 1) * limit

    cursor = col.find(filtro).skip(skip).limit(limit)

    pares = []
    async for doc in cursor:
        esp_slug = doc.get("especialidad_slug", "")
        ciu_slug = doc.get("ciudad_slug", "")
        pares.append(
            {
                "especialidad_nombre": doc.get("especialidad_nombre")
                or _slug_a_nombre(esp_slug),
                "especialidad_slug": esp_slug,
                "ciudad_nombre": _limpiar_nombre_ciudad(
                    doc.get("ciudad_nombre"), ciu_slug
                ),
                "ciudad_slug": ciu_slug,
                "modalidad": doc.get("modalidad"),
                "url": doc.get("url"),
            }
        )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
        "pares": pares,
    }
