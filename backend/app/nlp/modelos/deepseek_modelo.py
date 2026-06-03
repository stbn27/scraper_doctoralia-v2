"""
Implementación del modelo DeepSeek API.
"""

import logging
import os
import time

from openai import OpenAI, RateLimitError

from app.nlp.modelos.base_modelo import (
    BaseModelo,
    ErrorProveedorFatal,
    es_error_fatal_proveedor,
)

logger = logging.getLogger(__name__)


class DeepSeekModelo(BaseModelo):
    """Implementación del modelo DeepSeek para análisis de opiniones."""

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self._modelo = os.getenv("DEEPSEEK_MODEL_NLP", "deepseek-chat")
        self._base_url = os.getenv("DEEPSEEK_BASE_URL_NLP", "https://api.deepseek.com")
        self._cliente = OpenAI(api_key=self._api_key, base_url=self._base_url)

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
                max_tokens=2500,
                extra_body={"thinking": {"type": "disabled"}},
            )
            return respuesta.choices[0].message.content or ""
        except RateLimitError as exc:
            if es_error_fatal_proveedor(exc):
                raise ErrorProveedorFatal(str(exc), proveedor="deepseek") from exc
            logger.warning("[DeepSeek] Rate limit recuperable — esperando 60 segundos...")
            time.sleep(60)
            self._registrar_request_remoto()
            respuesta = self._cliente.chat.completions.create(
                model=self._modelo,
                messages=mensajes,
                temperature=0.1,
                max_tokens=2500,
            )
            return respuesta.choices[0].message.content or ""
        except Exception as exc:
            if es_error_fatal_proveedor(exc):
                raise ErrorProveedorFatal(str(exc), proveedor="deepseek") from exc
            raise

    def nombre_modelo(self) -> str:
        return f"deepseek ({self._modelo})"
