"""
Servicio de interpretación médica mediante LLM (Groq / Gemini).

Convierte mensajes en lenguaje natural del usuario en filtros de búsqueda
estructurados para el endpoint GET /especialistas.
Reutiliza las clases GroqModelo y GeminiModelo del pipeline NLP existente.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Optional

from app.nlp.modelos.groq_modelo import GroqModelo
from app.nlp.modelos.gemini_modelo import GeminiModelo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt del sistema
# ---------------------------------------------------------------------------

PROMPT_SISTEMA = """Actúa como un asistente de orientación médica para un sistema de búsqueda de especialistas.

Tu tarea NO es diagnosticar, NO es dar tratamiento y NO es reemplazar a un médico.
Tu tarea es interpretar lo que el usuario escribe y convertirlo en filtros de búsqueda para encontrar especialistas médicos.

Debes responder SIEMPRE en JSON válido. No uses Markdown. No escribas texto fuera del JSON.

Campos obligatorios de salida:

{
  "reply": string,
  "ready": boolean,
  "should_search": boolean,
  "detected": {
    "especialidad": string | null,
    "especialidad_slug": string | null,
    "ciudad": string | null,
    "ciudad_slug": string | null,
    "tipo_paciente": "nino" | "adulto" | "adolescente" | null,
    "atiende_ninos": boolean,
    "atiende_adultos": boolean,
    "atiende_adolescentes": boolean,
    "servicio": string | null,
    "orden": "puntuacion_desc" | "opiniones_desc" | "rating_desc" | null,
    "solo_analizados": boolean,
    "solo_con_opiniones": boolean,
    "confiabilidad": "alta" | "media" | "baja" | "sospechosa" | null,
    "sospecha_fraude": boolean | null,
    "precio_min": number | null,
    "precio_max": number | null
  },
  "missing_fields": string[],
  "suggestions": [
    {
      "type": "city" | "specialty" | "patient_type" | "action",
      "label": string,
      "value": string
    }
  ],
  "search_params": object | null,
  "safety": {
    "is_emergency": boolean,
    "message": string | null
  }
}

Reglas:
1. Si el usuario menciona síntomas o molestias, sugiere una especialidad probable.
2. Si falta ciudad o ubicación, pregunta por ciudad, estado o código postal.
3. Si falta suficiente información para determinar especialidad, pregunta de forma concreta.
4. Si hay especialidad y ubicación, ready debe ser true y should_search debe ser true.
5. Si falta especialidad o ubicación, ready debe ser false y should_search debe ser false.
6. Si el usuario menciona una urgencia grave, safety.is_emergency debe ser true y reply debe recomendar acudir a urgencias.
7. No inventes ciudades ni especialistas que no estén claros.
8. Normaliza especialidades a slugs cuando sea posible:
   - dolor de muela, caries, endodoncia, diente -> endodoncia o dentista
   - problemas de pareja, ansiedad, depresión, estrés emocional -> psicologo
   - embarazo, menstruación, revisión ginecológica -> ginecologo
   - corazón, dolor de pecho, presión alta -> cardiologo
   - piel, acné, manchas, ronchas -> dermatologo
   - huesos, articulaciones, rodilla, columna -> ortopedista
   - niños, pediatría -> pediatra
   - ojos, visión -> oftalmologo
   - oídos, nariz, garganta -> otorrinolaringologo
9. Si hay duda entre dos especialidades, haz una pregunta.
10. Señales de emergencia (is_emergency=true):
    - dolor de pecho intenso, dificultad para respirar, pérdida de conciencia,
      sangrado abundante, idea suicida, violencia física, abuso sexual,
      embarazo con sangrado intenso, dolor súbito e intenso, síntomas neurológicos graves.
11. Si el usuario tiene una ubicación registrada y se proporciona, úsala como sugerencia de ciudad.
12. search_params solo se incluye cuando ready=true con los filtros mínimos para buscar.
"""


def _construir_prompt_usuario(
    messages: list[dict],
    consulta: str,
    ubicacion_usuario: Optional[str] = None,
) -> str:
    """
    Construye el prompt de usuario a partir del historial de mensajes y la consulta actual.

    Parámetros
    ----------
    messages : list[dict]
        Historial de mensajes `[{role, content}, ...]`.
    consulta : str
        Último mensaje del usuario.
    ubicacion_usuario : str, opcional
        Ciudad registrada del usuario para usar como contexto de ubicación.

    Retorna
    -------
    str
        Prompt de usuario completo para enviar al LLM.
    """
    partes = []

    if ubicacion_usuario:
        partes.append(
            f"[Contexto: El usuario tiene registrada la ciudad '{ubicacion_usuario}']"
        )

    if messages:
        historial = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in messages[-6:]  # Solo últimos 6 mensajes para no exceder tokens
        )
        partes.append(f"Historial de conversación:\n{historial}")

    partes.append(f"Último mensaje del usuario: {consulta}")
    return "\n\n".join(partes)


def _respuesta_emergencia() -> dict:
    """Retorna respuesta estándar de emergencia médica."""
    return {
        "reply": (
            "Lo que describes puede requerir atención inmediata. "
            "Te recomiendo acudir a urgencias o llamar a servicios de emergencia de tu localidad."
        ),
        "ready": False,
        "should_search": False,
        "detected": None,
        "missing_fields": [],
        "suggestions": [],
        "search_params": None,
        "safety": {"is_emergency": True, "message": "Recomendar atención urgente."},
    }


def _construir_instancia_modelo(provider: str):
    """
    Instancia el modelo LLM según el proveedor solicitado.

    Parámetros
    ----------
    provider : str
        'groq', 'gemini' o 'auto'.

    Retorna
    -------
    tuple[BaseModelo, str, str]
        Tupla de (instancia_modelo, nombre_proveedor, nombre_modelo).
    """
    modelo_activo = os.getenv("MODELO_ACTIVO", "groq")

    if provider == "auto":
        provider = modelo_activo

    if provider == "gemini":
        m = GeminiModelo()
        return m, "gemini", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    else:
        m = GroqModelo()
        return m, "groq", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


async def interpretar_consulta_medica(
    consulta: str,
    messages: list[dict],
    provider: str = "groq",
    ubicacion_usuario: Optional[str] = None,
) -> dict[str, Any]:
    """
    Interpreta una consulta médica en lenguaje natural y extrae filtros de búsqueda.

    Llama al LLM configurado (Groq o Gemini) de forma asíncrona usando `asyncio.to_thread`
    ya que los modelos son síncronos. Parsea la respuesta JSON y la devuelve normalizada.

    En caso de error del proveedor, intenta fallback a Gemini si el proveedor principal era Groq.

    Parámetros
    ----------
    consulta : str
        Texto del usuario a interpretar.
    messages : list[dict]
        Historial de la conversación `[{role, content}]`.
    provider : str
        Proveedor LLM: 'groq', 'gemini' o 'auto'. Por defecto 'groq'.
    ubicacion_usuario : str, opcional
        Ciudad del usuario registrada en su perfil.

    Retorna
    -------
    dict
        Respuesta normalizada con: reply, ready, should_search, detected,
        missing_fields, suggestions, search_params, safety, model.

    Excepciones
    -----------
    RuntimeError
        Si todos los proveedores fallan y no se puede obtener respuesta.
    """
    prompt_usuario = _construir_prompt_usuario(messages, consulta, ubicacion_usuario)

    modelo, proveedor_nombre, modelo_nombre = _construir_instancia_modelo(provider)

    try:
        respuesta_raw = await asyncio.to_thread(
            modelo.analizar, PROMPT_SISTEMA, prompt_usuario
        )
        resultado = modelo.parsear_respuesta(respuesta_raw)
    except Exception as exc_principal:
        logger.warning(
            "[ChatService] Error con proveedor %s: %s", proveedor_nombre, exc_principal
        )

        # Fallback a Gemini si el principal era Groq
        if proveedor_nombre == "groq":
            try:
                fallback = GeminiModelo()
                respuesta_raw = await asyncio.to_thread(
                    fallback.analizar, PROMPT_SISTEMA, prompt_usuario
                )
                resultado = fallback.parsear_respuesta(respuesta_raw)
                proveedor_nombre = "gemini"
                modelo_nombre = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            except Exception as exc_fallback:
                logger.error("[ChatService] Fallback también falló: %s", exc_fallback)
                raise RuntimeError(
                    "El servicio de interpretación no está disponible."
                ) from exc_fallback
        else:
            raise RuntimeError(
                "El servicio de interpretación no está disponible."
            ) from exc_principal

    # Verificar emergencia primero
    safety = resultado.get("safety") or {}
    if safety.get("is_emergency"):
        respuesta = _respuesta_emergencia()
        respuesta["model"] = {"provider": proveedor_nombre, "name": modelo_nombre}
        return respuesta

    # Adjuntar info del modelo
    resultado["model"] = {"provider": proveedor_nombre, "name": modelo_nombre}

    # Asegurar campos obligatorios con defaults
    resultado.setdefault("reply", "")
    resultado.setdefault("ready", False)
    resultado.setdefault("should_search", False)
    resultado.setdefault("detected", {})
    resultado.setdefault("missing_fields", [])
    resultado.setdefault("suggestions", [])
    resultado.setdefault("search_params", None)
    resultado.setdefault("safety", {"is_emergency": False, "message": None})

    return resultado
