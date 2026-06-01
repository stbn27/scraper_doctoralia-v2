"""
Implementación del modelo Groq (Llama 3.3 70B).

Usa la librería oficial `groq` para comunicarse con la API.
Temperature=0.1 para respuestas consistentes, max_tokens=800.
Incluye manejo de RateLimitError con espera de 60 segundos.

Variables de entorno requeridas:
    - GROQ_API_KEY: API key de Groq (obtener en https://console.groq.com/keys)
    - GROQ_MODEL: Modelo a usar (default: llama-3.3-70b-versatile)
"""

import os
import time
import logging

from groq import Groq, RateLimitError

from app.nlp.modelos.base_modelo import BaseModelo

logger = logging.getLogger(__name__)


class GroqModelo(BaseModelo):
    """Implementación del modelo Groq para análisis de opiniones."""

    def __init__(self):
        """Inicializa el cliente Groq con la API key del entorno."""
        self._api_key = os.getenv("GROQ_API_KEY", "")
        self._modelo = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self._cliente = Groq(api_key=self._api_key)

    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        """
        Envía los prompts a Groq y retorna la respuesta.

        Incluye un reintento automático con espera de 60 segundos
        si se recibe un error de rate limit.

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
                "[Groq] Rate limit alcanzado — esperando 60 segundos..."
            )
            time.sleep(60)

            respuesta = self._cliente.chat.completions.create(
                model=self._modelo,
                messages=mensajes,
                temperature=0.1,
                max_tokens=800,
            )
            return respuesta.choices[0].message.content or ""

    def nombre_modelo(self) -> str:
        """Retorna el identificador del modelo para logging."""
        return f"groq ({self._modelo})"
