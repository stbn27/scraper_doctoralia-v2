"""
Logger dedicado al pipeline NLP de análisis de opiniones.

Genera un archivo de log independiente por cada ejecución del pipeline,
almacenado en ``backend/logs/nlp/``. Complementa (no reemplaza) el logger
estándar de consola del pipeline.

Formato de nombre de archivo:
    nlp_{ddMMyy}_{HHMMSS}_{modelo}_{modo}_{particion}.log

Ejemplo:
    nlp_010626_100100_groq_prueba_completo.log
    nlp_010626_100101_deepseek_masivo_p1de4.log
"""

import logging
import os
from datetime import datetime
from pathlib import Path


# ── Directorio base de logs NLP ──
_LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "nlp"


class _PaddedLevelFormatter(logging.Formatter):
    """
    Formatter que aplica padding fijo al nombre del nivel de log
    para mantener alineación visual en el archivo de salida.

    Ejemplo de salida:
        [2026-06-01 09:10:43] [INFO   ] mensaje
        [2026-06-01 09:10:44] [WARNING] mensaje
        [2026-06-01 09:10:45] [ERROR  ] mensaje
        [2026-06-01 09:10:46] [SUCCESS] mensaje completado
    """

    _LEVEL_MAP = {
        "DEBUG": "DEBUG  ",
        "INFO": "INFO   ",
        "WARNING": "WARNING",
        "ERROR": "ERROR  ",
        "CRITICAL": "CRITICAL",
        "SUCCESS": "SUCCESS",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro aplicando padding al nivel."""
        original = record.levelname
        record.levelname = self._LEVEL_MAP.get(original, original.ljust(7))
        resultado = super().format(record)
        record.levelname = original
        return resultado


def iniciar_sesion_log(
    modelo: str,
    modo: str = "prueba",
    particion: str = "completo",
) -> logging.Logger:
    """
    Crea y configura el logger para una ejecución del pipeline NLP.

    Escribe simultáneamente a:
      - ``backend/logs/nlp/nlp_{ddMMyy}_{HHMMSS}_{modelo}_{modo}_{particion}.log`` (archivo)
      - stdout (consola), con el mismo formato

    El directorio ``backend/logs/nlp/`` se crea automáticamente si no existe.

    Parámetros
    ----------
    modelo : str
        Nombre del modelo activo (ej: ``"groq"``, ``"deepseek"``).
    modo : str
        Modo de ejecución (ej: ``"prueba"``, ``"masivo"``, ``"especialidad"``).
    particion : str
        Identificador de partición (ej: ``"completo"``, ``"p1de4"``).

    Retorna
    -------
    logging.Logger
        Logger configurado con handlers de archivo y consola.

    Ejemplo
    -------
    >>> logger_nlp = iniciar_sesion_log("groq", "prueba", "completo")
    >>> logger_nlp.info("Pipeline iniciado correctamente")
    """
    # Asegurar que el directorio existe
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Generar nombre de archivo con timestamp
    ahora = datetime.now()
    timestamp = ahora.strftime("%d%m%y_%H%M%S")
    modelo_safe = modelo.split(" ")[0].replace("(", "").replace(")", "")
    nombre_archivo = f"nlp_{timestamp}_{modelo_safe}_{modo}_{particion}.log"
    ruta_log = _LOGS_DIR / nombre_archivo

    # Crear logger con nombre único por sesión para evitar colisiones
    nombre_logger = f"nlp_pipeline_{timestamp}_{modelo_safe}"
    logger_nlp = logging.getLogger(nombre_logger)
    logger_nlp.setLevel(logging.DEBUG)

    # Evitar duplicación de handlers si se llama más de una vez
    if logger_nlp.handlers:
        return logger_nlp

    # Formato compartido
    fmt = "[%(asctime)s] [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = _PaddedLevelFormatter(fmt=fmt, datefmt=datefmt)

    # Handler de archivo (UTF-8)
    file_handler = logging.FileHandler(ruta_log, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger_nlp.addHandler(file_handler)

    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger_nlp.addHandler(console_handler)

    # Evitar propagación al logger root para no duplicar salida
    logger_nlp.propagate = False

    # Registrar nivel SUCCESS si no existe
    if not hasattr(logging, "SUCCESS"):
        logging.SUCCESS = 25  # type: ignore[attr-defined]
        logging.addLevelName(25, "SUCCESS")

    logger_nlp.info(
        "Sesión de log iniciada — archivo: %s", nombre_archivo,
    )

    return logger_nlp


def registrar_respuesta_cruda(
    logger_nlp: logging.Logger,
    doctor_id: int,
    nombre: str,
    respuesta_raw: str,
    exito: bool,
) -> None:
    """
    Registra la respuesta completa (sin truncar) del modelo en el log.

    Incluye un bloque visual delimitado que facilita la lectura posterior
    del archivo de log para depuración y auditoría.

    Parámetros
    ----------
    logger_nlp : logging.Logger
        Logger de la sesión NLP activa.
    doctor_id : int
        Identificador del doctor en Doctoralia.
    nombre : str
        Nombre del especialista.
    respuesta_raw : str
        Respuesta cruda completa del modelo de IA.
    exito : bool
        ``True`` si el JSON se parseó correctamente, ``False`` en caso contrario.

    Ejemplo
    -------
    >>> registrar_respuesta_cruda(logger_nlp, 355439, "Dr. Pérez", '{"score": 8}', True)
    """
    estado_texto = "ÉXITO" if exito else "FALLO"
    longitud = len(respuesta_raw) if respuesta_raw else 0

    bloque = (
        f"\n══════════════════════════════════════════════════════\n"
        f"RESPUESTA MODELO — {nombre} | id={doctor_id}\n"
        f"Estado: {estado_texto} | Longitud: {longitud} chars\n"
        f"──────────────────────────────────────────────────────\n"
        f"{respuesta_raw}\n"
        f"══════════════════════════════════════════════════════"
    )

    if exito:
        logger_nlp.debug(bloque)
    else:
        logger_nlp.warning(bloque)


def registrar_resumen_final(
    logger_nlp: logging.Logger,
    stats: dict,
) -> None:
    """
    Registra el resumen consolidado de la ejecución al finalizar el pipeline.

    Parámetros
    ----------
    logger_nlp : logging.Logger
        Logger de la sesión NLP activa.
    stats : dict
        Diccionario con las estadísticas de la ejecución. Claves esperadas:

        - ``total`` (int): Total de especialistas procesados.
        - ``completados`` (int): Análisis completados exitosamente.
        - ``sin_opiniones`` (int): Análisis mínimos generados.
        - ``errores`` (int): Fallos definitivos.
        - ``skips`` (int): Omitidos por análisis reciente.
        - ``tiempo_segundos`` (float): Duración total en segundos.
        - ``modelo`` (str): Nombre del modelo utilizado.
        - ``modo`` (str): Modo de ejecución.

    Ejemplo
    -------
    >>> registrar_resumen_final(logger_nlp, {
    ...     "total": 100, "completados": 85, "sin_opiniones": 10,
    ...     "errores": 3, "skips": 2, "tiempo_segundos": 120.5,
    ...     "modelo": "groq", "modo": "prueba",
    ... })
    """
    total = stats.get("total", 0)
    completados = stats.get("completados", 0)
    sin_opiniones = stats.get("sin_opiniones", 0)
    errores = stats.get("errores", 0)
    skips = stats.get("skips", 0)
    tiempo = stats.get("tiempo_segundos", 0.0)
    modelo = stats.get("modelo", "desconocido")
    modo = stats.get("modo", "desconocido")

    minutos = int(tiempo // 60)
    segundos = int(tiempo % 60)
    promedio = f"{tiempo / total:.1f}s/médico" if total > 0 else "N/A"

    tasa_exito = f"{(completados / total * 100):.1f}%" if total > 0 else "N/A"

    bloque = (
        f"\n{'═' * 60}\n"
        f"  RESUMEN DE EJECUCIÓN — Pipeline NLP\n"
        f"{'─' * 60}\n"
        f"  Modelo:          {modelo}\n"
        f"  Modo:            {modo}\n"
        f"  Total médicos:   {total}\n"
        f"{'─' * 60}\n"
        f"  Completados:     {completados}\n"
        f"  Sin opiniones:   {sin_opiniones}\n"
        f"  Errores:         {errores}\n"
        f"  Skips:           {skips}\n"
        f"{'─' * 60}\n"
        f"  Tasa de éxito:   {tasa_exito}\n"
        f"  Tiempo total:    {minutos}m {segundos:02d}s\n"
        f"  Promedio:        {promedio}\n"
        f"{'═' * 60}"
    )

    logger_nlp.info(bloque)
