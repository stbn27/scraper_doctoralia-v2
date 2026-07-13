"""
Implementación del modelo Ollama (uso futuro — requiere Ollama instalado localmente).

# USO FUTURO — requiere Ollama instalado localmente
Usa httpx directamente contra la API REST de Ollama, sin dependencia adicional.
POST a {OLLAMA_BASE_URL}/api/chat.

Variables de entorno requeridas:
    - OLLAMA_BASE_URL: URL base de Ollama (default: http://localhost:11434)
    - OLLAMA_MODEL: Modelo a usar (default: llama3.1:8b)
"""

import os
import logging

# pyrefly: ignore [missing-import]
import httpx

from app.nlp.modelos.base_modelo import BaseModelo

logger = logging.getLogger(__name__)


class OllamaModelo(BaseModelo):
    """
    Implementación del modelo Ollama para análisis de opiniones.
    """

    def __init__(self):
        """Inicializa la configuración de conexión a Ollama o LM Studio."""
        self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._modelo = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self._es_lm_studio = False

    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        """
        Envía los prompts al proveedor local (Ollama o LM Studio) via HTTP y retorna la respuesta.

        El timeout es alto (600s) porque modelos locales grandes pueden tardar
        en la primera carga a VRAM.

        Parámetros
        ----------
        prompt_sistema : str
            Prompt del sistema con instructions del modelo.
        prompt_usuario : str
            Prompt del usuario con datos del especialista.

        Retorna
        -------
        str
            Respuesta cruda del modelo.
        """
        import time

        es_lm = self._es_lm_studio or "1234" in str(self._base_url) or str(self._base_url).rstrip("/").endswith("/v1")

        if es_lm:
            base = str(self._base_url).rstrip("/")
            if base.endswith("/v1"):
                url = f"{base}/chat/completions"
            else:
                url = f"{base}/v1/chat/completions"
            payload = {
                "model": self._modelo,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario},
                ],
                "stream": False,
                "temperature": 0.1,
                "max_tokens": 800,
            }
        else:
            url = f"{self._base_url.rstrip('/')}/api/chat"
            payload = {
                "model": self._modelo,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario},
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 800,
                },
            }

        t0 = time.monotonic()
        logger.info(
            "[OllamaModelo] Enviando petición a %s con modelo %s (es_lm_studio=%s)", url, self._modelo, es_lm
        )
        respuesta = httpx.post(url, json=payload, timeout=600.0)
        respuesta.raise_for_status()
        elapsed = time.monotonic() - t0
        logger.info("[OllamaModelo] Respuesta recibida en %.1fs", elapsed)

        datos = respuesta.json()
        if es_lm or "choices" in datos:
            choices = datos.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        return datos.get("message", {}).get("content", "")

    def nombre_modelo(self) -> str:
        """Retorna el identificador del modelo para logging."""
        tipo = "lm_studio" if (self._es_lm_studio or "1234" in str(self._base_url) or str(self._base_url).rstrip("/").endswith("/v1")) else "ollama"
        return f"{tipo} ({self._modelo})"
