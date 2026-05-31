"""
Gestión del estado persistente del pipeline masivo de scraping Doctoralia.

Persiste el progreso en ``fixtures/pipeline_estado.json`` para permitir
**reanudar ejecuciones interrumpidas** sin reprocesar lo ya completado.

Estructura del archivo de estado::

    {
      "inicio_ejecucion": "2026-05-27T14:00:00+00:00",
      "ultima_actividad": "2026-05-27T14:35:22+00:00",
      "fase_actual": "perfiles",
      "catalogos_cargados": false,
      "listados_completados": ["endodoncia/ciudad-de-mexico"],
      "perfiles_completados": [355439, 472513],
      "opiniones_completadas": [355439],
      "errores": [
        {
          "fase": "perfiles",
          "identificador": "https://doctoralia.com.mx/...",
          "error": "HTTPStatusError 429",
          "timestamp": "2026-05-27T14:31:00+00:00"
        }
      ]
    }

Cada función que modifica el estado llama a ``guardar_estado()`` antes de
retornar para minimizar la pérdida de progreso ante interrupciones inesperadas.

Uso básico::

    from app.scraper.utils.estado_pipeline import (
        cargar_estado, marcar_listado_completado, marcar_perfil_completado
    )

    estado = cargar_estado()
    estado = marcar_listado_completado(estado, "endodoncia/ciudad-de-mexico")
    estado = marcar_perfil_completado(estado, 355439)
"""

import json
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
_RAIZ_PROYECTO = Path(__file__).resolve().parents[3]
_RUTA_ESTADO = _RAIZ_PROYECTO / "fixtures" / "pipeline_estado.json"


def establecer_sufijo_estado(sufijo: str) -> None:
    """Configura dinámicamente un sufijo para el archivo de estado (ej: para sharding paralelo).

    Args:
        sufijo: Texto para añadir al final del nombre del archivo, ej. 'parte0'.
    """
    global _RUTA_ESTADO
    if sufijo:
        _RUTA_ESTADO = _RAIZ_PROYECTO / "fixtures" / f"pipeline_estado_{sufijo}.json"
    else:
        _RUTA_ESTADO = _RAIZ_PROYECTO / "fixtures" / "pipeline_estado.json"


# ---------------------------------------------------------------------------
# Estado vacío base
# ---------------------------------------------------------------------------
def _estado_vacio() -> dict:
    """Crea la estructura base de un estado vacío.

    Returns:
        Diccionario con todos los campos del estado inicializados a sus valores
        por defecto (listas vacías, banderas en False, timestamps actuales).
    """
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "inicio_ejecucion": ahora,
        "ultima_actividad": ahora,
        "fase_actual": None,
        "catalogos_cargados": False,
        "listados_completados": [],
        "cola_perfiles": [],
        "perfiles_completados": [],
        "opiniones_completadas": [],
        "errores": [],
    }


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------
def guardar_estado(estado: dict) -> None:
    """Persiste el estado en disco de forma atómica.

    Actualiza ``ultima_actividad`` al momento actual antes de escribir.
    El directorio ``fixtures/`` se crea automáticamente si no existe.

    Args:
        estado: Diccionario de estado actual del pipeline.

    Side Effects:
        Escribe o sobreescribe ``fixtures/pipeline_estado.json``.
    """
    estado["ultima_actividad"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )
    _RUTA_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    with _RUTA_ESTADO.open("w", encoding="utf-8") as archivo:
        json.dump(estado, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def cargar_estado() -> dict:
    """Carga el estado persistido desde disco.

    Si el archivo no existe o está corrupto, retorna un estado vacío nuevo
    sin lanzar excepción.

    Returns:
        Diccionario con el estado del pipeline. Siempre es un diccionario
        válido aunque sea el estado vacío inicial.

    Ejemplo::

        estado = cargar_estado()
        print(estado["fase_actual"])
    """
    if not _RUTA_ESTADO.exists():
        return _estado_vacio()
    try:
        with _RUTA_ESTADO.open("r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if not isinstance(datos, dict):
            return _estado_vacio()
        return datos
    except (json.JSONDecodeError, OSError):
        return _estado_vacio()


def resetear_estado() -> dict:
    """Borra el estado actual y crea uno nuevo vacío.

    Útil para reiniciar el pipeline desde cero, descartando todo el progreso
    anterior.

    Returns:
        Diccionario con el nuevo estado vacío, ya persistido en disco.

    Side Effects:
        Sobreescribe ``fixtures/pipeline_estado.json`` con un estado limpio.
    """
    nuevo_estado = _estado_vacio()
    guardar_estado(nuevo_estado)
    return nuevo_estado


def guardar_cola_perfiles(estado: dict, cola: list[dict]) -> dict:
    """Persiste la cola de perfiles en el estado para sobrevivir reinicios.

    La cola es la lista de médicos descubiertos en la Fase 2 (listados) que
    la Fase 3 (perfiles) debe procesar. Sin esta persistencia, una
    interrupción entre ambas fases perdería la cola.

    Args:
        estado: Estado actual del pipeline.
        cola: Lista de dicts ``{doctoralia_id, url_perfil, nombre}``.

    Returns:
        Estado actualizado con la cola persistida en disco.
    """
    estado["cola_perfiles"] = cola
    guardar_estado(estado)
    return estado


# ---------------------------------------------------------------------------
# Marcadores de progreso
# ---------------------------------------------------------------------------
def marcar_listado_completado(estado: dict, clave: str) -> dict:
    """Registra un par especialidad/ciudad como scrapeado exitosamente.

    Args:
        estado: Estado actual del pipeline.
        clave: Identificador del par, con formato ``"especialidad/ciudad"``,
            por ejemplo ``"endodoncia/ciudad-de-mexico"``.

    Returns:
        Estado actualizado con la clave añadida a ``listados_completados``
        y persistido en disco.
    """
    if clave not in estado.get("listados_completados", []):
        estado.setdefault("listados_completados", []).append(clave)
    guardar_estado(estado)
    return estado


def marcar_perfil_completado(estado: dict, doctoralia_id: int) -> dict:
    """Registra un perfil de médico como descargado y persistido.

    Args:
        estado: Estado actual del pipeline.
        doctoralia_id: Identificador interno del médico en Doctoralia.

    Returns:
        Estado actualizado con el ID añadido a ``perfiles_completados``
        y persistido en disco.
    """
    if doctoralia_id not in estado.get("perfiles_completados", []):
        estado.setdefault("perfiles_completados", []).append(doctoralia_id)
    guardar_estado(estado)
    return estado


def marcar_opiniones_completadas(estado: dict, doctoralia_id: int) -> dict:
    """Registra que las opiniones de un médico fueron descargadas y persistidas.

    Args:
        estado: Estado actual del pipeline.
        doctoralia_id: Identificador interno del médico en Doctoralia.

    Returns:
        Estado actualizado con el ID añadido a ``opiniones_completadas``
        y persistido en disco.
    """
    if doctoralia_id not in estado.get("opiniones_completadas", []):
        estado.setdefault("opiniones_completadas", []).append(doctoralia_id)
    guardar_estado(estado)
    return estado


def registrar_error(
    estado: dict, fase: str, identificador: str, error: str
) -> dict:
    """Registra un error ocurrido durante una fase del pipeline.

    No detiene la ejecución — solo persiste el error para revisión posterior.

    Args:
        estado: Estado actual del pipeline.
        fase: Nombre de la fase donde ocurrió el error
            (``"listados"``, ``"perfiles"``, ``"opiniones"``).
        identificador: URL, clave o ID del elemento que generó el error.
        error: Descripción del error (clase de excepción, mensaje HTTP, etc.).

    Returns:
        Estado actualizado con el error añadido a la lista ``errores``
        y persistido en disco.
    """
    entrada_error = {
        "fase": fase,
        "identificador": identificador,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    estado.setdefault("errores", []).append(entrada_error)
    guardar_estado(estado)
    return estado


# ---------------------------------------------------------------------------
# Consultas de estado (solo lectura)
# ---------------------------------------------------------------------------
def listado_ya_completado(estado: dict, clave: str) -> bool:
    """Verifica si un par especialidad/ciudad ya fue scrapeado.

    Args:
        estado: Estado actual del pipeline.
        clave: Identificador del par, con formato ``"especialidad/ciudad"``.

    Returns:
        ``True`` si la clave ya está en ``listados_completados``.
    """
    return clave in estado.get("listados_completados", [])


def perfil_ya_completado(estado: dict, doctoralia_id: int) -> bool:
    """Verifica si el perfil de un médico ya fue descargado.

    Args:
        estado: Estado actual del pipeline.
        doctoralia_id: Identificador interno del médico en Doctoralia.

    Returns:
        ``True`` si el ID ya está en ``perfiles_completados``.
    """
    return doctoralia_id in estado.get("perfiles_completados", [])


def opiniones_ya_completadas(estado: dict, doctoralia_id: int) -> bool:
    """Verifica si las opiniones de un médico ya fueron descargadas.

    Args:
        estado: Estado actual del pipeline.
        doctoralia_id: Identificador interno del médico en Doctoralia.

    Returns:
        ``True`` si el ID ya está en ``opiniones_completadas``.
    """
    return doctoralia_id in estado.get("opiniones_completadas", [])
