"""
Implementación del modelo MiniMax.

Usa el cliente OpenAI compatible con base_url de MiniMax.
El header de autenticación requiere Authorization: Bearer {API_KEY}.
Temperature=0.1, max_tokens=800.

Variables de entorno requeridas:
    - MINIMAX_API_KEY: API key de MiniMax
    - MINIMAX_GROUP_ID: Group ID de MiniMax
    - MINIMAX_MODEL: Modelo a usar (default: abab6.5s-chat)
"""

import os
import time
import logging

from openai import OpenAI, RateLimitError

from app.nlp.modelos.base_modelo import BaseModelo

logger = logging.getLogger(__name__)


class MiniMaxModelo(BaseModelo):
    """Implementación del modelo MiniMax para análisis de opiniones."""

    def __init__(self):
        """Inicializa el cliente OpenAI apuntando a la API de MiniMax."""
        self._api_key = os.getenv("MINIMAX_API_KEY", "")
        self._group_id = os.getenv("MINIMAX_GROUP_ID", "")
        self._modelo = os.getenv("MINIMAX_MODEL", "abab6.5s-chat")

        self._cliente = OpenAI(
            api_key=self._api_key,
            base_url="https://api.minimax.chat/v1",
        )

    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        """
        Envía los prompts a MiniMax y retorna la respuesta.

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
                max_tokens=1500,
            )
            return respuesta.choices[0].message.content or ""

        except RateLimitError:
            logger.warning(
                "[MiniMax] Rate limit alcanzado — esperando 60 segundos..."
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
        return f"minimax ({self._modelo})"
