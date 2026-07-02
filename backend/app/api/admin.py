"""
Router de administración — solo para usuarios con rol ADMIN.

Endpoints
---------
- GET  /admin/estadisticas          → Resumen global del sistema
- GET  /admin/especialistas         → Lista paginada con datos de scraping y análisis
- GET  /admin/especialistas/{id}    → Detalle admin de un especialista
- GET  /admin/scraping/resumen      → Estado del pipeline de scraping
"""

from __future__ import annotations

import math
import re
from typing import Optional, Any

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.mongo import get_doctoralia_async_db
from app.db.mysql import get_mysql_conn
from app.security import get_current_user

# pyrefly: ignore [missing-import]
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Administración"])


# =============================================================================
# Dependencia de rol ADMIN
# =============================================================================


def _requerir_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependencia de seguridad que valida que el usuario tenga rol ADMIN.

    Parámetros
    ----------
    current_user : dict
        Usuario autenticado extraído del JWT.

    Retorna
    -------
    dict
        El mismo usuario si tiene rol ADMIN.

    Excepciones
    -----------
    HTTPException 403
        Si el usuario no tiene rol ADMIN.
    """
    rol = current_user.get("rol", "USER")
    if rol != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. Se requiere rol ADMIN para esta operación.",
        )
    return current_user


# =============================================================================
# GET /admin/estadisticas
# =============================================================================


@router.get("/estadisticas")
async def obtener_estadisticas_globales(
    _admin: dict = Depends(_requerir_admin),
):
    """
    Retorna el resumen estadístico global del sistema para el panel de administración.

    Incluye totales de especialistas, opiniones, análisis y usuarios.

    Parámetros
    ----------
    _admin : dict
        Usuario administrador (inyectado por dependencia).

    Retorna
    -------
    dict
        Resumen con conteos y métricas globales del sistema.
    """
    db = get_doctoralia_async_db()

    # Conteos en paralelo
    total_especialistas = await db["doctor_profiles"].count_documents({})
    total_opiniones = await db["doctor_opinions"].count_documents({})
    total_analisis = await db["analisis_especialistas"].count_documents({})
    total_ciudades = await db["cities"].count_documents({})
    total_especialidades = await db["specializations"].count_documents({})

    # Especialistas con y sin opiniones
    especialistas_con_opiniones = await db["doctor_opinions"].distinct("doctor_id")
    especialistas_sin_opiniones = total_especialistas - len(especialistas_con_opiniones)

    # Análisis por estado
    pipeline_estados = [
        {"$group": {"_id": "$estatus_analisis", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]
    estados_analisis: dict[str, int] = {}
    async for doc in db["analisis_especialistas"].aggregate(pipeline_estados):
        estados_analisis[doc["_id"] or "sin_estado"] = doc["total"]

    # Análisis por modelo
    pipeline_modelos = [
        {"$match": {"modelo_usado": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$modelo_usado", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]
    modelos_usados: dict[str, int] = {}
    async for doc in db["analisis_especialistas"].aggregate(pipeline_modelos):
        modelos_usados[doc["_id"]] = doc["total"]

    # Con y sin análisis
    con_analisis = await db["analisis_especialistas"].count_documents(
        {"estatus_analisis": {"$ne": "sin_opiniones"}}
    )

    # Último scraping (por persistedAt en queue_meta)
    ultimo_scraping = None
    ultimo_doc = await db["doctor_profiles"].find_one(
        {"queue_meta.persistedAt": {"$exists": True}},
        sort=[("queue_meta.persistedAt", -1)],
    )
    if ultimo_doc and (ultimo_doc.get("queue_meta") or {}).get("persistedAt"):
        ultimo_scraping = ultimo_doc["queue_meta"]["persistedAt"].isoformat()

    # Usuarios en MySQL
    total_usuarios = 0
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
        row = cursor.fetchone()
        total_usuarios = row["total"] if row else 0
        cursor.close()
        conn.close()
    except Exception:
        pass

    return {
        "especialistas": {
            "total": total_especialistas,
            "con_analisis": con_analisis,
            "sin_analisis": total_especialistas - con_analisis,
            "con_opiniones": len(especialistas_con_opiniones),
            "sin_opiniones": especialistas_sin_opiniones,
        },
        "opiniones": {"total": total_opiniones},
        "analisis": {
            "total": total_analisis,
            "por_estado": estados_analisis,
            "por_modelo": modelos_usados,
        },
        "catalogo": {
            "ciudades": total_ciudades,
            "especialidades": total_especialidades,
        },
        "usuarios": {"total": total_usuarios},
        "scraping": {"ultimo_registro": ultimo_scraping},
    }


# =============================================================================
# GET /admin/usuarios
# =============================================================================


@router.get("/usuarios")
def listar_usuarios_admin(
    _admin: dict = Depends(_requerir_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None),
):
    """
    Lista usuarios registrados para el panel de administración.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    where_clause = ""
    params = []
    if q:
        where_clause = "WHERE u.nombre LIKE %s OR u.email LIKE %s OR u.apellido LIKE %s"
        like_q = f"%{q}%"
        params.extend([like_q, like_q, like_q])

    # Total
    cursor.execute(f"SELECT COUNT(*) AS total FROM usuarios u {where_clause}", params)
    total_row = cursor.fetchone()
    total = total_row["total"] if total_row else 0

    # Data
    offset = (page - 1) * limit
    params.extend([limit, offset])

    try:
        cursor.execute(f"""
            SELECT u.id, u.email, u.nombre, u.apellido, u.telefono, u.avatar_url, u.created_at, r.nombre AS rol
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            {where_clause}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """, params)
        usuarios = cursor.fetchall()
    except Exception:
        # Fallback si no existe tabla roles
        cursor.execute(f"""
            SELECT u.id, u.email, u.nombre, u.apellido, u.telefono, u.avatar_url, u.created_at, 'USER' AS rol
            FROM usuarios u
            {where_clause}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """, params)
        usuarios = cursor.fetchall()

    cursor.close()
    conn.close()

    for u in usuarios:
        if u.get("created_at"):
            u["created_at"] = u["created_at"].isoformat()

    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
        "usuarios": usuarios
    }


# =============================================================================
# GET /admin/especialistas
# =============================================================================


@router.get("/especialistas")
async def listar_especialistas_admin(
    q: Optional[str] = Query(None, description="Búsqueda por nombre del doctor"),
    especialidad: Optional[str] = Query(None, description="Filtrar por especialidad"),
    ciudad: Optional[str] = Query(None, description="Filtrar por ciudad"),
    con_analisis: Optional[bool] = Query(
        None, description="Filtrar por presencia de análisis"
    ),
    modelo_usado: Optional[str] = Query(
        None, description="Filtrar por modelo de IA usado"
    ),
    estatus_analisis: Optional[str] = Query(
        None, description="Filtrar por estatus de análisis"
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query(None, description="Campo para ordenar"),
    sort_order: Optional[str] = Query(None, description="Orden (asc o desc)"),
    _admin: dict = Depends(_requerir_admin),
):
    """
    Lista especialistas con datos de scraping, estadísticas y análisis IA.

    Diseñado para el panel de administración. Incluye:
    - Datos del perfil del doctor
    - Fecha del último scraping (queue_meta.persistedAt)
    - Total de opiniones registradas en BD
    - Estado y modelo del análisis IA

    Parámetros
    ----------
    q : str, opcional
        Búsqueda por nombre del doctor.
    especialidad : str, opcional
        Filtrar por especialidad.
    ciudad : str, opcional
        Filtrar por ciudad.
    con_analisis : bool, opcional
        True = solo con análisis, False = solo sin análisis.
    modelo_usado : str, opcional
        Filtrar por modelo de IA usado (deepseek, groq, gemini, etc.).
    estatus_analisis : str, opcional
        Filtrar por estatus del análisis.
    page : int
        Página actual.
    limit : int
        Resultados por página.

    Retorna
    -------
    dict
        Respuesta paginada con lista de especialistas enriquecidos.
    """
    db = get_doctoralia_async_db()
    col_doc = db["doctor_profiles"]
    col_ana = db["analisis_especialistas"]

    # Pre-filtro por análisis si aplica
    ids_validos: Optional[set[int]] = None
    if con_analisis is not None or modelo_usado or estatus_analisis:
        filtro_ana: dict[str, Any] = {}
        if con_analisis is False:
            # Sin análisis: buscar IDs que NO están en analisis
            ids_con = set()
            async for doc in col_ana.find({}, {"id_doctoralia": 1}):
                if doc.get("id_doctoralia"):
                    ids_con.add(doc["id_doctoralia"])
            # Esto se manejará en el filtro principal como $nin
            filtro_doc: dict = {}
            if ids_con:
                filtro_doc["doctor.id_doctoralia"] = {"$nin": list(ids_con)}
        else:
            if con_analisis is True:
                pass  # No filtro adicional en analisis, solo verificamos que exista
            if modelo_usado:
                filtro_ana["modelo_usado"] = {
                    "$regex": re.escape(modelo_usado.strip()),
                    "$options": "i",
                }
            if estatus_analisis:
                filtro_ana["estatus_analisis"] = estatus_analisis

            ids_validos = set()
            async for doc in col_ana.find(filtro_ana, {"id_doctoralia": 1}):
                if doc.get("id_doctoralia"):
                    ids_validos.add(doc["id_doctoralia"])

    # Filtro principal sobre doctor_profiles
    filtro_doc = {}
    if q:
        filtro_doc["doctor.nombre"] = {"$regex": re.escape(q.strip()), "$options": "i"}
    if especialidad:
        filtro_doc["doctor.especialidades"] = {
            "$regex": re.escape(especialidad.strip()),
            "$options": "i",
        }
    if ciudad:
        filtro_doc["$or"] = [
            {
                "doctor.direcciones.ciudad": {
                    "$regex": re.escape(ciudad.strip()),
                    "$options": "i",
                }
            },
            {"doctor.estado": {"$regex": re.escape(ciudad.strip()), "$options": "i"}},
        ]
    if ids_validos is not None:
        filtro_doc["doctor.id_doctoralia"] = {"$in": list(ids_validos)}
    if con_analisis is False and not ids_validos:
        # Caso sin análisis: excluir los que SÍ tienen
        ids_con_analisis = set()
        async for doc in col_ana.find({}, {"id_doctoralia": 1}):
            if doc.get("id_doctoralia"):
                ids_con_analisis.add(doc["id_doctoralia"])
        if ids_con_analisis:
            filtro_doc["doctor.id_doctoralia"] = {"$nin": list(ids_con_analisis)}

    total = await col_doc.count_documents(filtro_doc)
    pages = math.ceil(total / limit) if limit and total else 0
    skip = (page - 1) * limit

    sort_dict = [("queue_meta.persistedAt", -1)]
    if sort_by and sort_order:
        direccion = 1 if sort_order.lower() == "asc" else -1
        sort_dict = [(sort_by, direccion)]

    docs = [
        doc
        async for doc in col_doc.find(filtro_doc)
        .sort(sort_dict)
        .skip(skip)
        .limit(limit)
    ]

    # Batch de análisis para los docs de esta página
    doctoralia_ids = [
        (d.get("doctor") or {}).get("id_doctoralia")
        for d in docs
        if (d.get("doctor") or {}).get("id_doctoralia")
    ]
    mapa_analisis: dict[int, dict] = {}
    async for ana in col_ana.find({"id_doctoralia": {"$in": doctoralia_ids}}):
        did = ana.get("id_doctoralia")
        if did:
            mapa_analisis[did] = ana

    # Batch de conteo de opiniones por doctor_id
    pipeline_opiniones = [
        {"$match": {"doctor_id": {"$in": doctoralia_ids}}},
        {"$group": {"_id": "$doctor_id", "total": {"$sum": 1}}},
    ]
    mapa_opiniones: dict[int, int] = {}
    async for doc in db["doctor_opinions"].aggregate(pipeline_opiniones):
        mapa_opiniones[doc["_id"]] = doc["total"]

    # Construir lista
    especialistas = []
    for doc in docs:
        doctor = doc.get("doctor") or {}
        did = doctor.get("id_doctoralia")
        ana = mapa_analisis.get(did)
        queue = doc.get("queue_meta") or {}
        meta = doc.get("metadata") or {}

        # Fecha del último scraping
        persisted_at = queue.get("persistedAt")
        ultimo_scraping_str = persisted_at.isoformat() if persisted_at else None

        # Fecha de la fuente (consulta original)
        fecha_consulta = meta.get("fecha_consulta")

        # Datos del análisis
        analisis_info = None
        if ana:
            a = ana.get("analisis") or {}
            meta_ana = ana.get("metadata_analisis") or {}
            meta_op = ana.get("metadata_opiniones") or {}
            analisis_info = {
                "estatus": ana.get("estatus_analisis"),
                "modelo_usado": ana.get("modelo_usado"),
                "version_prompt": ana.get("version_prompt"),
                "fecha_analisis": str(meta_ana.get("fecha", "")),
                "puntuacion": a.get("puntuacion"),
                "confiabilidad": a.get("confiabilidad"),
                "resumen": a.get("resumen"),
                "sospecha_fraude": (meta_op or {}).get("sospecha_fraude"),
                "opiniones_analizadas": meta_ana.get("opiniones_enviadas"),
            }

        # Ciudades únicas
        direcciones = doctor.get("direcciones") or []
        ciudades_lista = []
        for d in direcciones:
            c = d.get("ciudad")
            if c and c not in ciudades_lista:
                ciudades_lista.append(c)

        especialistas.append(
            {
                "_id": str(doc.get("_id", "")),
                "doctoralia_id": did,
                "nombre": doctor.get("nombre", ""),
                "especialidades": doctor.get("especialidades") or [],
                "ciudades": ciudades_lista,
                "estado": (doctor.get("estado") or [None])[0],
                "foto_perfil": doctor.get("foto_perfil"),
                "cedulas": doctor.get("cedulas") or [],
                "total_opiniones_perfil": doc.get("total_opiniones", 0),
                "total_opiniones_bd": mapa_opiniones.get(did, 0),
                "tiene_analisis": ana is not None,
                "analisis": analisis_info,
                "scraping": {
                    "ultimo_scraping": ultimo_scraping_str,
                    "fecha_consulta": fecha_consulta,
                    "fuente": meta.get("fuente"),
                    "fuente_busqueda": meta.get("fuente_busqueda"),
                    "priority_score": queue.get("priority_score"),
                    "discovery_sources": queue.get("discovery_sources") or [],
                },
            }
        )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
        "especialistas": especialistas,
    }


# =============================================================================
# GET /admin/especialistas/{doctoralia_id}
# =============================================================================


@router.get("/especialistas/{doctoralia_id}")
async def detalle_especialista_admin(
    doctoralia_id: int,
    _admin: dict = Depends(_requerir_admin),
):
    """
    Obtiene el detalle completo de un especialista para la vista de administración.

    Incluye todos los datos de scraping, análisis IA completo y estadísticas de opiniones.

    Parámetros
    ----------
    doctoralia_id : int
        ID numérico del especialista en Doctoralia.

    Retorna
    -------
    dict
        Detalle completo del especialista con análisis y estadísticas.

    Excepciones
    -----------
    HTTPException 404
        Si el especialista no existe.
    """
    db = get_doctoralia_async_db()

    doc = await db["doctor_profiles"].find_one({"doctor.id_doctoralia": doctoralia_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    ana = await db["analisis_especialistas"].find_one({"id_doctoralia": doctoralia_id})
    total_opiniones_bd = await db["doctor_opinions"].count_documents(
        {"doctor_id": doctoralia_id}
    )

    # Pipeline de ratings para estadísticas de opiniones
    pipeline_ratings = [
        {"$match": {"doctor_id": doctoralia_id}},
        {
            "$group": {
                "_id": None,
                "rating_promedio": {"$avg": "$rating"},
                "total": {"$sum": 1},
                "verificadas": {
                    "$sum": {
                        "$cond": [
                            {
                                "$regexMatch": {
                                    "input": {"$ifNull": ["$tipo_verificacion", ""]},
                                    "regex": "verific",
                                }
                            },
                            1,
                            0,
                        ]
                    }
                },
            }
        },
    ]
    estadisticas_opiniones = {}
    async for stat in db["doctor_opinions"].aggregate(pipeline_ratings):
        estadisticas_opiniones = {
            "rating_promedio": round(stat.get("rating_promedio") or 0, 2),
            "total": stat.get("total", 0),
            "verificadas": stat.get("verificadas", 0),
        }

    doc["_id"] = str(doc["_id"])
    queue = doc.get("queue_meta") or {}
    meta = doc.get("metadata") or {}
    persisted_at = queue.get("persistedAt")

    analisis_completo = None
    if ana:
        a = ana.get("analisis") or {}
        meta_ana = ana.get("metadata_analisis") or {}
        meta_op = ana.get("metadata_opiniones") or {}
        analisis_completo = {
            "estatus": ana.get("estatus_analisis"),
            "modelo_usado": ana.get("modelo_usado") or meta_ana.get("modelo") or meta_ana.get("modelo_usado"),
            "version_prompt": ana.get("version_prompt") or meta_ana.get("version_prompt") or ana.get("prompt_version"),
            "fecha_analisis": str(meta_ana.get("fecha", "")),
            "puntuacion": a.get("puntuacion"),
            "resumen": a.get("resumen"),
            "puntos_fuertes": a.get("puntos_fuertes") or [],
            "puntos_debiles": a.get("puntos_debiles") or [],
            "confiabilidad": a.get("confiabilidad"),
            "justificacion": a.get("justificacion"),
            "alertas_preprocesamiento": ana.get("alertas_preprocesamiento"),
            "sospecha_fraude": meta_op.get("sospecha_fraude"),
            "razones_fraude": meta_op.get("razones_fraude") or [],
            "opiniones_en_bd": meta_op.get("opiniones_bd"),
            "opiniones_enviadas_modelo": meta_ana.get("opiniones_enviadas"),
            "rating_promedio_analisis": meta_op.get("rating_promedio"),
            "recencia_promedio_dias": meta_op.get("recencia_promedio_dias"),
        }

    return {
        "_id": str(doc.get("_id", "")),
        "doctor": doc.get("doctor"),
        "doctoralia_id": doctoralia_id,
        "total_opiniones_perfil": doc.get("total_opiniones", 0),
        "total_opiniones_bd": total_opiniones_bd,
        "estadisticas_opiniones_bd": estadisticas_opiniones,
        "tiene_analisis": ana is not None,
        "analisis": analisis_completo,
        "scraping": {
            "ultimo_scraping": persisted_at.isoformat() if persisted_at else None,
            "fecha_consulta": meta.get("fecha_consulta"),
            "fuente": meta.get("fuente"),
            "fuente_busqueda": meta.get("fuente_busqueda"),
            "moneda": meta.get("moneda_por_defecto"),
            "idioma": meta.get("idioma"),
            "priority_score": queue.get("priority_score"),
            "discovery_sources": queue.get("discovery_sources") or [],
        },
    }


# =============================================================================
# GET /admin/scraping/resumen
# =============================================================================


@router.get("/scraping/resumen")
async def resumen_scraping(
    _admin: dict = Depends(_requerir_admin),
):
    """
    Retorna el resumen del estado del pipeline de scraping.

    Muestra los registros más recientes y el histograma de scraping por fecha.

    Retorna
    -------
    dict
        Estado del scraping con últimos registros y distribución temporal.
    """
    db = get_doctoralia_async_db()

    # Los 10 doctores scrapeados más recientemente
    ultimos = []
    async for doc in (
        db["doctor_profiles"]
        .find({"queue_meta.persistedAt": {"$exists": True}})
        .sort("queue_meta.persistedAt", -1)
        .limit(10)
    ):
        doctor = doc.get("doctor") or {}
        queue = doc.get("queue_meta") or {}
        persisted = queue.get("persistedAt")
        ultimos.append(
            {
                "doctoralia_id": doctor.get("id_doctoralia"),
                "nombre": doctor.get("nombre", ""),
                "especialidades": (doctor.get("especialidades") or [])[:2],
                "ultimo_scraping": persisted.isoformat() if persisted else None,
                "priority_score": queue.get("priority_score"),
            }
        )

    # Total en cola de scraping
    total_en_cola = (
        await db["doctor_queue"].count_documents({})
        if "doctor_queue" in await db.list_collection_names()
        else 0
    )

    # Distribución por fuente de descubrimiento
    pipeline_fuentes = [
        {"$unwind": "$queue_meta.discovery_sources"},
        {"$group": {"_id": "$queue_meta.discovery_sources", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": 10},
    ]
    fuentes = {}
    async for doc in db["doctor_profiles"].aggregate(pipeline_fuentes):
        fuentes[doc["_id"]] = doc["total"]

    return {
        "ultimos_scrapeados": ultimos,
        "total_en_cola": total_en_cola,
        "top_fuentes_descubrimiento": fuentes,
    }


# =============================================================================
# DELETE /admin/especialistas/{doctoralia_id}
# =============================================================================


@router.delete("/especialistas/{doctoralia_id}")
async def eliminar_especialista_admin(
    doctoralia_id: int,
    _admin: dict = Depends(_requerir_admin),
):
    """
    Elimina en cascada un especialista y toda su información relacionada.
    
    Borra de las siguientes colecciones:
    1. doctor_opinions
    2. analisis_especialistas
    3. doctor_profiles
    
    Parámetros
    ----------
    doctoralia_id : int
        ID numérico del especialista en Doctoralia.
        
    Retorna
    -------
    dict
        Resultado de la operación indicando registros eliminados.
    """
    db = get_doctoralia_async_db()
    
    # 1. Comprobar que el especialista existe
    doc = await db["doctor_profiles"].find_one({"doctor.id_doctoralia": doctoralia_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")
        
    # En un cluster MongoDB replica set, podríamos usar db.client.start_session() y start_transaction().
    # Como fallback seguro, hacemos las eliminaciones secuencialmente e informamos.
    try:
        # 1. Opiniones
        opiniones_res = await db["doctor_opinions"].delete_many({"doctor_id": doctoralia_id})
        
        # 2. Análisis
        analisis_res = await db["analisis_especialistas"].delete_many({"id_doctoralia": doctoralia_id})
        
        # 3. Perfil
        perfil_res = await db["doctor_profiles"].delete_one({"doctor.id_doctoralia": doctoralia_id})
        
        return {
            "eliminado": True,
            "doctoralia_id": doctoralia_id,
            "detalle": {
                "opiniones_eliminadas": opiniones_res.deleted_count,
                "analisis_eliminados": analisis_res.deleted_count,
                "perfil_eliminado": perfil_res.deleted_count > 0
            }
        }
    except Exception as e:
        # En caso de error, el error se levanta con detalle parcial
        raise HTTPException(
            status_code=500, 
            detail=f"Error parcial en la eliminación en cascada: {str(e)}"
        )


class ValidarUrlRequest(BaseModel):
    url: str

@router.post("/especialistas/validar-url")
async def validar_url_admin(
    payload: ValidarUrlRequest,
    _admin: dict = Depends(_requerir_admin),
):
    """
    Valida una URL de Doctoralia y verifica si ya existe en la base de datos.
    Soporta normalización de URLs (limpieza de fragmentos, query params y slashes).
    """
    url = payload.url.strip()
    if not url.startswith("http") or "doctoralia.com.mx" not in url:
        return {"valida": False, "existe": False, "error": "URL no pertenece a doctoralia.com.mx o formato incorrecto"}
        
    from urllib.parse import urlparse
    parsed = urlparse(url)
    clean_url = parsed._replace(query="", fragment="").geturl().rstrip('/')
    clean_path = parsed.path.rstrip('/')

    db = get_doctoralia_async_db()
    
    condiciones = [
        {"doctor.url_perfil": clean_url},
        {"doctor.url_perfil": clean_url + "/"},
        {"metadata.fuente": clean_url},
        {"metadata.fuente": clean_url + "/"},
        {"scraping_meta.url_origen": clean_url},
        {"scraping_meta.url_origen": clean_url + "/"},
    ]

    # Extraer path o slug para comparar de forma flexible ante variaciones en la URL
    if clean_path and clean_path != "/":
        regex_path = re.escape(clean_path)
        condiciones.extend([
            {"doctor.url_perfil": {"$regex": regex_path, "$options": "i"}},
            {"metadata.fuente": {"$regex": regex_path, "$options": "i"}}
        ])
        
        path_parts = [p for p in clean_path.split('/') if p]
        if path_parts and path_parts[0] not in ('buscar', 'clinicas', 'centros-medicos', 'enfermedades', 'medicamentos', 'preguntas-respuestas'):
            slug = path_parts[0]
            if len(slug) > 3:
                regex_slug = f"/{re.escape(slug)}(/|$)"
                condiciones.extend([
                    {"doctor.url_perfil": {"$regex": regex_slug, "$options": "i"}},
                    {"metadata.fuente": {"$regex": regex_slug, "$options": "i"}}
                ])

    doc = await db["doctor_profiles"].find_one({"$or": condiciones})
    
    if doc:
        return {
            "valida": True,
            "existe": True,
            "doctoralia_id": doc.get("doctor", {}).get("id_doctoralia"),
            "nombre": doc.get("doctor", {}).get("nombre", "")
        }
        
    return {
        "valida": True,
        "existe": False
    }
