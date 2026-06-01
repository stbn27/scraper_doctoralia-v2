"""
Implementación del modelo DeepSeek API.

Usa el cliente OpenAI compatible con base_url de DeepSeek.
Temperature=0.1, max_tokens=800.

Variables de entorno requeridas:
    - DEEPSEEK_API_KEY: API key de DeepSeek
    - DEEPSEEK_MODEL_NLP: Modelo a usar (default: deepseek-chat)
    - DEEPSEEK_BASE_URL_NLP: URL base de la API (default: https://api.deepseek.com)
"""

import os
import time
import logging

from openai import OpenAI, RateLimitError

from app.nlp.modelos.base_modelo import BaseModelo

logger = logging.getLogger(__name__)


class DeepSeekModelo(BaseModelo):
    """Implementación del modelo DeepSeek para análisis de opiniones."""

    def __init__(self):
        """Inicializa el cliente OpenAI apuntando a la API de DeepSeek."""
        self._api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self._modelo = os.getenv("DEEPSEEK_MODEL_NLP", "deepseek-chat")
        self._base_url = os.getenv(
            "DEEPSEEK_BASE_URL_NLP", "https://api.deepseek.com"
        )
        self._cliente = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )

    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        """
        Envía los prompts a DeepSeek y retorna la respuesta.

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
        mensajes = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario},
        ]

        try:
            respuesta = self._cliente.chat.completions.create(
                model=self._modelo,
                messages=mensajes,
                temperature=0.1,
                max_tokens=800,
            )
            return respuesta.choices[0].message.content or ""

        except RateLimitError:
            logger.warning(
                "[DeepSeek] Rate limit alcanzado — esperando 60 segundos..."
            )
            time.sleep(60)

            respuesta = self._cliente.chat.completions.create(
                model=self._modelo,
                messages=mensajes,
                temperature=0.1,
                max_tokens=1500,
            )
            return respuesta.choices[0].message.content or ""

    def nombre_modelo(self) -> str:
        """Retorna el identificador del modelo para logging."""
        return f"deepseek ({self._modelo})"
