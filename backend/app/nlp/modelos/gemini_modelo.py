"""
Implementación del modelo Gemini 1.5 Flash.

Usa la librería google-generativeai. Combina prompt sistema + usuario
en un solo mensaje (la API básica de Gemini no tiene rol system separado).
Temperature=0.1, max_output_tokens=800.

Variables de entorno requeridas:
    - GEMINI_API_KEY: API key de Gemini (obtener en https://aistudio.google.com/app/apikey)
    - GEMINI_MODEL: Modelo a usar (default: gemini-1.5-flash)
"""

import os
import time
import logging

from google import genai
from google.genai import types
from app.nlp.modelos.base_modelo import BaseModelo

logger = logging.getLogger(__name__)


class GeminiModelo(BaseModelo):
    """Implementación del modelo Gemini para análisis de opiniones."""

    def __init__(self):
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        self._modelo_nombre = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        self._cliente = genai.Client(api_key=self._api_key)
        self._config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8000,
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="BLOCK_NONE",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="BLOCK_NONE",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="BLOCK_NONE",
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="BLOCK_NONE",
                ),
            ],
        )

    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        """
        Envía los prompts a Gemini y retorna la respuesta.

        Combina prompt_sistema y prompt_usuario en un solo mensaje
        ya que la API básica de Gemini no separa el rol system.

        Parámetros
        ----------
        prompt_sistema : str
            Prompt del sistema con instrucciones del modelo.
        prompt_usuario : str
            Prompt del usuario con datos del especialista.

        Retorna
        -------
        str
            Respuesta cruda del modelo.
        """
        prompt_combinado = (
            f"INSTRUCCIONES DEL SISTEMA:\n{prompt_sistema}\n\n"
            f"DATOS A ANALIZAR:\n{prompt_usuario}"
        )
        try:
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
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate" in error_str or "429" in error_str:
                logger.warning("[Gemini] Rate limit — esperando 60 segundos...")
                time.sleep(60)
                respuesta = self._cliente.models.generate_content(
                    model=self._modelo_nombre,
                    contents=prompt_combinado,
                    config=self._config,
                )
                return respuesta.text or ""
            raise

    def nombre_modelo(self) -> str:
        """Retorna el identificador del modelo para logging."""
        return f"gemini ({self._modelo_nombre})"
