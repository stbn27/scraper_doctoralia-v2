"""
Router del chatbot médico y endpoint combinado de recomendación.

Endpoints:
- POST /chat/interpretar       — Interpreta lenguaje natural (público).
- POST /chat/interpretar/auth  — Versión con contexto de usuario autenticado.
- POST /recomendar             — Interpreta y ejecuta la búsqueda si tiene datos.
"""

from __future__ import annotations

import logging
import random
import json
from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    ChatInterpretRequest,
    ChatInterpretResponse,
    RecomendarRequest,
    RecomendarResponse,
)
from app.security import get_current_user
from app.services import busqueda_service, chat_service
from app.db.mysql import get_mysql_conn

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chatbot"])


def _obtener_ciudad_usuario(usuario_id: int) -> Optional[str]:
    """
    Obtiene la ciudad de la dirección principal del usuario desde MySQL.

    Parámetros
    ----------
    usuario_id : int
        ID del usuario autenticado.

    Retorna
    -------
    str o None
        Ciudad registrada como principal o None si no existe.
    """
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT municipio_alcaldia, ciudad, estado FROM usuarios_direcciones
            WHERE usuario_id = %s AND es_principal = TRUE
            LIMIT 1
            """,
            (usuario_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
            
        mun = row.get("municipio_alcaldia")
        ciu = row.get("ciudad")
        est = row.get("estado")
        
        parts = []
        if mun and mun.strip():
            parts.append(mun.strip())
        if ciu and ciu.strip() and ciu.strip().lower() != (mun.strip().lower() if mun else ""):
            parts.append(ciu.strip())
        if est and est.strip() and est.strip().lower() != (ciu.strip().lower() if ciu else "") and est.strip().lower() != (mun.strip().lower() if mun else ""):
            parts.append(est.strip())
            
        return ", ".join(parts) if parts else None
    except Exception:
        return None


def _obtener_ubicaciones_usuario(usuario_id: int) -> list[str]:
    """
    Obtiene hasta 3 ubicaciones (ciudades/estados) registradas para el usuario.
    """
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT municipio_alcaldia, ciudad, estado FROM usuarios_direcciones
            WHERE usuario_id = %s
            ORDER BY es_principal DESC, id DESC
            LIMIT 3
            """,
            (usuario_id,),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        ubicaciones = []
        for row in rows:
            mun = row.get("municipio_alcaldia")
            ciu = row.get("ciudad")
            est = row.get("estado")
            
            parts = []
            if mun and mun.strip():
                parts.append(mun.strip())
            if ciu and ciu.strip() and ciu.strip().lower() != (mun.strip().lower() if mun else ""):
                parts.append(ciu.strip())
            if est and est.strip() and est.strip().lower() != (ciu.strip().lower() if ciu else "") and est.strip().lower() != (mun.strip().lower() if mun else ""):
                parts.append(est.strip())
                
            if parts:
                loc = ", ".join(parts)
                if loc not in ubicaciones:
                    ubicaciones.append(loc)
        return ubicaciones
    except Exception as exc:
        logger.error(f"Error en _obtener_ubicaciones_usuario: {exc}")
        return []


def _obtener_especialidades_frecuentes(usuario_id: int) -> list[str]:
    """
    Obtiene las especialidades más buscadas por el usuario desde su historial.
    """
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT especialidad, COUNT(*) as cnt
            FROM historial_busquedas
            WHERE usuario_id = %s AND especialidad IS NOT NULL AND especialidad != ''
            GROUP BY especialidad
            ORDER BY cnt DESC, id DESC
            LIMIT 4
            """,
            (usuario_id,),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [r["especialidad"].strip() for r in rows if r.get("especialidad")]
    except Exception:
        return []


def _obtener_especialidades_sugeridas(usuario_id: int) -> list[str]:
    """
    Retorna especialidades sugeridas combinando el historial del usuario y comunes.
    """
    frecuentes = _obtener_especialidades_frecuentes(usuario_id)
    comunes = [
        "Pediatra",
        "Dentista",
        "Cardiólogo",
        "Dermatólogo",
        "Ortopedista",
        "Ginecólogo",
        "Oftalmólogo",
        "Psicólogo",
    ]

    sugeridas = []
    vistas = set()

    for f in frecuentes:
        f_norm = f.strip().lower()
        if f_norm not in vistas:
            vistas.add(f_norm)
            sugeridas.append(f)

    random.shuffle(comunes)
    for c in comunes:
        if len(sugeridas) >= 4:
            break
        c_norm = c.strip().lower()
        if c_norm not in vistas:
            vistas.add(c_norm)
            sugeridas.append(c)

    return sugeridas


@router.post("/chat/interpretar", response_model=ChatInterpretResponse)
async def interpretar_consulta(body: ChatInterpretRequest):
    """
    Interpreta una consulta médica en lenguaje natural (endpoint público).

    Convierte el texto del usuario en filtros de búsqueda estructurados para
    el endpoint `GET /especialistas`. No requiere autenticación.

    Parámetros
    ----------
    body : ChatInterpretRequest
        Historial de mensajes, consulta actual, filtros conocidos y proveedor LLM.

    Retorna
    -------
    ChatInterpretResponse
        Respuesta del LLM con filtros detectados, campos faltantes y parámetros
        de búsqueda cuando la información es suficiente.

    Excepciones
    -----------
    HTTPException 503
        Si todos los proveedores LLM no están disponibles.
    """
    try:
        resultado = await chat_service.interpretar_consulta_medica(
            consulta=body.consulta,
            messages=[m.model_dump() for m in body.messages],
            provider=body.provider,
            ubicacion_usuario=None,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return resultado


@router.post("/chat/interpretar/auth", response_model=ChatInterpretResponse)
async def interpretar_consulta_autenticado(
    body: ChatInterpretRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Versión autenticada del endpoint de interpretación médica.

    Usa la ciudad registrada del usuario como contexto adicional para el LLM,
    lo que mejora la detección de la ubicación cuando el usuario no la menciona.

    Parámetros
    ----------
    body : ChatInterpretRequest
        Historial de mensajes, consulta actual y proveedor LLM.
    current_user : dict
        Usuario autenticado extraído del JWT.

    Retorna
    -------
    ChatInterpretResponse
        Respuesta del LLM enriquecida con contexto de ubicación del usuario.

    Excepciones
    -----------
    HTTPException 503
        Si todos los proveedores LLM no están disponibles.
    """
    usuario_id = current_user["id"]
    ubicacion_usuario = _obtener_ciudad_usuario(usuario_id)

    try:
        resultado = await chat_service.interpretar_consulta_medica(
            consulta=body.consulta,
            messages=[m.model_dump() for m in body.messages],
            provider=body.provider,
            ubicacion_usuario=ubicacion_usuario,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    filtros = resultado.get("filtros") or {}
    ubicacion_detectada = filtros.get("ubicacion")

    # 1. Si no hay ubicación en los filtros, sugerir ubicaciones registradas del usuario
    if not ubicacion_detectada:
        if not resultado.get("sql"):
            resultado["sql"] = []
        if "LOCATION_USER" not in resultado["sql"]:
            resultado["sql"].append("LOCATION_USER")

        ubicaciones = _obtener_ubicaciones_usuario(usuario_id)
        if ubicaciones:
            resultado["ubicaciones_usuario"] = ubicaciones

    # 2. Si no hay especialidad detectada en los filtros, sugerir especialidades frecuentes o aleatorias
    especialidad_detectada = filtros.get("especialidad")
    if not especialidad_detectada:
        sugerencias_especialidades = _obtener_especialidades_sugeridas(usuario_id)
        if sugerencias_especialidades:
            resultado["sugerencias"] = sugerencias_especialidades

    return resultado


@router.post("/recomendar")
async def recomendar(body: RecomendarRequest):
    """
    Interpreta la consulta médica y ejecuta la búsqueda si tiene datos suficientes.

    Si la interpretación no detecta especialidad + ciudad, devuelve la pregunta
    del asistente con resultados vacíos. Si tiene todos los datos necesarios,
    ejecuta la búsqueda en MongoDB y retorna los especialistas encontrados.

    Parámetros
    ----------
    body : RecomendarRequest
        Consulta en lenguaje natural, proveedor LLM y límite de resultados.

    Retorna
    -------
    dict
        Interpretación del LLM + lista de especialistas (puede estar vacía).

    Excepciones
    -----------
    HTTPException 503
        Si todos los proveedores LLM no están disponibles.
    """
    try:
        interpretacion = await chat_service.interpretar_consulta_medica(
            consulta=body.consulta,
            messages=[],
            provider=body.provider,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if not interpretacion.get("ready"):
        return {
            "interpretacion": {
                "ready": False,
                "mensaje": interpretacion.get("mensaje", ""),
                "respuesta": interpretacion.get("respuesta", []),
            },
            "results": [],
        }

    filtros = interpretacion.get("filtros") or {}
    otros = filtros.get("otros") or {}

    params_busqueda = {
        "especialidad": filtros.get("especialidad"),
        "ciudad": filtros.get("ubicacion"),
        "orden": "puntuacion_desc",
        "solo_analizados": True,
        "solo_con_opiniones": True,
        "atiende_ninos": otros.get("atiende_ninos", False),
        "atiende_adultos": otros.get("atiende_adultos", True),
        "atiende_adolescentes": otros.get("atiende_adolescentes", False),
    }

    resultado_busqueda = await busqueda_service.buscar_especialistas_paginado(
        params=params_busqueda,
        page=1,
        limit=body.limit,
    )

    return {
        "interpretacion": {
            "ready": True,
            "especialidad": filtros.get("especialidad"),
            "ciudad": filtros.get("ubicacion"),
            "filtros": filtros,
        },
        "results": resultado_busqueda.get("results", []),
    }
