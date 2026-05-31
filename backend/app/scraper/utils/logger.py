"""
Módulo de logging para el pipeline masivo de scraping Doctoralia.

Escribe simultáneamente en consola (con colores ANSI) y en un archivo de texto
plano rotativo ubicado en ``logs/pipeline_YYYY-MM-DD.log``, relativo a la raíz
del proyecto.

Uso básico::

    from app.scraper.utils.logger import obtener_logger

    log = obtener_logger("pipeline")
    log.info("Iniciando fase 1")
    log.success("Catálogo cargado correctamente")
    log.warning("HTTP 429 recibido — reintentando")
    log.error("Timeout después de 3 intentos")
"""

import logging
import logging.handlers
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Nivel personalizado SUCCESS
# ---------------------------------------------------------------------------
SUCCESS_LEVEL = 25  # entre INFO (20) y WARNING (30)
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


def _agregar_metodo_success(logger_instance: logging.Logger) -> None:
    """Inyecta el método ``success()`` en una instancia de Logger.

    Args:
        logger_instance: Instancia de ``logging.Logger`` a la que se le añade
            el método personalizado.
    """

    def success(mensaje: str, *args, **kwargs) -> None:
        """Registra un mensaje con nivel SUCCESS.

        Args:
            mensaje: Texto del mensaje a registrar.
            *args: Argumentos posicionales adicionales para el formatter.
            **kwargs: Argumentos clave adicionales para el formatter.
        """
        if logger_instance.isEnabledFor(SUCCESS_LEVEL):
            logger_instance._log(SUCCESS_LEVEL, mensaje, args, **kwargs)

    logger_instance.success = success  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Colores ANSI para consola
# ---------------------------------------------------------------------------
_COLORES = {
    "DEBUG": "\033[37m",       # blanco tenue
    "INFO": "\033[97m",        # blanco brillante
    "SUCCESS": "\033[92m",     # verde
    "WARNING": "\033[93m",     # amarillo
    "ERROR": "\033[91m",       # rojo
    "CRITICAL": "\033[95m",    # magenta
    "RESET": "\033[0m",
}


class _FormatterColor(logging.Formatter):
    """Formatter que agrega colores ANSI según el nivel del mensaje.

    Usado exclusivamente para el handler de consola.

    Ejemplo de salida::

        [2026-05-27 14:30:00] [SUCCESS] Perfil guardado: Dr. Pérez | id=355439
    """

    FORMATO = "[%(asctime)s] [%(levelname)-7s] %(message)s"
    FECHA_FMT = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        """Aplica color ANSI al texto del nivel y formatea el registro.

        Guarda y restaura ``record.levelname`` para no contaminar otros
        handlers que procesen el mismo registro.

        Args:
            record: Registro de log a formatear.

        Returns:
            Cadena formateada con códigos de color ANSI.
        """
        color = _COLORES.get(record.levelname, _COLORES["RESET"])
        reset = _COLORES["RESET"]
        original = record.levelname
        record.levelname = f"{color}{original}{reset}"
        formatter = logging.Formatter(self.FORMATO, datefmt=self.FECHA_FMT)
        resultado = formatter.format(record)
        record.levelname = original
        return resultado


class _FormatterPlano(logging.Formatter):
    """Formatter de texto plano sin colores ANSI.

    Usado exclusivamente para el handler de archivo. Produce líneas legibles
    en cualquier editor de texto.

    Ejemplo de salida::

        [2026-05-27 14:30:00] [SUCCESS] Perfil guardado: Dr. Pérez | id=355439
    """

    FORMATO = "[%(asctime)s] [%(levelname)-7s] %(message)s"
    FECHA_FMT = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro sin códigos ANSI.

        Args:
            record: Registro de log a formatear.

        Returns:
            Cadena formateada en texto plano.
        """
        formatter = logging.Formatter(self.FORMATO, datefmt=self.FECHA_FMT)
        return formatter.format(record)


# ---------------------------------------------------------------------------
# Directorio de logs
# ---------------------------------------------------------------------------
_RAIZ_PROYECTO = Path(__file__).resolve().parents[3]
_DIR_LOGS = _RAIZ_PROYECTO / "logs"

# Registro de loggers ya configurados para evitar handlers duplicados
_loggers_configurados: set[str] = set()


def obtener_logger(nombre: str) -> logging.Logger:
    """Retorna un logger configurado con handlers de consola y archivo.

    Si el logger con ese nombre ya fue configurado anteriormente, lo retorna
    directamente sin agregar handlers adicionales.

    El archivo de log se crea (o se continúa) en::

        logs/pipeline_YYYY-MM-DD.log

    relativo a la raíz del proyecto. El directorio ``logs/`` se crea
    automáticamente si no existe.

    Args:
        nombre: Nombre del logger. Permite identificar el módulo que lo usa.

    Returns:
        Instancia de ``logging.Logger`` con nivel ``DEBUG`` y dos handlers:
        uno de consola con colores y uno de archivo con rotación diaria.

    Ejemplo::

        log = obtener_logger("pipeline")
        log.info("Iniciando...")
        log.success("Completado")
    """
    logger = logging.getLogger(nombre)

    if nombre in _loggers_configurados:
        _agregar_metodo_success(logger)
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # --- Handler consola ---
    handler_consola = logging.StreamHandler(sys.stdout)
    handler_consola.setLevel(logging.DEBUG)
    handler_consola.setFormatter(_FormatterColor())

    # --- Handler archivo rotativo diario ---
    _DIR_LOGS.mkdir(parents=True, exist_ok=True)
    handler_archivo = logging.handlers.TimedRotatingFileHandler(
        filename=_DIR_LOGS / "pipeline_.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        utc=False,
    )
    # El nombre del archivo activo se personaliza mediante el sufijo de rotación
    handler_archivo.suffix = "%Y-%m-%d"
    handler_archivo.namer = lambda name: str(
        _DIR_LOGS / f"pipeline_{Path(name).suffix.lstrip('.')}.log"
    )
    handler_archivo.setLevel(logging.DEBUG)
    handler_archivo.setFormatter(_FormatterPlano())

    logger.addHandler(handler_consola)
    logger.addHandler(handler_archivo)

    _loggers_configurados.add(nombre)
    _agregar_metodo_success(logger)

    return logger
