"""
Implementación del modelo Groq.
"""

import logging
import os
import time

from groq import Groq, RateLimitError

from app.nlp.modelos.base_modelo import (
    BaseModelo,
    ErrorProveedorFatal,
    es_error_fatal_proveedor,
)

logger = logging.getLogger(__name__)


class GroqModelo(BaseModelo):
    """Implementación del modelo Groq para análisis de opiniones."""

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("GROQ_API_KEY", "")
        self._modelo = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self._cliente = Groq(api_key=self._api_key)

    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        mensajes = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario},
        ]
        try:
            self._registrar_request_remoto()
            respuesta = self._cliente.chat.completions.create(
                model=self._modelo,
                messages=mensajes,
                temperature=0.1,
                max_tokens=1500,
            )
            return respuesta.choices[0].message.content or ""
        except RateLimitError as exc:
            if es_error_fatal_proveedor(exc):
                raise ErrorProveedorFatal(str(exc), proveedor="groq") from exc
            logger.warning("[Groq] Rate limit recuperable — esperando 60 segundos...")
            time.sleep(60)
            self._registrar_request_remoto()
            respuesta = self._cliente.chat.completions.create(
                model=self._modelo,
                messages=mensajes,
                temperature=0.1,
                max_tokens=1500,
            )
            return respuesta.choices[0].message.content or ""
        except Exception as exc:
            if es_error_fatal_proveedor(exc):
                raise ErrorProveedorFatal(str(exc), proveedor="groq") from exc
            raise

    def nombre_modelo(self) -> str:
        return f"groq ({self._modelo})"
