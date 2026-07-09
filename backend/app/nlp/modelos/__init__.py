"""
Paquete de modelos de IA — Factory para instanciar el modelo activo.

Uso:
    >>> from app.nlp.modelos import obtener_modelo
    >>> modelo = obtener_modelo()           # Usa MODELO_ACTIVO del .env
    >>> modelo = obtener_modelo("deepseek") # Fuerza un modelo específico
"""

import os

from app.nlp.modelos.base_modelo import BaseModelo


def obtener_modelo(nombre: str | None = None) -> BaseModelo:
    """
    Retorna la instancia del modelo según el nombre.

    Si nombre es None, usa la variable de entorno MODELO_ACTIVO.

    Parámetros
    ----------
    nombre : str | None
        Nombre del modelo a instanciar.
        Valores válidos: groq | deepseek | gemini | minimax | ollama | lmstudio

    Retorna
    -------
    BaseModelo
        Instancia del modelo solicitado.

    Lanza
    -----
    ValueError
        Si el nombre del modelo no es válido.
    """
    if nombre is None:
        nombre = os.getenv("MODELO_ACTIVO", "groq")

    nombre = nombre.strip().lower()

    if nombre == "groq":
        from app.nlp.modelos.groq_modelo import GroqModelo

        return GroqModelo()

    elif nombre == "deepseek":
        from app.nlp.modelos.deepseek_modelo import DeepSeekModelo

        return DeepSeekModelo()

    elif nombre == "gemini":
        from app.nlp.modelos.gemini_modelo import GeminiModelo

        return GeminiModelo()

    elif nombre == "minimax":
        from app.nlp.modelos.minimax_modelo import MiniMaxModelo

        return MiniMaxModelo()

    elif nombre == "ollama":
        from app.nlp.modelos.ollama_modelo import OllamaModelo

        return OllamaModelo()

    elif nombre == "lmstudio":
        from app.nlp.modelos.lmstudio_modelo import LMStudioModelo

        return LMStudioModelo()

    else:
        modelos_validos = [
            "groq",
            "deepseek",
            "gemini",
            "minimax",
            "ollama",
            "lmstudio",
        ]
        raise ValueError(
            f"Modelo '{nombre}' no reconocido. "
            f"Valores válidos: {', '.join(modelos_validos)}"
        )
