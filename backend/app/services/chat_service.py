"""
Servicio de interpretación médica mediante LLM para el chatbot.

Convierte mensajes en lenguaje natural del usuario en filtros de búsqueda
estructurados para el endpoint GET /especialistas.

Prioridad de proveedores:
    1. LM Studio (local — primario)
    2. Ollama    (local — secundario)
    3. Externo   (Gemini / Groq — solo si el usuario proporcionó token)

El prompt del sistema está en inglés para mejorar la comprensión del LLM.
La respuesta se genera en español o inglés según el idioma detectado en la consulta.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Optional

from app.nlp.modelos.gemini_modelo import GeminiModelo
from app.nlp.modelos.groq_modelo import GroqModelo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt del sistema — en inglés para mayor comprensión en modelos pequeños.
# La instrucción de idioma de salida está embebida dentro del prompt.
# ---------------------------------------------------------------------------

PROMPT_SISTEMA = """You are a medical search assistant for a specialist finder platform in Mexico.

IMPORTANT RULES:
1. You are NOT a doctor. You do NOT diagnose. You do NOT prescribe treatment.
   You only help users FIND the right type of specialist.
2. If the user writes in English, respond in English. Otherwise, respond in Spanish.
3. Never say things like "You should go to a doctor" or "I recommend you see a specialist" as a final answer.
   Instead, ask clarifying questions and guide the user to select a specialist type on the platform.
4. Always respond with VALID JSON only. No Markdown, no text outside the JSON.

OUTPUT FORMAT — use real null (JSON null, not the string "null") when a value is unknown:
{
  "mensaje": "INTERNAL ONLY — one-sentence summary. Never shown to user.",
  "respuesta": [
    "Warm first message acknowledging what the user said",
    "Follow-up question for missing info"
  ],
  "mongo": null,
  "sql": null,
  "filtros": {
    "especialidad": null,
    "ubicacion": null,
    "otros": {
      "tipo_paciente": null,
      "atiende_ninos": false,
      "atiende_adultos": true,
      "atiende_adolescentes": false,
      "is_emergency": false
    }
  },
  "sugerencias": [],
  "historial_mensajes": null
}

CRITICAL JSON RULES:
- NEVER write the literal strings "city_name_or_null", "specialty_slug_or_null", "null" as values.
  If a value is unknown, write JSON null (no quotes): null
- "filtros.ubicacion" must be null until the user explicitly states a city, area, or postal code.
- "filtros.especialidad" must be null until the user clearly mentions a specialty or symptom.
- NEVER put suggestion text inside "respuesta". Suggestions belong ONLY in the "sugerencias" array.
- "respuesta" must contain ONLY conversational messages — no lists, no "Sugerencias:", no slugs.

SPECIALIST SLUG MAPPING (use these exact slugs in filtros.especialidad):
- tooth pain, cavity, root canal, braces → dentista-odontologo
- anxiety, depression, stress, mental health → psicologo
- pregnancy, menstruation, gynecology → ginecologo
- heart, blood pressure, cardiology → cardiologo
- skin, acne, rash, dermatology → dermatologo
- bones, joints, fractures → ortopedista
- children, pediatrics → pediatra
- eyes, vision → oftalmologo
- ear, nose, throat → otorrinolaringologo
- diabetes, hormones, thyroid → endocrinologo
- stomach, digestion, liver → gastroenterologo
- lungs, breathing, asthma → neumologo
- kidneys, urine → nefrologo
- brain, neurology, headaches → neurologo
- nutrition, obesity → nutriologo
- allergy, immunology → alergologo

CONVERSATIONAL TONE — CRITICAL:
The `respuesta` messages are what the user SEES in the chat. They must sound warm and human.
The `mensaje` field is for internal logging only and is NEVER shown.

NEVER write dry technical confirmations as the first respuesta:
  BAD: "La especialidad de cardiología está disponible."
  BAD: "Se detectó la especialidad: cardílogo."
  BAD: "Hemos identificado la especialidad requerida."

ALWAYS start with a warm, natural acknowledgment:
  GOOD: "¡Claro! Tenemos cardíologos disponibles en varias ciudades."
  GOOD: "Perfecto, puedo ayudarte a encontrar un cardílogo."
  GOOD: "Entendido, te ayudo a encontrar un especialista en cardiología."

Then ask for the missing info in the second message:
  GOOD: "¿En qué ciudad o estado te encuentras?"
  GOOD: "¿Me dices tu ciudad o código postal para buscar cerca de ti?"

BEHAVIOR RULES:
- Use exactly 2 short conversational messages in `respuesta` (max 3). No lists, no slugs, no "Sugerencias:".
- If specialty is known but location is missing: acknowledge the specialty warmly, then ask for location.
- If BOTH specialty AND location are known: confirm both and tell the user you found results.
  DO NOT ask for location again when you already have it in filtros.ubicacion.
- If the user describes an emergency (chest pain, severe bleeding, loss of consciousness), set is_emergency=true.
- Do NOT invent cities or specialties. Only use what the user has explicitly stated.
- `sugerencias` must contain 2-3 alternative specialty slugs (never names, never in `respuesta`).
- Mexican postal codes have 5 digits; put them as-is in ubicacion, the backend resolves them.

READY STATE LOGIC:
- Set ready:true ONLY when BOTH filtros.especialidad AND filtros.ubicacion are real non-null values.
- If location is null or unknown, ready must be false and you must ask for location.
- When ready is true, the second respuesta message should confirm the search, not ask for more info.
  GOOD when ready: "¡Listo! Encontré especialistas en [ciudad], haz clic en el botón para verlos."
"""


def _detectar_idioma_ingles(texto: str) -> bool:
    """
    Detecta heurísticamente si el texto está mayormente en inglés.

    Busca palabras comunes en inglés que raramente aparecen en español.

    Parámetros
    ----------
    texto : str
        Texto del usuario a analizar.

    Retorna
    -------
    bool
        True si el texto parece estar en inglés.

    Ejemplo
    -------
    >>> _detectar_idioma_ingles("I have a high fever")
    True
    >>> _detectar_idioma_ingles("Tengo fiebre alta")
    False
    """
    palabras_ingles = {
        "i",
        "i'm",
        "i've",
        "i have",
        "my",
        "me",
        "the",
        "and",
        "or",
        "but",
        "is",
        "are",
        "was",
        "have",
        "has",
        "with",
        "for",
        "that",
        "this",
        "very",
        "sick",
        "pain",
        "hurt",
        "feel",
        "need",
        "help",
        "doctor",
        "tooth",
        "teeth",
        "fever",
        "cold",
        "cough",
        "stomach",
        "head",
    }
    tokens = set(re.findall(r"\b\w+\b", texto.lower()))
    coincidencias = tokens.intersection(palabras_ingles)
    return len(coincidencias) >= 2


def _construir_prompt_usuario(
    messages: list[dict],
    consulta: str,
    ubicacion_usuario: Optional[str] = None,
) -> str:
    """
    Construye el prompt de usuario con historial y contexto de ubicación.

    Parámetros
    ----------
    messages : list[dict]
        Historial de mensajes [{role, content}, ...].
    consulta : str
        Último mensaje del usuario.
    ubicacion_usuario : str, opcional
        Ciudad registrada del usuario para usar como contexto de ubicación.

    Retorna
    -------
    str
        Prompt de usuario completo para enviar al LLM.
    """
    partes: list[str] = []

    if ubicacion_usuario:
        partes.append(f"[Context: The user has registered city '{ubicacion_usuario}']")

    idioma_ingles = _detectar_idioma_ingles(consulta)
    if idioma_ingles:
        partes.append(
            "[Language note: The user is writing in English. Respond in English.]"
        )
    else:
        partes.append(
            "[Language note: The user is writing in Spanish. Respond in Spanish.]"
        )

    if messages:
        historial = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in messages[-6:]  # Solo últimos 6 mensajes para no exceder tokens
        )
        partes.append(f"Conversation history:\n{historial}")

    partes.append(f"Latest user message: {consulta}")
    return "\n\n".join(partes)


def _respuesta_emergencia() -> dict:
    """Retorna respuesta estándar para emergencia médica detectada."""
    return {
        "mensaje": "Emergencia médica detectada",
        "respuesta": [
            "Lo que describes puede requerir atención inmediata.",
            "Por favor, acude a urgencias o llama a los servicios de emergencia de tu localidad.",
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


# ---------------------------------------------------------------------------
# Verificación de disponibilidad de proveedores locales
# ---------------------------------------------------------------------------


def _verificar_lmstudio_sync() -> bool:
    """
    Verifica si LM Studio está disponible de forma síncrona.

    Retorna
    -------
    bool
        True si el servidor LM Studio responde correctamente.
    """
    import httpx as _httpx  # pyrefly: ignore [missing-import]

    base_url = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234").rstrip("/")
    try:
        with _httpx.Client(timeout=3.0) as cliente:
            resp = cliente.get(f"{base_url}/api/v0/models")
            resp.raise_for_status()
            return True
    except Exception:
        return False


def _verificar_ollama_sync() -> tuple[bool, str]:
    """
    Verifica si Ollama está disponible de forma síncrona.

    Retorna
    -------
    tuple[bool, str]
        (disponible, modelo_a_usar) — el primer modelo instalado o vacío.
    """
    import httpx as _httpx  # pyrefly: ignore [missing-import]

    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "")
    try:
        with _httpx.Client(timeout=3.0) as cliente:
            resp = cliente.get(f"{ollama_url}/api/tags")
            resp.raise_for_status()
            datos = resp.json()
            modelos = [m["name"] for m in datos.get("models", [])]
            if not modelos:
                return False, ""
            modelo_elegido = ollama_model if ollama_model in modelos else modelos[0]
            return True, modelo_elegido
    except Exception:
        return False, ""


# ---------------------------------------------------------------------------
# Construcción de instancias de modelo según prioridad
# ---------------------------------------------------------------------------


def _construir_instancia_modelo(
    provider: str,
    token_externo: Optional[str] = None,
    proveedor_externo: Optional[str] = None,
):
    """
    Instancia el modelo LLM según prioridad y disponibilidad.

    Prioridad cuando provider='auto':
        1. LM Studio (local — primario)
        2. Ollama    (local — secundario)
        3. Externo   (Gemini/Groq — solo si token_externo está presente)

    Parámetros
    ----------
    provider : str
        'lmstudio', 'ollama', 'gemini', 'groq' o 'auto'.
    token_externo : str, opcional
        API key proporcionada por el usuario para proveedor externo.
    proveedor_externo : str, opcional
        Nombre del proveedor externo ('gemini' o 'groq').

    Retorna
    -------
    tuple[BaseModelo, str, str]
        Tupla de (instancia_modelo, nombre_proveedor, nombre_modelo).

    Lanza
    -----
    RuntimeError
        Si ningún proveedor está disponible.
    """
    from app.nlp.modelos.lmstudio_modelo import LMStudioModelo
    from app.nlp.modelos.ollama_modelo import OllamaModelo  # pyrefly: ignore

    if provider == "lmstudio":
        modelo = LMStudioModelo()
        return modelo, "lmstudio", modelo._modelo

    if provider == "ollama":
        ollama_model = os.getenv("OLLAMA_MODEL", "")
        modelo = OllamaModelo()
        if ollama_model:
            modelo._modelo = ollama_model
        return modelo, "ollama", ollama_model

    if provider in ("gemini", "groq"):
        clave = token_externo or os.getenv(
            "GEMINI_API_KEY" if provider == "gemini" else "GROQ_API_KEY", ""
        )
        if provider == "gemini":
            modelo = GeminiModelo()
            return modelo, "gemini", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        modelo = GroqModelo()
        return modelo, "groq", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # === AUTO: prioridad LMStudio → Ollama → externo ===
    if _verificar_lmstudio_sync():
        logger.info(
            "[ChatService] LM Studio disponible — usando como proveedor primario"
        )
        modelo = LMStudioModelo()
        return modelo, "lmstudio", modelo._modelo

    ollama_ok, ollama_model = _verificar_ollama_sync()
    if ollama_ok:
        logger.info(
            "[ChatService] Ollama disponible — usando como proveedor secundario"
        )
        modelo = OllamaModelo()
        if ollama_model:
            modelo._modelo = ollama_model
        return modelo, "ollama", ollama_model

    # Fallback externo — solo si hay token disponible
    api_key_gemini = token_externo or os.getenv("GEMINI_API_KEY", "").strip()
    if api_key_gemini and (proveedor_externo or "gemini") == "gemini":
        logger.info("[ChatService] Usando Gemini como proveedor externo de fallback")
        modelo = GeminiModelo()
        return modelo, "gemini", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    api_key_groq = token_externo or os.getenv("GROQ_API_KEY", "").strip()
    if api_key_groq:
        logger.info("[ChatService] Usando Groq como proveedor externo de fallback")
        modelo = GroqModelo()
        return modelo, "groq", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    raise RuntimeError("NO_LOCAL_LLM_AVAILABLE")


# ---------------------------------------------------------------------------
# Validación post-LLM de especialidad y ubicación
# ---------------------------------------------------------------------------


async def _validar_y_corregir_filtros(filtros: dict) -> dict:
    """
    Valida la especialidad y ubicación detectadas contra la base de datos MongoDB.

    Si la especialidad no existe exactamente, busca variantes por prefijo.
    Si la ubicación es un código postal, la resuelve a ciudad.

    Parámetros
    ----------
    filtros : dict
        Filtros detectados por el LLM {especialidad, ubicacion, otros}.

    Retorna
    -------
    dict
        Filtros con especialidad y ubicación corregidos o anulados si no existen.
    """
    from app.services.catalogo_service import (
        es_codigo_postal,
        resolver_codigo_postal,
        validar_ciudad,
        validar_especialidad,
    )

    filtros_corregidos = dict(filtros)
    slug_raw = filtros.get("especialidad")
    ubicacion_raw = filtros.get("ubicacion")

    # Validar especialidad
    if slug_raw:
        slug_validado = await validar_especialidad(slug_raw)
        if slug_validado:
            filtros_corregidos["especialidad"] = slug_validado
            logger.info(
                "[ChatService] Especialidad '%s' → '%s' (validada)",
                slug_raw,
                slug_validado,
            )
        else:
            logger.warning(
                "[ChatService] Especialidad '%s' no encontrada — se anula del filtro",
                slug_raw,
            )
            filtros_corregidos["especialidad"] = None

    # Validar ubicación / código postal
    if ubicacion_raw:
        if es_codigo_postal(ubicacion_raw):
            ciudad_resuelta = resolver_codigo_postal(ubicacion_raw)
            if ciudad_resuelta:
                logger.info(
                    "[ChatService] CP '%s' resuelto a '%s'",
                    ubicacion_raw,
                    ciudad_resuelta,
                )
                filtros_corregidos["ubicacion"] = ciudad_resuelta
            else:
                logger.warning(
                    "[ChatService] CP '%s' no resuelto — manteniendo valor original",
                    ubicacion_raw,
                )
        else:
            ciudad_validada = await validar_ciudad(ubicacion_raw)
            if ciudad_validada:
                filtros_corregidos["ubicacion"] = ciudad_validada
            else:
                # No anulamos la ciudad — puede ser válida aunque no esté en nuestra tabla
                logger.info(
                    "[ChatService] Ciudad '%s' no encontrada en catálogo, manteniendo valor",
                    ubicacion_raw,
                )

    return filtros_corregidos


# ---------------------------------------------------------------------------
# Función principal de interpretación
# ---------------------------------------------------------------------------


async def interpretar_consulta_medica(
    consulta: str,
    messages: list[dict],
    provider: str = "auto",
    ubicacion_usuario: Optional[str] = None,
    token_externo: Optional[str] = None,
    proveedor_externo: Optional[str] = None,
) -> dict[str, Any]:
    """
    Interpreta una consulta médica en lenguaje natural y extrae filtros de búsqueda.

    Flujo:
        1. Construye el prompt de usuario con historial y contexto.
        2. Selecciona proveedor LLM según prioridad (LMStudio → Ollama → externo).
        3. Llama al LLM de forma asíncrona.
        4. Valida la especialidad y ubicación contra MongoDB.
        5. Retorna respuesta normalizada.

    Parámetros
    ----------
    consulta : str
        Texto del usuario a interpretar.
    messages : list[dict]
        Historial de la conversación [{role, content}].
    provider : str
        Proveedor LLM: 'lmstudio', 'ollama', 'gemini', 'groq' o 'auto'.
    ubicacion_usuario : str, opcional
        Ciudad del usuario registrada en su perfil.
    token_externo : str, opcional
        API key del usuario para proveedor externo.
    proveedor_externo : str, opcional
        Nombre del proveedor externo ('gemini' o 'groq').

    Retorna
    -------
    dict
        Respuesta normalizada con: mensaje, respuesta, filtros, ready, model, etc.

    Lanza
    -----
    RuntimeError
        Con el código "NO_LOCAL_LLM_AVAILABLE" si no hay LLM local ni token externo.
        Con "SERVICIO_NO_DISPONIBLE" si todos los proveedores fallan.
    """
    prompt_usuario = _construir_prompt_usuario(messages, consulta, ubicacion_usuario)

    try:
        modelo, proveedor_nombre, modelo_nombre = _construir_instancia_modelo(
            provider, token_externo, proveedor_externo
        )
    except RuntimeError as exc:
        raise exc  # Propagar NO_LOCAL_LLM_AVAILABLE tal cual

    try:
        respuesta_raw = await asyncio.to_thread(
            modelo.analizar, PROMPT_SISTEMA, prompt_usuario
        )
        resultado = modelo.parsear_respuesta(respuesta_raw)
    except Exception as exc_principal:
        logger.warning(
            "[ChatService] Error con proveedor '%s': %s",
            proveedor_nombre,
            exc_principal,
        )

        # Fallback encadenado: LMStudio → Ollama → Gemini → Groq
        from app.nlp.modelos.lmstudio_modelo import LMStudioModelo
        from app.nlp.modelos.ollama_modelo import OllamaModelo  # pyrefly: ignore

        fallback_exitoso = False

        if proveedor_nombre != "lmstudio" and _verificar_lmstudio_sync():
            try:
                fb = LMStudioModelo()
                respuesta_raw = await asyncio.to_thread(
                    fb.analizar, PROMPT_SISTEMA, prompt_usuario
                )
                resultado = fb.parsear_respuesta(respuesta_raw)
                proveedor_nombre, modelo_nombre = "lmstudio", fb._modelo
                fallback_exitoso = True
            except Exception as exc_fb:
                logger.warning("[ChatService] Fallback LMStudio falló: %s", exc_fb)

        if not fallback_exitoso and proveedor_nombre != "ollama":
            ollama_ok, ollama_model = _verificar_ollama_sync()
            if ollama_ok:
                try:
                    fb_ollama = OllamaModelo()
                    if ollama_model:
                        fb_ollama._modelo = ollama_model
                    respuesta_raw = await asyncio.to_thread(
                        fb_ollama.analizar, PROMPT_SISTEMA, prompt_usuario
                    )
                    resultado = fb_ollama.parsear_respuesta(respuesta_raw)
                    proveedor_nombre, modelo_nombre = "ollama", ollama_model
                    fallback_exitoso = True
                except Exception as exc_ollama:
                    logger.warning(
                        "[ChatService] Fallback Ollama falló: %s", exc_ollama
                    )

        if not fallback_exitoso:
            api_key_gemini = token_externo or os.getenv("GEMINI_API_KEY", "").strip()
            if api_key_gemini:
                try:
                    fb_gem = GeminiModelo()
                    respuesta_raw = await asyncio.to_thread(
                        fb_gem.analizar, PROMPT_SISTEMA, prompt_usuario
                    )
                    resultado = fb_gem.parsear_respuesta(respuesta_raw)
                    proveedor_nombre = "gemini"
                    modelo_nombre = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                    fallback_exitoso = True
                except Exception as exc_gem:
                    logger.error("[ChatService] Fallback Gemini falló: %s", exc_gem)

        if not fallback_exitoso:
            raise RuntimeError("SERVICIO_NO_DISPONIBLE") from exc_principal

    # Verificar emergencia primero
    filtros = resultado.get("filtros", {})
    otros = filtros.get("otros", {}) if isinstance(filtros, dict) else {}

    if isinstance(otros, dict) and otros.get("is_emergency"):
        respuesta = _respuesta_emergencia()
        respuesta["model"] = {"provider": proveedor_nombre, "name": modelo_nombre}
        return respuesta

    # Validar especialidad y ubicación contra MongoDB
    if isinstance(filtros, dict):
        filtros_validados = await _validar_y_corregir_filtros(filtros)
        resultado["filtros"] = filtros_validados
    else:
        filtros_validados = {}

    # Adjuntar info del modelo
    resultado["model"] = {"provider": proveedor_nombre, "name": modelo_nombre}

    # Asegurar campos obligatorios con defaults
    resultado.setdefault("mensaje", consulta)
    resultado.setdefault("respuesta", ["Lo siento, no pude entender tu mensaje."])
    if not isinstance(resultado["respuesta"], list):
        resultado["respuesta"] = [str(resultado["respuesta"])]

    # Sanitizar respuesta: quitar mensajes de ruido que el LLM pequeño inserta
    # erróneamente (listas de sugerencias, slugs de especialidades, etc.)
    import re as _re
    _PATRON_SLUG = _re.compile(r"\b[a-z]+-[a-z]+\b")  # ej. "dentista-odontologo"
    _PREFIJOS_RUIDO = ("sugerencias:", "slug:", "especialidad:")

    def _es_ruido(msg: str) -> bool:
        m = msg.strip().lower()
        if any(m.startswith(p) for p in _PREFIJOS_RUIDO):
            return True
        # Mensaje que es SOLO un slug o lista de slugs (sin texto conversacional)
        if _PATRON_SLUG.search(m) and len(m.split()) <= 6:
            return True
        return False

    resultado["respuesta"] = [
        msg for msg in resultado["respuesta"]
        if isinstance(msg, str) and msg.strip() and not _es_ruido(msg)
    ] or ["Lo siento, no pude procesar tu mensaje."]


    resultado.setdefault("mongo", None)
    resultado.setdefault("sql", None)
    resultado.setdefault(
        "filtros", {"especialidad": None, "ubicacion": None, "otros": None}
    )
    resultado.setdefault("sugerencias", [])
    resultado.setdefault("historial_mensajes", None)

    # Valores que indican que el LLM copió el placeholder en lugar de usar null.
    # Si alguno aparece como valor real, se trata como ausente.
    _PLACEHOLDERS = {
        "city_name_or_null", "specialty_slug_or_null", "null", "none",
        "ciudad", "city", "ubicacion", "location", "especialidad", "specialty",
    }

    # Calcular ready: necesita especialidad y ubicación reales (no placeholders)
    f = resultado.get("filtros") or {}
    esp = f.get("especialidad")
    ubi = f.get("ubicacion")

    if isinstance(esp, str) and esp.strip().lower() in _PLACEHOLDERS:
        f["especialidad"] = None
        esp = None
        logger.warning("[ChatService] especialidad era un placeholder, anulada")

    if isinstance(ubi, str) and ubi.strip().lower() in _PLACEHOLDERS:
        f["ubicacion"] = None
        ubi = None
        logger.warning("[ChatService] ubicacion era un placeholder, anulada")

    resultado["ready"] = bool(esp and ubi)

    return resultado


# ---------------------------------------------------------------------------
# Verificación de estado de proveedores (para el endpoint de healthcheck)
# ---------------------------------------------------------------------------


async def verificar_disponibilidad_proveedores() -> dict[str, Any]:
    """
    Verifica qué proveedores LLM están disponibles en este momento.

    Retorna
    -------
    dict
        Estado de cada proveedor: {lmstudio, ollama, externo_disponible}.

    Ejemplo
    -------
    >>> await verificar_disponibilidad_proveedores()
    {"lmstudio": True, "ollama": False, "externo_disponible": True}
    """
    lmstudio_ok, ollama_info = await asyncio.gather(
        asyncio.to_thread(_verificar_lmstudio_sync),
        asyncio.to_thread(_verificar_ollama_sync),
    )
    ollama_ok, ollama_modelo = ollama_info

    externo_disponible = bool(
        os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GROQ_API_KEY", "").strip()
    )

    return {
        "lmstudio": lmstudio_ok,
        "ollama": ollama_ok,
        "ollama_modelo": ollama_modelo if ollama_ok else None,
        "externo_disponible": externo_disponible,
        "requiere_token": not lmstudio_ok and not ollama_ok and not externo_disponible,
    }
