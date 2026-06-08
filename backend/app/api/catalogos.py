"""
Router de catálogos para autocompletado de especialidades, ciudades y pares.

Todos los endpoints son públicos (sin autenticación).
Los datos provienen de la colección `catalogos` en MongoDB.
"""

from __future__ import annotations

import math
import re
from typing import Optional

from fastapi import APIRouter, Query

from app.db.mongo import get_mongo_async_db
from app.models.schemas import (
    CiudadesListResponse,
    EspecialidadesListResponse,
    ParesListResponse,
)

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])

# Mapa de slugs a nombres legibles con acentos correctos
_SLUG_A_NOMBRE: dict[str, str] = {
    "cirujano-general": "Cirujano General",
    "dermatologo": "Dermatólogo",
    "endodoncia": "Endodoncia",
    "ginecologo": "Ginecólogo",
    "implantologo": "Implantólogo",
    "internista": "Internista",
    "nutriologo": "Nutriólogo",
    "oftalmologo": "Oftalmólogo",
    "ortodoncista": "Ortodoncista",
    "ortopedista": "Ortopedista",
    "otorrinolaringologo": "Otorrinolaringólogo",
    "pediatra": "Pediatra",
    "periodoncia": "Periodoncia",
    "psicologo": "Psicólogo",
    "psiquiatra": "Psiquiatra",
    "traumatologo": "Traumatólogo",
    "urologo": "Urólogo",
    "dentista": "Dentista",
    "cardiologo": "Cardiólogo",
    "endocrinologo": "Endocrinólogo",
    "gastroenterologo": "Gastroenterólogo",
    "neurologo": "Neurólogo",
    "oncologo": "Oncólogo",
    "reumatologo": "Reumatólogo",
    "psicoterapeuta": "Psicoterapeuta",
    "ciudad-de-mexico": "Ciudad de México",
    "guadalajara": "Guadalajara",
    "monterrey": "Monterrey",
    "oaxaca-de-juarez": "Oaxaca de Juárez",
    "puebla": "Puebla",
    "tijuana": "Tijuana",
    "merida": "Mérida",
    "leon": "León",
    "queretaro": "Querétaro",
}


def _slug_a_nombre(slug: str) -> str:
    """
    Convierte un slug a nombre legible con capitalización y acentos correctos.

    Parámetros
    ----------
    slug : str
        Slug en formato 'endodoncia' o 'ciudad-de-mexico'.

    Retorna
    -------
    str
        Nombre legible desde el mapa, o título capitalizado si no está en el mapa.

    Ejemplo
    -------
    >>> _slug_a_nombre("ginecologo")
    'Ginecólogo'
    >>> _slug_a_nombre("ciudad-de-mexico")
    'Ciudad de México'
    """
    return _SLUG_A_NOMBRE.get(slug, slug.replace("-", " ").title())


async def _obtener_coleccion():
    """Retorna la colección `catalogos` de MongoDB."""
    db = get_mongo_async_db()
    return db["catalogos"]


def _filtro_con_busqueda(campo: str, q: Optional[str]) -> dict:
    """
    Construye el filtro MongoDB para un campo con búsqueda parcial opcional.

    Parámetros
    ----------
    campo : str
        Nombre del campo en MongoDB.
    q : str o None
        Texto de búsqueda parcial case-insensitive. Si es None, no aplica regex.

    Retorna
    -------
    dict
        Filtro MongoDB listo para usar en `find()` o `aggregate()`.
    """
    if q:
        return {campo: {"$regex": re.escape(q.lower()), "$options": "i"}}
    return {}


@router.get("/especialidades", response_model=EspecialidadesListResponse)
async def listar_especialidades(
    q: Optional[str] = Query(None, description="Búsqueda parcial por nombre o slug"),
    limit: int = Query(200, ge=1, le=500),
):
    """
    Lista especialidades médicas disponibles para autocompletado.

    Agrupa los documentos del catálogo por `especialidad_slug` y devuelve
    el nombre legible de cada especialidad con el total de ciudades disponibles.

    Parámetros
    ----------
    q : str, opcional
        Filtro de búsqueda parcial sobre el slug (case-insensitive).
    limit : int
        Máximo de especialidades únicas a devolver. Por defecto 200.

    Retorna
    -------
    EspecialidadesListResponse
        Total real y lista de especialidades con nombre, slug y total de pares.
    """
    col = await _obtener_coleccion()
    filtro = _filtro_con_busqueda("especialidad_slug", q)

    pipeline_conteo = [
        {"$match": filtro},
        {"$group": {"_id": "$especialidad_slug"}},
        {"$count": "total"},
    ]
    pipeline_datos = [
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

    total_real = 0
    async for doc in col.aggregate(pipeline_conteo):
        total_real = doc.get("total", 0)

    especialidades = []
    async for doc in col.aggregate(pipeline_datos):
        slug = doc["_id"] or ""
        if not slug:
            continue
        nombre = doc.get("especialidad_nombre") or _slug_a_nombre(slug)
        especialidades.append(
            {
                "nombre": nombre,
                "slug": slug,
                "total_pares": doc.get("total_pares", 0),
            }
        )

    return {"total": total_real, "especialidades": especialidades}


@router.get("/ciudades", response_model=CiudadesListResponse)
async def listar_ciudades(
    q: Optional[str] = Query(None, description="Búsqueda parcial por slug de ciudad"),
    especialidad: Optional[str] = Query(
        None, description="Filtrar por especialidad disponible"
    ),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Lista ciudades disponibles para autocompletado, opcionalmente filtradas por especialidad.

    Parámetros
    ----------
    q : str, opcional
        Búsqueda parcial sobre el slug de ciudad (case-insensitive).
    especialidad : str, opcional
        Slug de especialidad para filtrar solo ciudades con esa especialidad disponible.
    limit : int
        Máximo de ciudades únicas a devolver. Por defecto 100.

    Retorna
    -------
    CiudadesListResponse
        Total real de ciudades únicas y lista con nombre, slug y total de pares.
    """
    col = await _obtener_coleccion()

    filtro = _filtro_con_busqueda("ciudad_slug", q)
    if especialidad:
        filtro["especialidad_slug"] = {
            "$regex": re.escape(especialidad.lower()),
            "$options": "i",
        }

    pipeline_conteo = [
        {"$match": filtro},
        {"$group": {"_id": "$ciudad_slug"}},
        {"$count": "total"},
    ]
    pipeline_datos = [
        {"$match": filtro},
        {
            "$group": {
                "_id": "$ciudad_slug",
                "total_pares": {"$sum": 1},
            }
        },
        {"$sort": {"total_pares": -1, "_id": 1}},
        {"$limit": limit},
    ]

    total_real = 0
    async for doc in col.aggregate(pipeline_conteo):
        total_real = doc.get("total", 0)

    ciudades = []
    async for doc in col.aggregate(pipeline_datos):
        slug = doc["_id"] or ""
        if not slug:
            continue
        ciudades.append(
            {
                "nombre": _slug_a_nombre(slug),
                "slug": slug,
                "estado": None,
                "total_pares": doc.get("total_pares", 0),
            }
        )

    return {"total": total_real, "ciudades": ciudades}


@router.get("/pares", response_model=ParesListResponse)
async def listar_pares(
    especialidad: Optional[str] = Query(None, description="Slug de especialidad"),
    ciudad: Optional[str] = Query(None, description="Slug de ciudad"),
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

    pares = []
    async for doc in col.find(filtro).skip(skip).limit(limit):
        esp_slug = doc.get("especialidad_slug", "")
        ciu_slug = doc.get("ciudad_slug", "")
        pares.append(
            {
                "especialidad_nombre": doc.get("especialidad_nombre")
                or _slug_a_nombre(esp_slug),
                "especialidad_slug": esp_slug,
                "ciudad_nombre": _slug_a_nombre(ciu_slug),
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
