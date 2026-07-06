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
  "mensaje": "Resumen breve de lo que el usuario dijo o síntoma principal identificado",
  "respuesta": [
    "Mensaje 1 para mostrar al usuario",
    "Mensaje 2 (por ejemplo, recomendaciones o preguntas adicionales)"
  ],
  "mongo": null,
  "sql": null,
  "filtros": {
    "especialidad": "slug_de_la_especialidad" | null,
    "ubicacion": "ciudad" | null,
    "otros": {
      "tipo_paciente": "nino" | "adulto" | "adolescente" | null,
      "atiende_ninos": boolean,
      "atiende_adultos": boolean,
      "atiende_adolescentes": boolean,
      "is_emergency": boolean
    }
  },
  "sugerencias": [
    "especialidad o síntoma sugerido",
    "otra opción"
  ],
  "historial_mensajes": null
}

Reglas:
1. Divide tu respuesta en varios mensajes cortos dentro del array `respuesta` para simular un chat natural.
2. Si el usuario menciona síntomas o molestias, sugiere una especialidad probable en `sugerencias`.
3. Si falta ciudad o ubicación, en uno de tus mensajes (`respuesta`) pregunta por ciudad, estado o código postal.
4. Si falta información, formula preguntas en `respuesta`.
5. Si el usuario ya indicó especialidad y ubicación (o las detectas con certeza), puedes colocar ["UBICACION_USUARIO"] en el campo `sql` si crees que hace falta confirmar la ubicación guardada, o simplemente pon los datos en `filtros`.
6. Si el usuario menciona una urgencia grave (ej: dolor de pecho, sangrado), `is_emergency` en `otros` debe ser true, y en `respuesta` recomienda acudir a urgencias.
7. No inventes ciudades ni especialistas que no estén claros.
8. Normaliza especialidades a slugs en `filtros.especialidad`:
   - dolor de muela, caries, endodoncia -> endodoncia o dentista
   - ansiedad, depresión, estrés emocional -> psicologo
   - embarazo, menstruación -> ginecologo
   - corazón, presión alta -> cardiologo
   - piel, acné -> dermatologo
   - huesos, articulaciones -> ortopedista
   - niños, pediatría -> pediatra
   - ojos, visión -> oftalmologo
   - oídos, nariz, garganta -> otorrinolaringologo
9. Si el usuario tiene una ubicación registrada y se proporciona en el contexto, úsala como sugerencia de ciudad.
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
        "mensaje": "Emergencia médica detectada",
        "respuesta": [
            "Lo que describes puede requerir atención inmediata.",
            "Te recomiendo acudir a urgencias o llamar a los servicios de emergencia de tu localidad lo antes posible.",
        ],
        "mongo": None,
        "sql": None,
        "filtros": {
            "especialidad": None,
            "ubicacion": None,
            "otros": {"is_emergency": True},
        },
        "sugerencias": [],
        "historial_mensajes": None,
    }


def _verificar_ollama_sync() -> tuple[bool, str]:
    """
    Verifica si Ollama está disponible de forma síncrona (para uso en threads).

    Retorna
    -------
    tuple[bool, str]
        (disponible, modelo_a_usar) — el primer modelo instalado o vacío.
    """
    import httpx as _httpx  # pyrefly: ignore [missing-import]
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_CHAT_MODEL", "")
    try:
        with _httpx.Client(timeout=3.0) as c:
            resp = c.get(f"{ollama_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            modelos = [m["name"] for m in data.get("models", [])]
            if not modelos:
                return False, ""
            # Usar el modelo configurado o el primero disponible
            modelo_elegido = ollama_model if ollama_model in modelos else modelos[0]
            return True, modelo_elegido
    except Exception:
        return False, ""


def _construir_instancia_modelo(provider: str):
    """
    Instancia el modelo LLM según el proveedor solicitado.

    Prioridad cuando provider='auto':
      1. Ollama (local, sin costo) — si está disponible
      2. Gemini — si hay GEMINI_API_KEY
      3. Groq  — si hay GROQ_API_KEY

    Parámetros
    ----------
    provider : str
        'groq', 'gemini', 'ollama' o 'auto'.

    Retorna
    -------
    tuple[BaseModelo, str, str]
        Tupla de (instancia_modelo, nombre_proveedor, nombre_modelo).
    """
    if provider == "auto":
        # 1. Intentar Ollama primero
        ollama_ok, ollama_model = _verificar_ollama_sync()
        if ollama_ok:
            from app.nlp.modelos.ollama_modelo import OllamaModelo  # pyrefly: ignore
            m = OllamaModelo()
            if ollama_model:
                m._modelo = ollama_model
            return m, "ollama", ollama_model

        # 2. Gemini como fallback
        if os.getenv("GEMINI_API_KEY", "").strip():
            m = GeminiModelo()
            return m, "gemini", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # 3. Groq como último recurso
        m = GroqModelo()
        return m, "groq", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    if provider == "ollama":
        from app.nlp.modelos.ollama_modelo import OllamaModelo  # pyrefly: ignore
        ollama_model = os.getenv("OLLAMA_CHAT_MODEL", "")
        m = OllamaModelo()
        if ollama_model:
            m._modelo = ollama_model
        return m, "ollama", ollama_model

    if provider == "gemini":
        m = GeminiModelo()
        return m, "gemini", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # groq (u otro valor desconocido)
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

        # Fallback encadenado: ollama → gemini → groq
        if proveedor_nombre in ("ollama", "groq"):
            # Intentar Gemini como segundo paso
            if os.getenv("GEMINI_API_KEY", "").strip():
                try:
                    fallback = GeminiModelo()
                    respuesta_raw = await asyncio.to_thread(
                        fallback.analizar, PROMPT_SISTEMA, prompt_usuario
                    )
                    resultado = fallback.parsear_respuesta(respuesta_raw)
                    proveedor_nombre = "gemini"
                    modelo_nombre = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                except Exception as exc_fallback:
                    logger.error("[ChatService] Fallback Gemini también falló: %s", exc_fallback)
                    raise RuntimeError(
                        "El servicio de interpretación no está disponible."
                    ) from exc_fallback
            else:
                # Sin clave Gemini, intentar Groq como último recurso
                try:
                    fallback_groq = GroqModelo()
                    respuesta_raw = await asyncio.to_thread(
                        fallback_groq.analizar, PROMPT_SISTEMA, prompt_usuario
                    )
                    resultado = fallback_groq.parsear_respuesta(respuesta_raw)
                    proveedor_nombre = "groq"
                    modelo_nombre = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
                except Exception as exc_groq:
                    logger.error("[ChatService] Fallback Groq también falló: %s", exc_groq)
                    raise RuntimeError(
                        "El servicio de interpretación no está disponible."
                    ) from exc_groq
        else:
            raise RuntimeError(
                "El servicio de interpretación no está disponible."
            ) from exc_principal

    # Verificar emergencia primero
    filtros = resultado.get("filtros", {})
    otros = filtros.get("otros", {}) if isinstance(filtros, dict) else {}

    if isinstance(otros, dict) and otros.get("is_emergency"):
        respuesta = _respuesta_emergencia()
        respuesta["model"] = {"provider": proveedor_nombre, "name": modelo_nombre}
        return respuesta

    # Adjuntar info del modelo
    resultado["model"] = {"provider": proveedor_nombre, "name": modelo_nombre}

    # Asegurar campos obligatorios con defaults
    resultado.setdefault("mensaje", consulta)
    resultado.setdefault("respuesta", ["Lo siento, no pude entender tu mensaje."])
    if not isinstance(resultado["respuesta"], list):
        resultado["respuesta"] = [str(resultado["respuesta"])]

    resultado.setdefault("mongo", None)
    resultado.setdefault("sql", None)
    resultado.setdefault(
        "filtros", {"especialidad": None, "ubicacion": None, "otros": None}
    )
    resultado.setdefault("sugerencias", [])
    resultado.setdefault("historial_mensajes", None)

    # Añadir flags calculados de retrocompatibilidad
    f = resultado.get("filtros") or {}
    esp = f.get("especialidad")
    ubi = f.get("ubicacion")

    # Ready si tiene especialidad y ubicación
    resultado["ready"] = bool(esp and ubi)

    return resultado
