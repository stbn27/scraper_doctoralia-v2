"""
Clase base abstracta para todos los modelos de IA.
"""

import json
import re
from abc import ABC, abstractmethod
from threading import Lock


class ErrorProveedorFatal(RuntimeError):
    """Error no recuperable del proveedor: cuota, billing, créditos o cuenta."""

    fatal_proveedor = True

    def __init__(self, mensaje: str, proveedor: str | None = None):
        self.proveedor = proveedor
        super().__init__(mensaje)


class LimiteRequestsLLMAlcanzado(RuntimeError):
    """Se alcanzó el límite configurado antes de hacer otra llamada remota."""


_PATRONES_FATAL_PROVEEDOR = (
    "quota exceeded",
    "insufficient quota",
    "insufficient_quota",
    "exceeded your current quota",
    "exhausted credits",
    "exhausted credit",
    "insufficient credits",
    "insufficient tokens",
    "billing required",
    "payment required",
    "account disabled",
    "account has been disabled",
    "forbidden by account",
    "hard limit",
    "credit balance is too low",
    "no credits",
)

_PATRONES_RATE_RECUPERABLE = (
    "rate limit",
    "ratelimit",
    "too many requests",
    "429",
    "resource exhausted",
)


def es_error_fatal_proveedor(error) -> bool:
    """Detecta errores de cuota/crédito no recuperables por texto normalizado."""
    texto = str(error).lower()
    return any(patron in texto for patron in _PATRONES_FATAL_PROVEEDOR)


def es_rate_limit_recuperable(error) -> bool:
    """Detecta rate limit recuperable sin clasificar cuota agotada como retry."""
    if es_error_fatal_proveedor(error):
        return False
    texto = str(error).lower()
    return any(patron in texto for patron in _PATRONES_RATE_RECUPERABLE)


class BaseModelo(ABC):
    """Clase abstracta que todos los modelos de IA deben implementar."""

    def __init__(self) -> None:
        self._requests_remotos_realizados = 0
        self._limite_requests_remotos: int | None = None
        self._lock_requests = Lock()

    def _asegurar_medidor_requests(self) -> None:
        """Inicializa el medidor si una subclase antigua no llamó super().__init__."""
        if not hasattr(self, "_lock_requests"):
            self._requests_remotos_realizados = 0
            self._limite_requests_remotos = None
            self._lock_requests = Lock()

    def configurar_limite_requests(self, limite: int | None) -> None:
        """Define un límite duro de invocaciones remotas para esta ejecución."""
        self._asegurar_medidor_requests()
        with self._lock_requests:
            self._limite_requests_remotos = limite

    @property
    def requests_remotos_realizados(self) -> int:
        """Total de requests remotos intentados por esta instancia."""
        self._asegurar_medidor_requests()
        with self._lock_requests:
            return self._requests_remotos_realizados

    def _registrar_request_remoto(self) -> None:
        """Debe llamarse justo antes de invocar HTTP al proveedor remoto."""
        self._asegurar_medidor_requests()
        with self._lock_requests:
            if (
                self._limite_requests_remotos is not None
                and self._requests_remotos_realizados >= self._limite_requests_remotos
            ):
                raise LimiteRequestsLLMAlcanzado(
                    "Límite de requests LLM alcanzado antes de llamar al proveedor."
                )
            self._requests_remotos_realizados += 1

    @abstractmethod
    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        """Envía los prompts al modelo y retorna la respuesta como string."""

    def parsear_respuesta(self, respuesta_raw: str) -> dict:
        """
        Extrae el JSON de la respuesta del modelo.
        Maneja bloques ```json...```, texto antes/después del JSON,
        y respuestas truncadas.
        """
        if not respuesta_raw or not respuesta_raw.strip():
            raise ValueError("El modelo retornó una respuesta vacía.")

        texto = respuesta_raw.strip()

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
        if match:
            candidato = match.group(1).strip()
            try:
                return json.loads(candidato)
            except json.JSONDecodeError:
                pass

        inicio = texto.find("{")
        fin = texto.rfind("}")
        if inicio != -1 and fin != -1 and fin > inicio:
            candidato = texto[inicio:fin + 1]
            try:
                return json.loads(candidato)
            except json.JSONDecodeError:
                pass

        if inicio != -1:
            decoder = json.JSONDecoder()
            try:
                obj, _ = decoder.raw_decode(texto, inicio)
                return obj
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"No se pudo extraer JSON válido de la respuesta del modelo. "
            f"Respuesta recibida (primeros 500 chars): {respuesta_raw[:500]}"
        )

    @abstractmethod
    def nombre_modelo(self) -> str:
        """Retorna el identificador del modelo para logging y persistencia."""
