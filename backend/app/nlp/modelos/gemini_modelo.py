"""
Implementación del modelo Gemini.
"""

import logging
import os
import time

from google import genai
from google.genai import types

from app.nlp.modelos.base_modelo import (
    BaseModelo,
    ErrorProveedorFatal,
    es_error_fatal_proveedor,
    es_rate_limit_recuperable,
)

logger = logging.getLogger(__name__)


class GeminiModelo(BaseModelo):
    """Implementación del modelo Gemini para análisis de opiniones."""

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        self._modelo_nombre = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        self._cliente = genai.Client(api_key=self._api_key)
        self._config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8000,
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            ],
        )

    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        prompt_combinado = (
            f"INSTRUCCIONES DEL SISTEMA:\n{prompt_sistema}\n\n"
            f"DATOS A ANALIZAR:\n{prompt_usuario}"
        )
        try:
            self._registrar_request_remoto()
            respuesta = self._cliente.models.generate_content(
                model=self._modelo_nombre,
                contents=prompt_combinado,
                config=self._config,
            )
            if not respuesta.text:
                raise ValueError(
                    f"Gemini bloqueó la respuesta o devolvió vacío. "
                    f"finish_reason: {respuesta.candidates[0].finish_reason}"
                )
            return respuesta.text
        except Exception as exc:
            if es_error_fatal_proveedor(exc):
                raise ErrorProveedorFatal(str(exc), proveedor="gemini") from exc
            if es_rate_limit_recuperable(exc):
                logger.warning("[Gemini] Rate limit recuperable — esperando 60 segundos...")
                time.sleep(60)
                self._registrar_request_remoto()
                respuesta = self._cliente.models.generate_content(
                    model=self._modelo_nombre,
                    contents=prompt_combinado,
                    config=self._config,
                )
                return respuesta.text or ""
            raise

    def nombre_modelo(self) -> str:
        return f"gemini ({self._modelo_nombre})"
