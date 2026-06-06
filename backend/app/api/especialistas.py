"""
Router de especialistas v2.

Mantiene compatibilidad con endpoints existentes y agrega:
- GET /especialistas          → Búsqueda avanzada con filtros y paginación
- GET /especialistas/{id}     → Detalle con análisis IA completo
- GET /especialistas/doctoralia/{id} → Por doctoralia_id
- GET /especialistas/{id}/opiniones  → Opiniones paginadas y filtrables
- (Conservados) /buscar, /catalogo/*, DELETE
"""

from __future__ import annotations

import math
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo import get_mongo_async_db
from app.db.repositorios import analisis_repo, especialistas_repo
from app.models.especialista import EspecialistaResponse
from app.models.opinion import OpinionesResponse
from app.models.schemas import EspecialistaDetailResponse, OpinionesPaginadasResponse
from app.services.busqueda_service import buscar_especialistas_paginado
from app.services.especialistas_service import (
    actualizar_catalogo_desde_web,
    buscar_o_scrapear_especialistas,
    cargar_catalogo_desde_fixture,
)
from app.services.opiniones_service import obtener_o_scrapear_opiniones
from pydantic import BaseModel

router = APIRouter(prefix="/especialistas", tags=["Especialistas"])


class CatalogoCargaRequest(BaseModel):
    """Payload para cargar el catálogo desde fixtures."""

    especialidad: str
    ciudad: str


def _serializar_doc(doc: dict) -> dict:
    """
    Convierte el campo `_id` de un documento MongoDB a string.

    Parámetros
    ----------
    doc : dict
        Documento MongoDB con posible campo `_id` de tipo ObjectId.

    Retorna
    -------
    dict
        Documento con `_id` convertido a string.
    """
    if "_id" in doc and doc["_id"] is not None:
        doc["_id"] = str(doc["_id"])
    return doc


def _extraer_analisis_detalle(analisis_doc: Optional[dict]) -> dict:
    """
    Extrae el análisis IA completo para la vista de detalle del especialista.

    Parámetros
    ----------
    analisis_doc : dict o None
        Documento completo de `analisis_especialistas`.

    Retorna
    -------
    dict
        Análisis completo incluyendo puntos fuertes, débiles y justificación.
    """
    if not analisis_doc:
        return {"tiene_analisis": False}

    resultado_ia = analisis_doc.get("resultado_ia") or {}
    metricas = analisis_doc.get("metricas_locales") or {}

    return {
        "tiene_analisis": True,
        "estado": analisis_doc.get("estado"),
        "modelo_usado": analisis_doc.get("modelo_usado"),
        "version_prompt": analisis_doc.get("version_prompt"),
        "fecha_analisis": str(analisis_doc.get("fecha_analisis", "")),
        "puntuacion_recomendacion": resultado_ia.get("puntuacion_recomendacion"),
        "resumen": resultado_ia.get("resumen"),
        "puntos_fuertes": resultado_ia.get("puntos_fuertes") or [],
        "puntos_debiles": resultado_ia.get("puntos_debiles") or [],
        "confiabilidad_opiniones": resultado_ia.get("confiabilidad_opiniones"),
        "justificacion_puntuacion": resultado_ia.get("justificacion_puntuacion"),
        "metricas_locales": {
            "total_opiniones_bd": metricas.get("total_opiniones_bd"),
            "opiniones_enviadas_al_modelo": metricas.get(
                "opiniones_enviadas_al_modelo"
            ),
            "porcentaje_verificadas": metricas.get("porcentaje_verificadas"),
            "recencia_promedio_dias": metricas.get("recencia_promedio_dias"),
            "longitud_promedio_palabras": metricas.get("longitud_promedio_palabras"),
            "porcentaje_texto_corto": metricas.get("porcentaje_texto_corto"),
            "porcentaje_ultimos_6_meses": metricas.get("porcentaje_ultimos_6_meses"),
            "rating_promedio": metricas.get("rating_promedio"),
            "sospecha_fraude": metricas.get("sospecha_fraude"),
            "razones_fraude": metricas.get("razones_fraude") or [],
        },
    }


# =============================================================================
# ENDPOINT PRINCIPAL — GET /especialistas (búsqueda avanzada con filtros)
# =============================================================================


@router.get("/", response_model=dict)
async def buscar_especialistas_v2(
    especialidad: Optional[str] = Query(None),
    especialidad_slug: Optional[str] = Query(None),
    ciudad: Optional[str] = Query(None),
    ciudad_slug: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Búsqueda textual por nombre"),
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=50),
    orden: Optional[str] = Query(
        "opiniones_desc",
        description="puntuacion_desc|puntuacion_asc|opiniones_desc|opiniones_asc|rating_desc|rating_asc|nombre_asc|nombre_desc|recencia_analisis_desc",
    ),
    solo_con_opiniones: bool = Query(False),
    min_opiniones: Optional[int] = Query(None),
    max_opiniones: Optional[int] = Query(None),
    solo_analizados: bool = Query(False),
    estado_analisis: Optional[str] = Query(None),
    confiabilidad: Optional[str] = Query(None),
    sospecha_fraude: Optional[bool] = Query(None),
    atiende_ninos: Optional[bool] = Query(None),
    atiende_adultos: Optional[bool] = Query(None),
    atiende_adolescentes: Optional[bool] = Query(None),
    rating_min: Optional[float] = Query(None),
    rating_max: Optional[float] = Query(None),
    puntuacion_min: Optional[float] = Query(None),
    puntuacion_max: Optional[float] = Query(None),
    solo_con_foto: Optional[bool] = Query(None),
    solo_con_cedula: Optional[bool] = Query(None),
    solo_con_consultorio: Optional[bool] = Query(None),
    solo_con_precio: Optional[bool] = Query(None),
    precio_min: Optional[int] = Query(None),
    precio_max: Optional[int] = Query(None),
    servicio: Optional[str] = Query(None),
    alcaldia_o_municipio: Optional[str] = Query(None),
    codigo_postal: Optional[str] = Query(None),
):
    """
    Búsqueda avanzada de especialistas con filtros múltiples y paginación.

    No dispara scraping. Consulta exclusivamente datos almacenados en MongoDB.
    Enriquece cada resultado con datos de análisis IA de `analisis_especialistas`.

    Parámetros
    ----------
    especialidad : str, opcional
        Nombre o slug de especialidad para filtrar.
    ciudad : str, opcional
        Nombre o slug de ciudad para filtrar.
    q : str, opcional
        Búsqueda textual por nombre del especialista.
    page : int
        Página actual. Por defecto 1.
    limit : int
        Resultados por página. Por defecto 12, máximo 50.
    orden : str
        Criterio de ordenamiento. Por defecto 'opiniones_desc'.
    solo_analizados : bool
        Si True, devuelve solo especialistas con análisis IA.
    ... (ver query params completos en la documentación)

    Retorna
    -------
    dict
        Respuesta paginada con total, filtros aplicados y lista de especialistas.
    """
    params = {
        "especialidad": especialidad or especialidad_slug,
        "ciudad": ciudad or ciudad_slug,
        "q": q,
        "orden": orden,
        "solo_con_opiniones": solo_con_opiniones,
        "min_opiniones": min_opiniones,
        "max_opiniones": max_opiniones,
        "solo_analizados": solo_analizados,
        "estado_analisis": estado_analisis,
        "confiabilidad": confiabilidad,
        "sospecha_fraude": sospecha_fraude,
        "atiende_ninos": atiende_ninos,
        "atiende_adultos": atiende_adultos,
        "atiende_adolescentes": atiende_adolescentes,
        "rating_min": rating_min,
        "rating_max": rating_max,
        "puntuacion_min": puntuacion_min,
        "puntuacion_max": puntuacion_max,
        "solo_con_foto": solo_con_foto,
        "solo_con_cedula": solo_con_cedula,
        "solo_con_consultorio": solo_con_consultorio,
        "solo_con_precio": solo_con_precio,
        "precio_min": precio_min,
        "precio_max": precio_max,
        "servicio": servicio,
        "alcaldia_o_municipio": alcaldia_o_municipio,
        "codigo_postal": codigo_postal,
    }

    return await buscar_especialistas_paginado(params=params, page=page, limit=limit)


# =============================================================================
# DETALLE DE ESPECIALISTA — GET /especialistas/{id}
# =============================================================================


@router.get("/doctoralia/{doctoralia_id}", response_model=dict)
async def obtener_especialista_por_doctoralia_id(doctoralia_id: int):
    """
    Obtiene el detalle completo de un especialista por su ID de Doctoralia.

    Parámetros
    ----------
    doctoralia_id : int
        ID numérico del especialista en Doctoralia.

    Retorna
    -------
    dict
        Detalle completo del especialista con análisis IA.

    Excepciones
    -----------
    HTTPException 404
        Si no se encuentra el especialista.
    """
    doc = await especialistas_repo.buscar_por_doctoralia_id(doctoralia_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    doc = _serializar_doc(doc)
    analisis_doc = await analisis_repo.obtener_por_doctoralia_id(doctoralia_id)
    doc["analisis"] = _extraer_analisis_detalle(analisis_doc)
    return doc


@router.get("/{especialista_id}/opiniones", response_model=dict)
async def obtener_opiniones_paginadas(
    especialista_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    orden: str = Query(
        "reciente", description="reciente|antigua|rating_desc|rating_asc"
    ),
    rating_min: Optional[float] = Query(None),
    rating_max: Optional[float] = Query(None),
    solo_verificadas: Optional[bool] = Query(None),
    servicio: Optional[str] = Query(None),
):
    """
    Obtiene las opiniones paginadas y filtrables de un especialista.

    Parámetros
    ----------
    especialista_id : str
        ObjectId de MongoDB del especialista.
    page : int
        Página actual. Por defecto 1.
    limit : int
        Opiniones por página. Por defecto 20, máximo 100.
    orden : str
        Criterio de orden: 'reciente', 'antigua', 'rating_desc', 'rating_asc'.
    rating_min : float, opcional
        Rating mínimo para filtrar opiniones.
    rating_max : float, opcional
        Rating máximo para filtrar opiniones.
    solo_verificadas : bool, opcional
        Si True, devuelve solo opiniones con verificación.
    servicio : str, opcional
        Filtrar por servicio consultado (búsqueda parcial).

    Retorna
    -------
    dict
        Respuesta paginada con datos del especialista y lista de opiniones.

    Excepciones
    -----------
    HTTPException 404
        Si no se encuentra el especialista.
    """
    especialista = await especialistas_repo.buscar_por_id(especialista_id)
    if not especialista:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    doctor_id = especialista.get("doctoralia_id")
    if not doctor_id:
        raise HTTPException(
            status_code=422, detail="El especialista no tiene doctoralia_id asociado"
        )

    db = get_mongo_async_db()
    col = db["opiniones"]

    # Filtro de opiniones
    filtro: dict[str, Any] = {"doctor_id": doctor_id}
    if rating_min is not None:
        filtro.setdefault("rating", {})["$gte"] = rating_min
    if rating_max is not None:
        filtro.setdefault("rating", {})["$lte"] = rating_max
    if solo_verificadas:
        filtro["tipo_verificacion"] = {"$regex": "verific", "$options": "i"}
    if servicio:
        filtro["servicio_consultado"] = {"$regex": servicio, "$options": "i"}

    # Ordenamiento
    _sort_opiniones = {
        "reciente": [("fecha_publicacion", -1)],
        "antigua": [("fecha_publicacion", 1)],
        "rating_desc": [("rating", -1)],
        "rating_asc": [("rating", 1)],
    }
    sort = _sort_opiniones.get(orden, [("fecha_publicacion", -1)])

    total = await col.count_documents(filtro)
    pages = math.ceil(total / limit) if limit and total else 0
    skip = (page - 1) * limit

    cursor = col.find(filtro).sort(sort).skip(skip).limit(limit)

    opiniones = []
    async for op in cursor:
        op["_id"] = str(op["_id"])
        tipo_ver = op.get("tipo_verificacion") or ""
        op["es_verificada"] = "verific" in tipo_ver.lower()
        opiniones.append(op)

    esp_info = {
        "_id": str(especialista.get("_id", "")),
        "doctoralia_id": doctor_id,
        "nombre": especialista.get("nombre", ""),
        "especialidad": especialista.get("especialidad"),
        "ciudad": especialista.get("ciudad"),
        "rating_global": especialista.get("rating_global"),
        "total_opiniones": especialista.get("total_opiniones"),
    }

    return {
        "especialista": esp_info,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "orden": orden,
        "results": opiniones,
    }


@router.get("/{especialista_id}", response_model=dict)
async def obtener_especialista_detalle(especialista_id: str):
    """
    Obtiene el detalle completo de un especialista por ObjectId de MongoDB.

    Parámetros
    ----------
    especialista_id : str
        ObjectId de MongoDB del especialista.

    Retorna
    -------
    dict
        Detalle completo con todos los campos y análisis IA completo.

    Excepciones
    -----------
    HTTPException 404
        Si no se encuentra el especialista.
    """
    doc = await especialistas_repo.buscar_por_id(especialista_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    doc = _serializar_doc(doc)
    doctoralia_id = doc.get("doctoralia_id")
    analisis_doc = None
    if doctoralia_id:
        analisis_doc = await analisis_repo.obtener_por_doctoralia_id(doctoralia_id)

    doc["analisis"] = _extraer_analisis_detalle(analisis_doc)
    return doc


# =============================================================================
# ENDPOINTS LEGACY — Conservados para compatibilidad
# =============================================================================


@router.get("/buscar", response_model=dict)
async def buscar_especialistas_legacy(
    especialidad: str = Query(...),
    ciudad: str = Query(...),
    limite: int = Query(20, ge=1, le=100),
    forzar_scraping: bool = Query(False),
):
    """
    [LEGACY] Busca especialistas con posibilidad de scraping.

    Conservado para compatibilidad. Para búsqueda sin scraping usar GET /especialistas.

    Parámetros
    ----------
    especialidad : str
        Especialidad a buscar (obligatorio).
    ciudad : str
        Ciudad a buscar (obligatorio).
    limite : int
        Límite de resultados. Por defecto 20.
    forzar_scraping : bool
        Si True, fuerza re-scraping aunque haya datos en Mongo.

    Retorna
    -------
    dict
        Lista de especialistas con metadatos de la búsqueda.
    """
    try:
        resultado = await buscar_o_scrapear_especialistas(
            especialidad=especialidad,
            ciudad=ciudad,
            limite=limite,
            forzar_scraping=forzar_scraping,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    especialistas = [_serializar_doc(doc) for doc in resultado.get("especialistas", [])]
    resultado["especialistas"] = especialistas
    return resultado


@router.delete("/{especialista_id}")
async def eliminar_especialista(especialista_id: str):
    """Elimina un especialista por ObjectId."""
    eliminado = await especialistas_repo.eliminar_especialista(especialista_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")
    return {"eliminado": True}


@router.post("/catalogo/cargar")
async def cargar_catalogo(payload: CatalogoCargaRequest):
    """Carga el catálogo de especialidad y ciudad desde fixtures."""
    try:
        return await cargar_catalogo_desde_fixture(payload.especialidad, payload.ciudad)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/catalogo/actualizar")
async def actualizar_catalogo():
    """Scrapea el catálogo completo y lo persiste en Mongo."""
    return await actualizar_catalogo_desde_web()
