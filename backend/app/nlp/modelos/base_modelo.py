"""
Clase base abstracta para todos los modelos de IA.

Todas las implementaciones de modelos (Groq, DeepSeek, Gemini, MiniMax, Ollama)
deben heredar de BaseModelo e implementar los métodos abstractos.

Ejemplo de uso:
    >>> from app.nlp.modelos import obtener_modelo
    >>> modelo = obtener_modelo("groq")
    >>> respuesta = modelo.analizar(prompt_sistema, prompt_usuario)
    >>> resultado = modelo.parsear_respuesta(respuesta)
"""

import json
import re
from abc import ABC, abstractmethod


class BaseModelo(ABC):
    """Clase abstracta que todos los modelos de IA deben implementar."""

    @abstractmethod
    def analizar(self, prompt_sistema: str, prompt_usuario: str) -> str:
        """
        Envía los prompts al modelo y retorna la respuesta como string.

        Parámetros
        ----------
        prompt_sistema : str
            Prompt del sistema con el rol e instrucciones del modelo.
        prompt_usuario : str
            Prompt del usuario con los datos del especialista.

        Retorna
        -------
        str
            Respuesta cruda del modelo como string.

        Lanza
        -----
        Exception
            En caso de error de conexión, rate limit, etc.
        """

    def parsear_respuesta(self, respuesta_raw: str) -> dict:
        """
        Extrae el JSON de la respuesta del modelo.
        Maneja: bloques ```json...```, texto antes/después del JSON,
        y respuestas truncadas (intenta reparar con json.JSONDecoder).

        Parámetros
        ----------
        respuesta_raw : str
            Respuesta cruda del modelo como string.

        Retorna
        -------
        dict
            Diccionario con las claves del análisis.

        Lanza
        -----
        ValueError
            Si no se puede extraer JSON válido de la respuesta.
        """

        if not respuesta_raw or not respuesta_raw.strip():
            raise ValueError("El modelo retornó una respuesta vacía.")

        texto = respuesta_raw.strip()

        # Intento 1: bloque ```json ... ```
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
        if match:
            candidato = match.group(1).strip()
            try:
                return json.loads(candidato)
            except json.JSONDecodeError:
                pass

        # Intento 2: primer { hasta el último }
        inicio = texto.find("{")
        fin = texto.rfind("}")
        if inicio != -1 and fin != -1 and fin > inicio:
            candidato = texto[inicio:fin + 1]
            try:
                return json.loads(candidato)
            except json.JSONDecodeError:
                pass

        # Intento 3: json.JSONDecoder con raw_decode (maneja JSON seguido de texto)
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
        """
        Retorna el identificador del modelo para logging y persistencia.

        Retorna
        -------
        str
            Nombre del modelo (ej: "groq", "deepseek", "gemini").
        """
