"""
Pipeline CLI principal — Procesamiento masivo de opiniones con IA.

Script independiente para analizar las opiniones de especialistas médicos
usando múltiples modelos de IA y guardar resultados en MongoDB.

Uso:
    # Prueba con 10 médicos (SIEMPRE ejecutar esto primero)
    python -m app.nlp.analizador_pipeline --prueba --limite 10

    # Ejecutar para una especialidad específica
    python -m app.nlp.analizador_pipeline --especialidad Endodoncia

    # Ejecutar para todos los especialistas
    python -m app.nlp.analizador_pipeline --todos

    # Solo los que fallaron o están pendientes
    python -m app.nlp.analizador_pipeline --reintentar-errores

    # Usar modelo específico (sobreescribe MODELO_ACTIVO del .env)
    python -m app.nlp.analizador_pipeline --todos --modelo deepseek

Variables de entorno requeridas en .env:
    - MODELO_ACTIVO: Modelo por defecto (groq|deepseek|gemini|minimax|ollama)
    - MONGO_URL: URL de conexión a MongoDB
    - MONGO_DB: Nombre de la base de datos
    - Variables específicas del modelo activo (ver documentación de cada modelo)
"""

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from threading import Semaphore

from dotenv import load_dotenv

# ── Cargar variables de entorno ──
load_dotenv()

from app.db.mongo import get_mongo_db
from app.nlp.modelos import obtener_modelo
from app.nlp.nlp_logger import (
    iniciar_sesion_log,
    registrar_respuesta_cruda,
    registrar_resumen_final,
)
from app.nlp.preprocesador import preparar_datos_para_analisis
from app.nlp.prompt_builder import (
    construir_analisis_minimo,
    construir_prompt_sistema,
    construir_prompt_usuario,
)
from app.nlp.repositorios.analisis_repo import (
    analisis_existente_reciente,
    guardar_analisis,
    listar_pendientes,
    marcar_error,
)

# ── Configuración de logging ──
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("analizador_pipeline")

# Nivel SUCCESS personalizado
SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")


def _log_success(mensaje: str) -> None:
    """Log con nivel SUCCESS personalizado."""
    logger.log(SUCCESS, mensaje)


# ── Versión del prompt ──
VERSION_PROMPT = "v1"

# ── Logger NLP (se inicializa en main) ──
_logger_nlp = None


def _parsear_argumentos() -> argparse.Namespace:
    """
    Parsea los argumentos de línea de comandos.

    Retorna
    -------
    argparse.Namespace
        Argumentos parseados con todos los flags del pipeline.
    """
    parser = argparse.ArgumentParser(
        description="Analizador masivo de opiniones de especialistas médicos con IA",
    )
    parser.add_argument(
        "--prueba",
        action="store_true",
        default=False,
        help="Activa modo prueba",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=10,
        help="Médicos a procesar (en modo prueba o para limitar). Default: 10",
    )
    parser.add_argument(
        "--especialidad",
        type=str,
        default=None,
        help="Filtra por especialidad",
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        default=False,
        help="Procesa todos los especialistas",
    )
    parser.add_argument(
        "--reintentar-errores",
        action="store_true",
        default=False,
        help="Solo procesa los que tienen estado=error",
    )
    parser.add_argument(
        "--modelo",
        type=str,
        default=None,
        help="Sobreescribe MODELO_ACTIVO del .env",
    )
    parser.add_argument(
        "--concurrencia",
        type=int,
        default=5,
        help="Máximo de llamadas paralelas a la IA. Default: 5",
    )
    parser.add_argument(
        "--pausa-entre-lotes",
        type=float,
        default=2.0,
        help="Segundos entre lotes (respetar rate limits). Default: 2.0",
    )

    return parser.parse_args()


def _obtener_especialistas(args: argparse.Namespace) -> list[dict]:
    """
    Obtiene la lista de especialistas a procesar según los argumentos CLI.

    Parámetros
    ----------
    args : argparse.Namespace
        Argumentos parseados del CLI.

    Retorna
    -------
    list[dict]
        Lista de documentos de especialistas desde MongoDB.
    """
    db = get_mongo_db()

    if args.reintentar_errores:
        # Obtener doctor_ids con errores del repo de análisis
        pendientes = listar_pendientes(limite=args.limite if args.prueba else 50000)
        doctor_ids = [p["doctor_id"] for p in pendientes if "doctor_id" in p]
        if not doctor_ids:
            return []
        cursor = db["especialistas"].find(
            {"doctoralia_id": {"$in": doctor_ids}}
        )
        return list(cursor)

    filtro: dict = {}
    if args.especialidad:
        filtro["especialidad"] = {
            "$regex": args.especialidad, "$options": "i"
        }

    cursor = db["especialistas"].find(filtro)

    if args.prueba or not args.todos:
        cursor = cursor.limit(args.limite)

    return list(cursor)


def _obtener_opiniones_doctor(doctor_id: int) -> list[dict]:
    """
    Obtiene las opiniones de un doctor desde MongoDB (síncrono).

    Parámetros
    ----------
    doctor_id : int
        Identificador del doctor en Doctoralia.

    Retorna
    -------
    list[dict]
        Lista de opiniones ordenadas por fecha descendente.
    """
    db = get_mongo_db()
    cursor = db["opiniones"].find(
        {"doctor_id": doctor_id}
    ).sort("fecha_publicacion", -1)
    return list(cursor)


def _es_clinica(especialista: dict) -> bool:
    """
    Determina si el especialista es en realidad una clínica o centro médico.

    Parámetros
    ----------
    especialista : dict
        Documento del especialista desde MongoDB.

    Retorna
    -------
    bool
        True si la URL corresponde a una clínica o centro médico, False en caso contrario.
    """
    url = (especialista.get("scraping_meta") or {}).get("url_origen", "")
    return "/clinicas/" in url or "/centros-medicos/" in url


def _procesar_especialista(
    especialista: dict,
    modelo,
    prompt_sistema: str,
    semaforo: Semaphore,
) -> dict:
    """
    Procesa un especialista individual: preprocesa, analiza con IA y guarda.

    Parámetros
    ----------
    especialista : dict
        Documento del especialista desde MongoDB.
    modelo : BaseModelo
        Instancia del modelo de IA a usar.
    prompt_sistema : str
        Prompt del sistema pre-construido.
    semaforo : Semaphore
        Semáforo para controlar concurrencia de llamadas a la IA.

    Retorna
    -------
    dict
        Resultado del procesamiento con estado y detalles.
    """
    global _logger_nlp

    doctor_id = especialista.get("doctoralia_id", 0)
    nombre = especialista.get("nombre", "Sin nombre")

    resultado = {
        "doctor_id": doctor_id,
        "nombre": nombre,
        "estado": "error",
        "detalle": "",
    }

    # Verificar si es clínica
    if _es_clinica(especialista):
        logger.info(
            f"{nombre} | id={doctor_id} | skip → es clínica, se procesará en fase 2"
        )
        resultado["estado"] = "skip"
        resultado["detalle"] = "es clínica"
        return resultado

    try:
        # Verificar análisis reciente
        if analisis_existente_reciente(doctor_id):
            resultado["estado"] = "skip"
            resultado["detalle"] = "análisis reciente existente"
            return resultado

        # Obtener opiniones
        opiniones = _obtener_opiniones_doctor(doctor_id)

        # Preprocesar
        datos = preparar_datos_para_analisis(especialista, opiniones)

        # Si no es apto para IA → análisis mínimo
        if not datos["apto_para_ia"]:
            razon = datos["razon_no_apto"] or "desconocida"
            analisis_minimo = construir_analisis_minimo(especialista, razon)

            doc_guardar = {
                "doctor_id": doctor_id,
                "doctoralia_id": doctor_id,
                "nombre_especialista": nombre,
                "especialidad": especialista.get("especialidad", ""),
                "estado": "sin_opiniones",
                "fecha_analisis": datetime.now(timezone.utc),
                "modelo_usado": "ninguno",
                "version_prompt": VERSION_PROMPT,
                "metricas_locales": datos["metricas_locales"],
                "alertas_preprocesamiento": datos["alertas"],
                "resultado_ia": analisis_minimo,
                "error_detalle": None,
            }
            guardar_analisis(doc_guardar)

            resultado["estado"] = "sin_opiniones"
            resultado["detalle"] = razon
            logger.warning(
                "%s | id=%d | %s → análisis mínimo generado",
                nombre, doctor_id, razon,
            )
            return resultado

        # Log de sospecha de fraude si aplica
        if datos["metricas_locales"].get("sospecha_fraude"):
            logger.warning(
                "%s | id=%d | sospecha_fraude detectada localmente",
                nombre, doctor_id,
            )

        # Construir prompt de usuario
        prompt_usuario = construir_prompt_usuario(datos)

        # Llamar al modelo con semáforo
        respuesta_raw = None
        with semaforo:
            try:
                respuesta_raw = modelo.analizar(prompt_sistema, prompt_usuario)
            except Exception as e:
                logger.error(
                    "%s | id=%d | Error en modelo: %s",
                    nombre, doctor_id, str(e),
                )
                marcar_error(doctor_id, f"Error en modelo: {str(e)}")
                resultado["detalle"] = str(e)
                return resultado

        # Parsear respuesta JSON
        resultado_ia = None
        try:
            resultado_ia = modelo.parsear_respuesta(respuesta_raw)

            # ── Registrar respuesta cruda exitosa ──
            if _logger_nlp and respuesta_raw:
                registrar_respuesta_cruda(
                    _logger_nlp, doctor_id, nombre, respuesta_raw, exito=True,
                )

        except ValueError:
            # ── Registrar respuesta cruda fallida ──
            if _logger_nlp and respuesta_raw:
                registrar_respuesta_cruda(
                    _logger_nlp, doctor_id, nombre, respuesta_raw, exito=False,
                )

            # Reintentar una vez con el mismo prompt
            logger.warning(
                "%s | id=%d | JSON inválido, reintentando...",
                nombre, doctor_id,
            )
            try:
                with semaforo:
                    respuesta_raw = modelo.analizar(
                        prompt_sistema, prompt_usuario
                    )
                resultado_ia = modelo.parsear_respuesta(respuesta_raw)

                # ── Registrar respuesta cruda del reintento exitoso ──
                if _logger_nlp and respuesta_raw:
                    registrar_respuesta_cruda(
                        _logger_nlp, doctor_id, nombre, respuesta_raw,
                        exito=True,
                    )

            except (ValueError, Exception) as e2:
                # ── Registrar respuesta cruda del reintento fallido ──
                if _logger_nlp and respuesta_raw:
                    registrar_respuesta_cruda(
                        _logger_nlp, doctor_id, nombre, respuesta_raw,
                        exito=False,
                    )

                logger.error(
                    "%s | id=%d | Fallo en reintento: %s",
                    nombre, doctor_id, str(e2),
                )
                marcar_error(
                    doctor_id,
                    f"JSON inválido tras reintento: {str(e2)}"
                )
                resultado["detalle"] = f"JSON inválido: {str(e2)}"
                return resultado

        # Determinar estado final
        estado = "completado"
        if datos["metricas_locales"].get("sospecha_fraude"):
            estado = "sospecha_fraude"

        doc_guardar = {
            "doctor_id": doctor_id,
            "doctoralia_id": doctor_id,
            "nombre_especialista": nombre,
            "especialidad": especialista.get("especialidad", ""),
            "estado": estado,
            "fecha_analisis": datetime.now(timezone.utc),
            "modelo_usado": modelo.nombre_modelo().split(" ")[0],
            "version_prompt": VERSION_PROMPT,
            "metricas_locales": datos["metricas_locales"],
            "alertas_preprocesamiento": datos["alertas"],
            "resultado_ia": resultado_ia,
            "error_detalle": None,
        }
        guardar_analisis(doc_guardar)

        score = resultado_ia.get("puntuacion_recomendacion", "N/A")
        confiabilidad = resultado_ia.get("confiabilidad_opiniones", "N/A")

        _log_success(
            f"{nombre} | id={doctor_id} | score={score} | "
            f"confiabilidad={confiabilidad}"
        )
        resultado["estado"] = estado
        resultado["detalle"] = f"score={score}"

    except Exception as e:
        logger.error(
            "%s | id=%d | Error inesperado: %s",
            nombre, doctor_id, str(e),
        )
        marcar_error(doctor_id, f"Error inesperado: {str(e)}")
        resultado["detalle"] = str(e)

    return resultado


def main() -> None:
    """Punto de entrada principal del pipeline CLI."""
    global _logger_nlp

    args = _parsear_argumentos()

    # ── Log de inicio ──
    logger.info("Analizador de opiniones — Iniciando")

    # ── Inicializar modelo ──
    nombre_modelo = args.modelo
    modelo = obtener_modelo(nombre_modelo)
    logger.info("Modelo activo: %s", modelo.nombre_modelo())

    # ── Determinar modo ──
    if args.prueba:
        modo = f"prueba | Límite: {args.limite} médicos"
        modo_log = "prueba"
    elif args.reintentar_errores:
        modo = "reintentar errores"
        modo_log = "reintentar"
    elif args.especialidad:
        modo = f"especialidad: {args.especialidad}"
        modo_log = "especialidad"
    elif args.todos:
        modo = "todos los especialistas"
        modo_log = "masivo"
    else:
        modo = f"limitado a {args.limite} médicos"
        modo_log = "limitado"

    logger.info("Modo: %s", modo)

    # ── Iniciar logger NLP dedicado ──
    modelo_corto = modelo.nombre_modelo().split(" ")[0]
    _logger_nlp = iniciar_sesion_log(
        modelo=modelo_corto,
        modo=modo_log,
        particion="completo",
    )
    _logger_nlp.info("Modelo activo: %s", modelo.nombre_modelo())
    _logger_nlp.info("Modo: %s", modo)

    # ── Obtener especialistas ──
    especialistas = _obtener_especialistas(args)
    total_especialistas = len(especialistas)
    logger.info("Especialistas encontrados: %d", total_especialistas)
    _logger_nlp.info("Especialistas encontrados: %d", total_especialistas)

    if total_especialistas == 0:
        logger.info("No hay especialistas para procesar. Finalizando.")
        return

    # ── Preparar ejecución ──
    prompt_sistema = construir_prompt_sistema()
    semaforo = Semaphore(args.concurrencia)
    tiempo_inicio = time.time()

    # Contadores
    completados = 0
    sin_opiniones = 0
    errores = 0
    skips = 0

    # ── Procesar con ThreadPoolExecutor ──
    with ThreadPoolExecutor(max_workers=args.concurrencia) as executor:
        futuros = {}
        procesados = 0

        for i, esp in enumerate(especialistas):
            futuro = executor.submit(
                _procesar_especialista,
                esp,
                modelo,
                prompt_sistema,
                semaforo,
            )
            futuros[futuro] = esp

            # Pausa entre lotes para respetar rate limits
            if (i + 1) % args.concurrencia == 0 and i < total_especialistas - 1:
                time.sleep(args.pausa_entre_lotes)

        for futuro in as_completed(futuros):
            procesados += 1

            try:
                resultado = futuro.result()
                estado = resultado.get("estado", "error")

                if estado in ("completado", "sospecha_fraude"):
                    completados += 1
                elif estado == "sin_opiniones":
                    sin_opiniones += 1
                elif estado == "skip":
                    skips += 1
                else:
                    errores += 1
            except Exception as e:
                errores += 1
                logger.error("Error en futuro: %s", str(e))

            # Log de progreso cada 50 médicos
            if procesados % 50 == 0:
                logger.info(
                    "Progreso: %d/%d procesados | "
                    "Completados: %d | Sin opiniones: %d | "
                    "Errores: %d | Skips: %d",
                    procesados, total_especialistas,
                    completados, sin_opiniones, errores, skips,
                )
                _logger_nlp.info(
                    "Progreso: %d/%d procesados | "
                    "Completados: %d | Sin opiniones: %d | "
                    "Errores: %d | Skips: %d",
                    procesados, total_especialistas,
                    completados, sin_opiniones, errores, skips,
                )

    # ── Resumen final ──
    tiempo_total = time.time() - tiempo_inicio
    minutos = int(tiempo_total // 60)
    segundos = int(tiempo_total % 60)

    promedio = (
        f"{tiempo_total / total_especialistas:.1f}s/médico"
        if total_especialistas > 0
        else "N/A"
    )

    logger.info("══════════════════════════════════")

    tipo_fin = "PRUEBA FINALIZADA" if args.prueba else "PROCESAMIENTO FINALIZADO"
    _log_success(
        f"{tipo_fin} — {total_especialistas} médicos procesados"
    )
    logger.info(
        "Completados: %d | Sin opiniones: %d | Errores: %d | Skips: %d",
        completados, sin_opiniones, errores, skips,
    )
    logger.info(
        "Tiempo total: %dm %02ds | Promedio: %s",
        minutos, segundos, promedio,
    )

    # ── Registrar resumen en el logger NLP ──
    registrar_resumen_final(_logger_nlp, {
        "total": total_especialistas,
        "completados": completados,
        "sin_opiniones": sin_opiniones,
        "errores": errores,
        "skips": skips,
        "tiempo_segundos": tiempo_total,
        "modelo": modelo.nombre_modelo(),
        "modo": modo,
    })


if __name__ == "__main__":
    main()
