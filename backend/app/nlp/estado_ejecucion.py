"""Contadores operativos del pipeline NLP."""

from dataclasses import dataclass


@dataclass
class EstadisticasNLP:
    candidatos_revisados: int = 0
    procesados_llm: int = 0
    procesados_localmente: int = 0
    skips: int = 0
    errores: int = 0
    requests_llm_realizados: int = 0
    requests_llm_exitosos: int = 0
    requests_llm_fallidos: int = 0
    limite_requests_llm: int | None = None
    detenido_por: str | None = None


def actualizar_estadisticas(stats: EstadisticasNLP, resultado: dict) -> None:
    """Actualiza contadores sin descontar límite por procesos locales/skips."""
    estado = resultado.get("estado", "error")
    requests = int(resultado.get("requests_consumidos", 0) or 0)
    stats.requests_llm_realizados += requests

    if resultado.get("llm_exitoso"):
        stats.procesados_llm += 1
        stats.requests_llm_exitosos += 1
    elif resultado.get("llm_realizado"):
        stats.requests_llm_fallidos += 1

    if estado in ("sin_opiniones", "sospecha_fraude") and not resultado.get("llm_realizado"):
        stats.procesados_localmente += 1
    elif estado == "skip":
        stats.skips += 1
    elif estado == "error":
        stats.errores += 1
