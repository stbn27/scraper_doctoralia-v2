"""
Implementación del modelo LM Studio (servidor local de inferencia).

Usa la API compatible con OpenAI que expone LM Studio en http://127.0.0.1:1234.
El endpoint de chat es POST /api/v1/chat, distinto al de Ollama.

Variables de entorno requeridas:
    - LMSTUDIO_BASE_URL : URL base del servidor LM Studio (default: http://127.0.0.1:1234)
    - LMSTUDIO_MODEL    : Nombre del modelo activo en LM Studio (default: qwen3-0.6b)
"""

import logging
import os
import time

# pyrefly: ignore [missing-import]
import httpx

from app.nlp.modelos.base_modelo import BaseModelo

logger = logging.getLogger(__name__)


class LMStudioModelo(BaseModelo):
    """
    Implementación del modelo LM Studio para el chatbot médico.

    Conecta contra el servidor local de LM Studio usando su API REST propia.
    Soporta system_prompt + input como campo único (API nativa de LM Studio).

    Ejemplo de uso:
        >>> modelo = LMStudioModelo()
        >>> respuesta = modelo.analizar(prompt_sistema, prompt_usuario)
    """

    def __init__(self):
        """Inicializa la configuración de conexión a LM Studio."""
        super().__init__()
        self._base_url = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234").rstrip(
            "/"
        )
        self._modelo = os.getenv("LMSTUDIO_MODEL", "qwen3-0.6b")

    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        """
        Envía los prompts a LM Studio y retorna la respuesta.

        Usa el endpoint /api/v1/chat de LM Studio que acepta system_prompt + input.
        Timeout de 120s suficiente para modelos pequeños (Qwen3 0.6B).

        Parámetros
        ----------
        prompt_sistema : str
            Prompt del sistema con instrucciones del modelo.
        prompt_usuario : str
            Prompt del usuario con la consulta actual.

        Retorna
        -------
        str
            Respuesta cruda del modelo en texto plano.

        Lanza
        -----
        httpx.HTTPStatusError
            Si el servidor retorna un código de error HTTP.
        httpx.ConnectError
            Si el servidor LM Studio no está disponible.
        """
        url = f"{self._base_url}/api/v1/chat"
        payload = {
            "model": self._modelo,
            "system_prompt": prompt_sistema,
            "input": prompt_usuario,
        }

        t0 = time.monotonic()
        logger.info(
            "[LMStudioModelo] Enviando petición a %s con modelo %s", url, self._modelo
        )

        self._registrar_request_remoto()
        respuesta = httpx.post(url, json=payload, timeout=120.0)
        respuesta.raise_for_status()

        elapsed = time.monotonic() - t0
        logger.info("[LMStudioModelo] Respuesta recibida en %.1fs", elapsed)

        datos = respuesta.json()

        # La API /api/v1/chat de LM Studio devuelve:
        # {
        #   "output": [
        #     {"type": "reasoning", "content": "...pensamiento interno..."},
        #     {"type": "message",   "content": "...respuesta final..."}
        #   ]
        # }
        # Solo nos interesa el item de tipo "message".
        output = datos.get("output", [])
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict) and item.get("type") == "message":
                    return item.get("content", "")
            # Si no hay item tipo "message", concatenar todo lo que no sea reasoning
            partes = [
                item.get("content", "")
                for item in output
                if isinstance(item, dict) and item.get("type") != "reasoning"
            ]
            if partes:
                return "\n".join(partes)

        # Compatibilidad con formatos alternativos
        if "response" in datos:
            return datos["response"]

        choices = datos.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")

        return str(datos)

    def nombre_modelo(self) -> str:
        """Retorna el identificador del modelo para logging."""
        return f"lmstudio ({self._modelo})"
