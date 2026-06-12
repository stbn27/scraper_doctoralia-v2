"""
Router del chatbot médico y endpoint combinado de recomendación.

Endpoints:
- POST /chat/interpretar       — Interpreta lenguaje natural (público).
- POST /chat/interpretar/auth  — Versión con contexto de usuario autenticado.
- POST /recomendar             — Interpreta y ejecuta la búsqueda si tiene datos.
"""

from __future__ import annotations

import logging
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
            SELECT ciudad FROM usuarios_direcciones
            WHERE usuario_id = %s AND es_principal = TRUE
            LIMIT 1
            """,
            (usuario_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row["ciudad"] if row else None
    except Exception:
        return None


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
    ubicacion_usuario = _obtener_ciudad_usuario(current_user["id"])

    try:
        resultado = await chat_service.interpretar_consulta_medica(
            consulta=body.consulta,
            messages=[m.model_dump() for m in body.messages],
            provider=body.provider,
            ubicacion_usuario=ubicacion_usuario,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

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
