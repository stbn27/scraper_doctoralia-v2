"""
Router de catálogos para autocompletado de especialidades, ciudades, estados y pares.

Todos los endpoints son públicos (sin autenticación).
Los datos provienen de la BD Doctoralia (27017):
- ``specializations``              → especialidades
- ``cities``                       → ciudades
- ``provinces``                    → estados/provincias
- ``specialization_city_links``    → pares especialidad-ciudad

Endpoints
---------
- GET /catalogos/especialidades     → lista de especialidades
- GET /catalogos/ciudades           → lista de ciudades
- GET /catalogos/ubicaciones        → ciudades + estados para autocompletado mixto
- GET /catalogos/pares              → pares especialidad-ciudad con URL de búsqueda
"""

from __future__ import annotations

import math
import re
from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Query

from app.db.mongo import get_doctoralia_async_db
from app.models.schemas import (
    CiudadesListResponse,
    EspecialidadesListResponse,
    ParesListResponse,
)

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


# =============================================================================
# Helpers
# =============================================================================


def _filtro_busqueda_texto(campo: str, q: Optional[str]) -> dict:
    """
    Construye filtro MongoDB de búsqueda parcial case-insensitive sobre un campo.

    Parámetros
    ----------
    campo : str
        Nombre del campo en la colección.
    q : str o None
        Texto de búsqueda. Si es None o vacío, retorna filtro vacío.

    Retorna
    -------
    dict
        Filtro MongoDB ``{campo: {$regex: ..., $options: 'i'}}``.

    Ejemplo
    -------
    >>> _filtro_busqueda_texto("displayName", "azca")
    {'displayName': {'$regex': 'azca', '$options': 'i'}}
    """
    if q and q.strip():
        return {campo: {"$regex": re.escape(q.strip()), "$options": "i"}}
    return {}


async def _obtener_db():
    """Retorna la base de datos Doctoralia asíncrona."""
    return get_doctoralia_async_db()


# =============================================================================
# GET /catalogos/especialidades
# =============================================================================


@router.get("/especialidades", response_model=EspecialidadesListResponse)
async def listar_especialidades(
    q: Optional[str] = Query(None, description="Búsqueda parcial por nombre o slug"),
    limit: int = Query(300, ge=1, le=500),
):
    """
    Lista especialidades médicas disponibles para autocompletado.

    Lee de la colección ``specializations`` de la BD Doctoralia.
    Cada documento tiene: id, name, urlname, seoUrl, searchUrlTemplate.

    Parámetros
    ----------
    q : str, opcional
        Filtro de búsqueda parcial sobre el nombre (case-insensitive).
    limit : int
        Máximo de especialidades a devolver. Por defecto 300.

    Retorna
    -------
    EspecialidadesListResponse
        Total y lista de especialidades con ``nombre``, ``slug`` y ``total_pares``.

    Ejemplo
    -------
    GET /catalogos/especialidades?q=cardio
    → [{"nombre": "Cardiólogo", "slug": "cardiologo", "total_pares": 0}]
    """
    db = await _obtener_db()
    col = db["specializations"]

    filtro = _filtro_busqueda_texto("name", q)

    total = await col.count_documents(filtro)

    especialidades = []
    async for doc in col.find(filtro).sort("name", 1).limit(limit):
        especialidades.append(
            {
                "nombre": doc.get("name", ""),
                "slug": doc.get("urlname", ""),
                "total_pares": 0,
            }
        )

    return {"total": total, "especialidades": especialidades}


# =============================================================================
# GET /catalogos/ciudades
# =============================================================================


@router.get("/ciudades", response_model=CiudadesListResponse)
async def listar_ciudades(
    q: Optional[str] = Query(None, description="Búsqueda parcial por nombre de ciudad"),
    especialidad: Optional[str] = Query(
        None, description="Filtrar ciudades que tienen esa especialidad disponible"
    ),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Lista ciudades disponibles para autocompletado.

    Lee de la colección ``cities`` de la BD Doctoralia.
    Si se proporciona ``especialidad``, filtra usando ``specialization_city_links``.

    Parámetros
    ----------
    q : str, opcional
        Búsqueda parcial sobre ``displayName`` (case-insensitive).
    especialidad : str, opcional
        Slug de especialidad para filtrar solo ciudades donde hay esa especialidad.
    limit : int
        Máximo de ciudades. Por defecto 100.

    Retorna
    -------
    CiudadesListResponse
        Total y lista con ``nombre``, ``slug``, ``estado``, ``total_pares``.
    """
    db = await _obtener_db()
    col_cities = db["cities"]

    # Si se filtra por especialidad, obtener slugs de ciudades válidas primero
    slugs_validos: Optional[set] = None
    if especialidad:
        col_links = db["specialization_city_links"]
        filtro_esp = {
            "specialtySlug": {
                "$regex": re.escape(especialidad.strip()),
                "$options": "i",
            }
        }
        cursor_links = col_links.find(filtro_esp, {"citySlug": 1})
        slugs_validos = set()
        async for lnk in cursor_links:
            if lnk.get("citySlug"):
                slugs_validos.add(lnk["citySlug"])

    # Construir filtro principal
    filtro: dict = _filtro_busqueda_texto("displayName", q)
    if slugs_validos is not None:
        filtro["slug"] = {"$in": list(slugs_validos)}

    total = await col_cities.count_documents(filtro)

    ciudades = []
    async for doc in col_cities.find(filtro).sort("displayName", 1).limit(limit):
        ciudades.append(
            {
                "nombre": doc.get("displayName", ""),
                "slug": doc.get("slug", ""),
                "estado": None,
                "total_pares": 0,
            }
        )

    return {"total": total, "ciudades": ciudades}


# =============================================================================
# GET /catalogos/ubicaciones  (NUEVO — para autocompletado mixto)
# =============================================================================


@router.get("/ubicaciones")
async def buscar_ubicaciones(
    q: Optional[str] = Query(None, description="Texto libre: ciudad, alcaldía, estado"),
    limit: int = Query(15, ge=1, le=50),
):
    """
    Busca ubicaciones para autocompletado mixto: ciudades y estados.

    Prioriza resultados de la colección ``cities``. Si hay menos de ``limit`` resultados,
    complementa con ``provinces`` para cubrir búsquedas por estado.

    Parámetros
    ----------
    q : str, opcional
        Texto libre de búsqueda (ciudad, alcaldía, estado). Mínimo 2 caracteres.
    limit : int
        Máximo de sugerencias totales. Por defecto 15.

    Retorna
    -------
    dict
        ``{"total": int, "ubicaciones": [{nombre, slug, tipo, searchLoc}]}``.
        ``tipo`` puede ser ``'ciudad'`` o ``'estado'``.

    Ejemplo
    -------
    GET /catalogos/ubicaciones?q=azca
    → {"ubicaciones": [{"nombre": "Azcapotzalco", "slug": "azcapotzalco", "tipo": "ciudad"}]}
    """
    if not q or len(q.strip()) < 2:
        return {"total": 0, "ubicaciones": []}

    db = await _obtener_db()
    filtro = _filtro_busqueda_texto("displayName", q)

    ubicaciones: list[dict] = []

    # 1. Buscar en cities primero
    col_cities = db["cities"]
    async for doc in col_cities.find(filtro).sort("displayName", 1).limit(limit):
        ubicaciones.append(
            {
                "nombre": doc.get("displayName", ""),
                "slug": doc.get("slug", ""),
                "tipo": "ciudad",
                "searchLoc": doc.get("searchLoc", doc.get("displayName", "")),
            }
        )

    # 2. Complementar con provinces si hay espacio
    restante = limit - len(ubicaciones)
    if restante > 0:
        col_prov = db["provinces"]
        slugs_ya = {u["slug"] for u in ubicaciones}
        async for doc in col_prov.find(filtro).sort("displayName", 1).limit(restante * 2):
            slug = doc.get("slug", "")
            if slug not in slugs_ya:
                ubicaciones.append(
                    {
                        "nombre": doc.get("displayName", ""),
                        "slug": slug,
                        "tipo": "estado",
                        "searchLoc": doc.get("searchLoc", doc.get("displayName", "")),
                    }
                )
                slugs_ya.add(slug)
            if len(ubicaciones) >= limit:
                break

    return {"total": len(ubicaciones), "ubicaciones": ubicaciones}


# =============================================================================
# GET /catalogos/pares
# =============================================================================


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

    Lee de la colección ``specialization_city_links`` de la BD Doctoralia.

    Parámetros
    ----------
    especialidad : str, opcional
        Slug de especialidad para filtrar.
    ciudad : str, opcional
        Slug de ciudad para filtrar.
    modalidad : str, opcional
        No aplicable en la nueva BD (se ignora, mantenido por compatibilidad).
    page : int
        Página actual. Por defecto 1.
    limit : int
        Pares por página. Por defecto 50.

    Retorna
    -------
    ParesListResponse
        Paginación completa y lista de pares con URL canónica de búsqueda.
    """
    db = await _obtener_db()
    col = db["specialization_city_links"]

    filtro: dict = {}
    if especialidad:
        filtro["specialtySlug"] = {
            "$regex": re.escape(especialidad.strip()),
            "$options": "i",
        }
    if ciudad:
        filtro["citySlug"] = {
            "$regex": re.escape(ciudad.strip()),
            "$options": "i",
        }

    total = await col.count_documents(filtro)
    pages = math.ceil(total / limit) if limit and total else 0
    skip = (page - 1) * limit

    pares = []
    async for doc in col.find(filtro).skip(skip).limit(limit):
        pares.append(
            {
                "especialidad_nombre": doc.get("specialtyName", ""),
                "especialidad_slug": doc.get("specialtySlug", ""),
                "ciudad_nombre": doc.get("citySlug", "").replace("-", " ").title(),
                "ciudad_slug": doc.get("citySlug", ""),
                "modalidad": None,
                "url": doc.get("canonicalUrl") or doc.get("searchUrl"),
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
