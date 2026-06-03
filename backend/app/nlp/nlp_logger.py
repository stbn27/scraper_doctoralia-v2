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

    logger_nlp.debug(bloque)


def registrar_evento_candidato(
    logger_nlp: logging.Logger,
    resultado: dict,
) -> None:
    """Registra la decisión final tomada para un candidato."""
    doctor_id = resultado.get("doctor_id", "N/A")
    nombre = resultado.get("nombre") or "Sin nombre"
    estado = resultado.get("estado", "desconocido")
    detalle = resultado.get("detalle") or ""
    requests = int(resultado.get("requests_consumidos", 0) or 0)
    llm_realizado = "si" if resultado.get("llm_realizado") else "no"

    mensaje = (
        "CANDIDATO | estado=%s | id=%s | nombre=%s | llm=%s | requests=%d | detalle=%s"
        % (estado, doctor_id, nombre, llm_realizado, requests, detalle)
    )

    logger_nlp.debug(mensaje)


def registrar_evento_llm(
    logger_nlp: logging.Logger,
    doctor_id: int,
    nombre: str,
    evento: str,
    detalle: str = "",
) -> None:
    """Registra eventos intermedios de llamada/parsing del modelo."""
    mensaje = "LLM | evento=%s | id=%s | nombre=%s" % (evento, doctor_id, nombre)
    if detalle:
        mensaje = f"{mensaje} | detalle={detalle}"

    logger_nlp.debug(mensaje)


def registrar_progreso(
    logger_nlp: logging.Logger,
    stats: dict,
    limite: int | None,
) -> None:
    """Registra un corte de progreso legible para ejecuciones largas."""
    requests = stats.get("requests_llm_realizados", 0)
    limite_txt = f"/{limite}" if limite is not None else ""
    logger_nlp.debug(
        "PROGRESO | revisados=%d | LLM=%d | locales=%d | skips=%d | errores=%d | requests=%d%s",
        stats.get("candidatos_revisados", 0),
        stats.get("procesados_llm", 0),
        stats.get("procesados_localmente", 0),
        stats.get("skips", 0),
        stats.get("errores", 0),
        requests,
        limite_txt,
    )


def registrar_resumen_final(
    logger_nlp: logging.Logger,
    stats: dict,
) -> None:
    """Registra el resumen consolidado de la ejecución al finalizar el pipeline."""
    total = stats.get("total", stats.get("candidatos_revisados", 0))
    candidatos = stats.get("candidatos_revisados", total)
    procesados_llm = stats.get("procesados_llm", stats.get("completados", 0))
    locales = stats.get("procesados_localmente", stats.get("sin_opiniones", 0))
    errores = stats.get("errores", 0)
    skips = stats.get("skips", 0)
    requests = stats.get("requests_llm_realizados", procesados_llm)
    limite = stats.get("limite_requests_llm")
    exitosos = stats.get("requests_llm_exitosos", procesados_llm)
    fallidos = stats.get("requests_llm_fallidos", 0)
    tiempo = stats.get("tiempo_segundos", 0.0)
    modelo = stats.get("modelo", "desconocido")
    modo = stats.get("modo", "desconocido")
    detenido_por = stats.get("detenido_por")

    minutos = int(tiempo // 60)
    segundos = int(tiempo % 60)
    promedio = f"{tiempo / candidatos:.1f}s/candidato" if candidatos > 0 else "N/A"
    limite_txt = f"/{limite}" if limite is not None else ""
    restantes = "N/A" if limite is None else max(int(limite) - int(requests), 0)

    bloque = (
        f"\n{'═' * 60}\n"
        f"  RESUMEN DE EJECUCIÓN — Pipeline NLP\n"
        f"{'─' * 60}\n"
        f"  Modelo:                    {modelo}\n"
        f"  Modo:                      {modo}\n"
        f"  Candidatos revisados:      {candidatos}\n"
        f"{'─' * 60}\n"
        f"  Procesados por LLM:        {procesados_llm}\n"
        f"  Procesados localmente:     {locales}\n"
        f"  Skips:                     {skips}\n"
        f"  Errores:                   {errores}\n"
        f"{'─' * 60}\n"
        f"  Requests reales al modelo: {requests}{limite_txt}\n"
        f"  Requests exitosos:         {exitosos}\n"
        f"  Requests fallidos:         {fallidos}\n"
        f"  Requests restantes:        {restantes}\n"
        f"{'─' * 60}\n"
        f"  Detenido por:              {detenido_por or 'finalización normal'}\n"
        f"  Tiempo total:              {minutos}m {segundos:02d}s\n"
        f"  Promedio:                  {promedio}\n"
        f"{'═' * 60}"
    )

    logger_nlp.info(bloque)
