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

import google.generativeai as genai

from app.nlp.modelos.base_modelo import BaseModelo

logger = logging.getLogger(__name__)


class GeminiModelo(BaseModelo):
    """Implementación del modelo Gemini para análisis de opiniones."""

    def __init__(self):
        """Inicializa el cliente Gemini con la API key del entorno."""
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        self._modelo_nombre = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        genai.configure(api_key=self._api_key)

        self._config = genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=1500,
        )
        self._modelo = genai.GenerativeModel(
            model_name=self._modelo_nombre,
            generation_config=self._config,
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
            respuesta = self._modelo.generate_content(prompt_combinado)
            return respuesta.text or ""

        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "rate" in error_str or "429" in error_str:
                logger.warning(
                    "[Gemini] Rate limit alcanzado — esperando 60 segundos..."
                )
                time.sleep(60)

                respuesta = self._modelo.generate_content(prompt_combinado)
                return respuesta.text or ""
            raise

    def nombre_modelo(self) -> str:
        """Retorna el identificador del modelo para logging."""
        return f"gemini ({self._modelo_nombre})"
