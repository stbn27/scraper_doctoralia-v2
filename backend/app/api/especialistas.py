"""
Router de especialistas v2 — BD Doctoralia.

Consulta las colecciones ``doctor_profiles`` y ``analisis_especialistas`` de la BD Doctoralia (27017).

Endpoints
---------
- GET  /especialistas/              → Búsqueda avanzada con filtros y paginación
- GET  /especialistas/doctoralia/{id} → Detalle por ID de Doctoralia
- GET  /especialistas/{id}          → Detalle por _id de MongoDB
- GET  /especialistas/{id}/opiniones → Opiniones paginadas
- DELETE /especialistas/{id}        → Eliminar (legacy)
"""

from __future__ import annotations

import math
from typing import Any, Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Query

from app.db.mongo import get_doctoralia_async_db
from app.db.repositorios import analisis_repo
from app.services.busqueda_service import (
    buscar_especialistas_paginado,
    _construir_card,
    _serializar_id,
    _extraer_analisis_resumen,
)

# pyrefly: ignore [missing-import]
from pydantic import BaseModel

router = APIRouter(prefix="/especialistas", tags=["Especialistas"])


class CatalogoCargaRequest(BaseModel):
    """Payload para cargar catálogo (legacy)."""

    especialidad: str
    ciudad: str


def _serializar_doc(doc: dict) -> dict:
    """
    Convierte el campo ``_id`` de un documento MongoDB a string.

    Parámetros
    ----------
    doc : dict
        Documento MongoDB con posible campo ``_id`` de tipo ObjectId.

    Retorna
    -------
    dict
        Documento con ``_id`` convertido a string.
    """
    if "_id" in doc and doc["_id"] is not None:
        doc["_id"] = str(doc["_id"])
    return doc


def _extraer_analisis_detalle(analisis_doc: Optional[dict]) -> dict:
    """
    Extrae el análisis IA completo para la vista de detalle del especialista.

    Usa el nuevo esquema de ``analisis_especialistas`` donde:
    - El puntaje está en ``analisis.puntuacion``.
    - Los puntos fuertes/débiles en ``analisis.puntos_fuertes`` y ``analisis.puntos_debiles``.
    - Las métricas en ``metadata_opiniones.*``.

    Parámetros
    ----------
    analisis_doc : dict o None
        Documento completo de ``analisis_especialistas``.

    Retorna
    -------
    dict
        Análisis completo incluyendo puntos fuertes, débiles y justificación.
        Si no hay análisis, retorna ``{"tiene_analisis": False, "mensaje": ...}``.
    """
    if not analisis_doc:
        return {
            "tiene_analisis": False,
            "mensaje": "Este especialista aún no ha sido analizado por la IA.",
        }

    analisis = analisis_doc.get("analisis") or {}
    meta_op = analisis_doc.get("metadata_opiniones") or {}
    meta_ana = analisis_doc.get("metadata_analisis") or {}

    return {
        "tiene_analisis": True,
        "estado": analisis_doc.get("estatus_analisis"),
        "modelo_usado": analisis_doc.get("modelo_usado"),
        "version_prompt": analisis_doc.get("version_prompt"),
        "fecha_analisis": str(meta_ana.get("fecha", "")),
        "puntuacion_recomendacion": analisis.get("puntuacion"),
        "resumen": analisis.get("resumen"),
        "puntos_fuertes": analisis.get("puntos_fuertes") or [],
        "puntos_debiles": analisis.get("puntos_debiles") or [],
        "confiabilidad": analisis.get("confiabilidad"),
        "justificacion": analisis.get("justificacion"),
        "alertas_preprocesamiento": analisis_doc.get("alertas_preprocesamiento"),
        "metricas_opiniones": {
            "total_opiniones_bd": meta_op.get("opiniones_bd"),
            "opiniones_analizadas": meta_ana.get("opiniones_enviadas"),
            "porcentaje_verificadas": meta_op.get("verificadas"),
            "recencia_promedio_dias": meta_op.get("recencia_promedio_dias"),
            "longitud_promedio_palabras": meta_op.get("longitud_promedio_palabras"),
            "porcentaje_texto_corto": meta_op.get("porcentaje_texto_corto"),
            "porcentaje_ultimos_6_meses": meta_op.get("porcentaje_ultimos_6_meses"),
            "rating_promedio": meta_op.get("rating_promedio"),
            "sospecha_fraude": meta_op.get("sospecha_fraude"),
            "razones_fraude": meta_op.get("razones_fraude") or [],
        },
    }


# =============================================================================
# ENDPOINT PRINCIPAL — GET /especialistas (búsqueda avanzada)
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

    Consulta ``doctor_profiles`` en la BD Doctoralia. Los especialistas con análisis
    IA siempre aparecen primero en los resultados, independientemente del orden elegido.

    Parámetros
    ----------
    especialidad : str, opcional
        Nombre o slug de especialidad.
    ciudad : str, opcional
        Ciudad, alcaldía o estado para filtrar.
    q : str, opcional
        Búsqueda textual por nombre del especialista.
    solo_analizados : bool
        Si True, devuelve solo especialistas con análisis IA.
    orden : str
        Criterio de ordenamiento. Por defecto 'opiniones_desc'.

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
# DETALLE POR DOCTORALIA ID
# =============================================================================


@router.get("/doctoralia/{doctoralia_id}", response_model=dict)
async def obtener_especialista_por_doctoralia_id(doctoralia_id: int):
    """
    Obtiene el detalle completo de un especialista por su ID de Doctoralia.

    Busca en ``doctor_profiles`` y enriquece con análisis de ``analisis_especialistas``.

    Parámetros
    ----------
    doctoralia_id : int
        ID numérico del especialista en Doctoralia.

    Retorna
    -------
    dict
        Detalle completo del especialista con análisis IA (o mensaje si no tiene).

    Excepciones
    -----------
    HTTPException 404
        Si no se encuentra el especialista.
    """
    db = get_doctoralia_async_db()
    col = db["doctor_profiles"]

    doc = await col.find_one({"doctor.id_doctoralia": doctoralia_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    doc = _serializar_doc(doc)
    analisis_doc = await analisis_repo.obtener_por_doctoralia_id(doctoralia_id)
    doc["analisis"] = _extraer_analisis_detalle(analisis_doc)
    return doc


# =============================================================================
# OPINIONES PAGINADAS
# =============================================================================


@router.get("/{especialista_id}/opiniones", response_model=dict)
async def obtener_opiniones_paginadas(
    especialista_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    orden: str = Query("reciente", description="reciente|antigua|rating_desc|rating_asc"),
    rating_min: Optional[float] = Query(None),
    rating_max: Optional[float] = Query(None),
    solo_verificadas: Optional[bool] = Query(None),
    servicio: Optional[str] = Query(None),
):
    """
    Obtiene las opiniones paginadas de un especialista.

    Primero resuelve el ``doctoralia_id`` desde ``doctor_profiles`` usando el ``_id`` de Mongo,
    luego consulta ``doctor_opinions`` filtrando por ``doctor_id`` (entero).

    Parámetros
    ----------
    especialista_id : str
        ``_id`` de MongoDB del documento en ``doctor_profiles``.
    page : int
        Página actual. Por defecto 1.
    limit : int
        Opiniones por página. Por defecto 20, máximo 100.
    orden : str
        Criterio: 'reciente', 'antigua', 'rating_desc', 'rating_asc'.
    rating_min : float, opcional
        Rating mínimo.
    rating_max : float, opcional
        Rating máximo.
    solo_verificadas : bool, opcional
        Si True, solo opiniones con cita verificada.
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
    # pyrefly: ignore [missing-import]
    from bson import ObjectId

    db = get_doctoralia_async_db()
    col_profiles = db["doctor_profiles"]
    col_opiniones = db["doctor_opinions"]

    # pyrefly: ignore [missing-import]
    from bson.errors import InvalidId
    
    try:
        oid = ObjectId(especialista_id)
        query = {"_id": {"$in": [oid, especialista_id]}}
    except InvalidId:
        query = {"_id": especialista_id}

    doc_esp = await col_profiles.find_one(query)

    if not doc_esp:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    doctor_id = (doc_esp.get("doctor") or {}).get("id_doctoralia")
    if not doctor_id:
        raise HTTPException(
            status_code=422, detail="El especialista no tiene id_doctoralia asociado"
        )

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

    total = await col_opiniones.count_documents(filtro)
    pages = math.ceil(total / limit) if limit and total else 0
    skip = (page - 1) * limit

    cursor = col_opiniones.find(filtro).sort(sort).skip(skip).limit(limit)

    opiniones = []
    async for op in cursor:
        op["_id"] = str(op["_id"])
        tipo_ver = op.get("tipo_verificacion") or ""
        op["es_verificada"] = "verific" in tipo_ver.lower()
        # Limpiar campos internos de scraping si no se necesitan
        op.pop("scraping_meta", None)
        opiniones.append(op)

    doctor = doc_esp.get("doctor") or {}
    especialidades = doctor.get("especialidades") or []
    direcciones = doctor.get("direcciones") or []
    ciudad = (direcciones[0].get("ciudad") if direcciones else None) or (
        (doctor.get("estado") or [None])[0]
    )

    esp_info = {
        "_id": str(doc_esp.get("_id", "")),
        "doctoralia_id": doctor_id,
        "nombre": doctor.get("nombre", ""),
        "especialidad": especialidades[0] if especialidades else None,
        "ciudad": ciudad,
        "total_opiniones": doc_esp.get("total_opiniones"),
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


# =============================================================================
# DETALLE POR _id DE MONGODB
# =============================================================================


@router.get("/{especialista_id}", response_model=dict)
async def obtener_especialista_detalle(especialista_id: str):
    """
    Obtiene el detalle completo de un especialista por su ``_id`` de MongoDB.

    Busca en ``doctor_profiles`` y enriquece con análisis IA.

    Parámetros
    ----------
    especialista_id : str
        ``_id`` de MongoDB del documento en ``doctor_profiles``.

    Retorna
    -------
    dict
        Detalle completo con análisis IA (o mensaje si no tiene análisis).

    Excepciones
    -----------
    HTTPException 404
        Si no se encuentra el especialista.
    """
    # pyrefly: ignore [missing-import]
    from bson import ObjectId

    db = get_doctoralia_async_db()
    col = db["doctor_profiles"]

    # pyrefly: ignore [missing-import]
    from bson.errors import InvalidId

    try:
        oid = ObjectId(especialista_id)
        query = {"_id": {"$in": [oid, especialista_id]}}
    except InvalidId:
        query = {"_id": especialista_id}

    doc = await col.find_one(query)

    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    doc = _serializar_doc(doc)
    doctoralia_id = (doc.get("doctor") or {}).get("id_doctoralia")
    analisis_doc = None
    if doctoralia_id:
        analisis_doc = await analisis_repo.obtener_por_doctoralia_id(doctoralia_id)

    doc["analisis"] = _extraer_analisis_detalle(analisis_doc)
    return doc


# =============================================================================
# DELETE (legacy)
# =============================================================================


@router.delete("/{especialista_id}")
async def eliminar_especialista(especialista_id: str):
    """
    Elimina un especialista de ``doctor_profiles`` por su ``_id``.

    Parámetros
    ----------
    especialista_id : str
        ``_id`` de MongoDB del documento a eliminar.
    """
    # pyrefly: ignore [missing-import]
    from bson import ObjectId

    db = get_doctoralia_async_db()
    col = db["doctor_profiles"]

    # pyrefly: ignore [missing-import]
    from bson.errors import InvalidId

    try:
        oid = ObjectId(especialista_id)
        query = {"_id": {"$in": [oid, especialista_id]}}
    except InvalidId:
        query = {"_id": especialista_id}

    resultado = await col.delete_one(query)

    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")
    return {"eliminado": True}


# =============================================================================
# ENDPOINTS LEGACY (catálogo) — conservados por compatibilidad
# =============================================================================


@router.post("/catalogo/cargar")
async def cargar_catalogo(payload: CatalogoCargaRequest):
    """[Legacy] Carga el catálogo desde fixtures. Redirige al nuevo sistema."""
    return {
        "mensaje": "El catálogo ahora se sirve directamente desde la BD Doctoralia. "
        "Usa GET /catalogos/especialidades y GET /catalogos/ciudades.",
        "especialidad": payload.especialidad,
        "ciudad": payload.ciudad,
    }


@router.post("/catalogo/actualizar")
async def actualizar_catalogo():
    """[Legacy] Actualizaba el catálogo vía scraping. Ya no es necesario."""
    return {
        "mensaje": "El catálogo se actualiza automáticamente con el pipeline de scraping de Doctoralia. "
        "No se requiere acción manual.",
    }
