"""
Pipeline CLI principal — Procesamiento masivo de opiniones con IA.
"""

import argparse
import logging
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone

try:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
except ModuleNotFoundError:

    def load_dotenv(*args, **kwargs):
        return False


load_dotenv()

from app.db.mongo import get_mongo_db
from app.nlp.estado_ejecucion import EstadisticasNLP, actualizar_estadisticas
from app.nlp.modelos import obtener_modelo
from app.nlp.modelos.base_modelo import ErrorProveedorFatal, LimiteRequestsLLMAlcanzado
from app.nlp.nlp_logger import (
    iniciar_sesion_log,
    registrar_evento_candidato,
    registrar_evento_llm,
    registrar_progreso,
    registrar_respuesta_cruda,
    registrar_resumen_final,
)
from app.nlp.preprocesador import preparar_datos_para_analisis
from app.nlp.prompt_builder import (
    construir_analisis_minimo,
    construir_prompt_sistema,
    construir_prompt_usuario,
    reforzar_resultado_analisis,
)
from app.nlp.repositorios.analisis_repo import (
    guardar_analisis,
    listar_ids_finalizados_recientes,
    listar_pendientes,
    marcar_error,
)
from app.scraper.utils.estado_pipeline import (
    cargar_estado,
    guardar_resumen_nlp,
    marcar_detencion_nlp,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("analizador_pipeline")

SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")
VERSION_PROMPT = "v2"
PERSISTIR_ESTADO_CADA_CANDIDATOS = 50
_logger_nlp = None


def _log_success(mensaje: str) -> None:
    logger.log(SUCCESS, mensaje)


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analizador masivo de opiniones de especialistas médicos con IA",
    )
    parser.add_argument(
        "--prueba", action="store_true", default=False, help="Activa modo prueba"
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help=(
            "Máximo de requests reales al LLM. Si no se especifica: 10 en modo prueba/limitado; "
            "sin límite en --todos."
        ),
    )
    parser.add_argument(
        "--especialidad", type=str, default=None, help="Filtra por especialidad"
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
        help="Solo procesa estado=error",
    )
    parser.add_argument(
        "--modelo", type=str, default=None, help="Sobreescribe MODELO_ACTIVO del .env"
    )
    parser.add_argument(
        "--min-opiniones-ia",
        type=int,
        default=5,
        help="Mínimo de opiniones descargadas en Mongo para llamar al modelo. Default: 5.",
    )
    parser.add_argument(
        "--reanalizar-sospecha-fraude",
        action="store_true",
        default=False,
        help=(
            "No trata estado=sospecha_fraude reciente como finalizado, para regenerarlo "
            "con el modelo IA bajo los criterios actuales."
        ),
    )
    parser.add_argument(
        "--concurrencia",
        type=int,
        default=5,
        help="Reservado para compatibilidad; el corte por requests reales se ejecuta secuencialmente.",
    )
    parser.add_argument(
        "--pausa-entre-lotes",
        type=float,
        default=2.0,
        help="Pausa entre requests LLM reales",
    )
    parser.add_argument(
        "--forzar-reanalisis",
        action="store_true",
        default=False,
        help="Recalcula aunque exista análisis finalizado reciente. Úsalo solo para cambios de prompt/modelo.",
    )
    return parser.parse_args()


def _limite_efectivo(args: argparse.Namespace) -> int | None:
    if args.limite is not None:
        return args.limite
    if args.todos:
        return None
    return 10


def _limite_scan(args: argparse.Namespace, limite_llm: int | None) -> int | None:
    if args.todos:
        return None
    if limite_llm is None:
        return None
    return max(limite_llm * 20, 100)


def _obtener_especialistas(
    args: argparse.Namespace, limite_llm: int | None
) -> list[dict]:
    db = get_mongo_db()
    limite_consulta = _limite_scan(args, limite_llm)

    if args.reintentar_errores:
        pendientes = listar_pendientes(limite=limite_consulta or 50000)
        doctor_ids = [p["doctor_id"] for p in pendientes if "doctor_id" in p]
        if not doctor_ids:
            return []
        cursor = db["especialistas"].find({"doctoralia_id": {"$in": doctor_ids}})
        return list(cursor)

    filtro: dict = {}
    if args.especialidad:
        filtro["especialidad"] = {"$regex": args.especialidad, "$options": "i"}

    cursor = db["especialistas"].find(filtro)
    if limite_consulta:
        cursor = cursor.limit(limite_consulta)
    return list(cursor)


def _obtener_opiniones_doctor(doctor_id: int) -> list[dict]:
    db = get_mongo_db()
    cursor = (
        db["opiniones"].find({"doctor_id": doctor_id}).sort("fecha_publicacion", -1)
    )
    return list(cursor)


def _es_clinica(especialista: dict) -> bool:
    scraping_meta = especialista.get("scraping_meta") or {}
    url = (
        scraping_meta.get("url_origen", "")
        if isinstance(scraping_meta, dict)
        else str(scraping_meta)
    )
    return "/clinicas/" in url or "/centros-medicos/" in url


def _doc_base(
    especialista: dict,
    doctor_id: int,
    nombre: str,
    estado: str,
    datos: dict,
    resultado_ia: dict,
    modelo_usado: str,
) -> dict:
    return {
        "doctor_id": doctor_id,
        "doctoralia_id": doctor_id,
        "nombre_especialista": nombre,
        "especialidad": especialista.get("especialidad", ""),
        "estado": estado,
        "fecha_analisis": datetime.now(timezone.utc),
        "modelo_usado": modelo_usado,
        "version_prompt": VERSION_PROMPT,
        "metricas_locales": datos.get("metricas_locales", {}),
        "metadatos_muestreo": datos.get("metadatos_muestreo", {}),
        "perfil_limpio": datos.get("perfil_limpio", {}),
        "alertas_preprocesamiento": datos.get("alertas", []),
        "resultado_ia": resultado_ia,
        "error_detalle": None,
        "fatal_proveedor": False,
    }


def _resultado(
    doctor_id: int,
    nombre: str,
    estado: str,
    detalle: str = "",
    requests_antes: int = 0,
    requests_despues: int = 0,
    fatal: bool = False,
) -> dict:
    consumidos = max(requests_despues - requests_antes, 0)
    return {
        "doctor_id": doctor_id,
        "nombre": nombre,
        "estado": estado,
        "detalle": detalle,
        "requests_consumidos": consumidos,
        "llm_realizado": consumidos > 0,
        "llm_exitoso": estado in ("completado",) and consumidos > 0,
        "fatal_proveedor": fatal,
    }


def _procesar_especialista(
    especialista: dict,
    modelo,
    prompt_sistema: str,
    analisis_finalizados: set[int],
    forzar_reanalisis: bool,
    min_opiniones_ia: int,
) -> dict:
    global _logger_nlp

    doctor_id = especialista.get("doctoralia_id", 0)
    nombre = especialista.get("nombre", "Sin nombre")
    requests_antes = modelo.requests_remotos_realizados

    if _es_clinica(especialista):
        logger.info("%s | id=%d | skip → es clínica", nombre, doctor_id)
        return _resultado(
            doctor_id,
            nombre,
            "skip",
            "es clínica",
            requests_antes,
            modelo.requests_remotos_realizados,
        )

    try:
        if not forzar_reanalisis:
            if doctor_id in analisis_finalizados:
                return _resultado(
                    doctor_id,
                    nombre,
                    "skip",
                    "análisis finalizado reciente",
                    requests_antes,
                    modelo.requests_remotos_realizados,
                )

        opiniones = _obtener_opiniones_doctor(doctor_id)
        datos = preparar_datos_para_analisis(
            especialista,
            opiniones,
            min_opiniones_ia=min_opiniones_ia,
        )

        if not datos["apto_para_ia"]:
            razon = datos["razon_no_apto"] or "desconocida"
            analisis_minimo = construir_analisis_minimo(especialista, razon)
            guardar_analisis(
                _doc_base(
                    especialista,
                    doctor_id,
                    nombre,
                    "sin_opiniones",
                    datos,
                    analisis_minimo,
                    "ninguno",
                )
            )
            logger.warning("%s | id=%d | %s → análisis local", nombre, doctor_id, razon)
            return _resultado(
                doctor_id,
                nombre,
                "sin_opiniones",
                razon,
                requests_antes,
                modelo.requests_remotos_realizados,
            )

        if datos["metricas_locales"].get("sospecha_fraude"):
            razones = datos["metricas_locales"].get("razones_fraude", [])
            logger.warning(
                "%s | id=%d | sospecha_fraude local → se enviará al LLM con penalización contextual: %s",
                nombre,
                doctor_id,
                "; ".join(razones[:2]) or "sin detalle",
            )

        prompt_usuario = construir_prompt_usuario(datos)
        respuesta_raw = None
        try:
            if _logger_nlp:
                registrar_evento_llm(_logger_nlp, doctor_id, nombre, "request_inicio")
            respuesta_raw = modelo.analizar(prompt_sistema, prompt_usuario)
        except (ErrorProveedorFatal, LimiteRequestsLLMAlcanzado) as exc:
            requests_despues = modelo.requests_remotos_realizados
            detalle = str(exc)
            logger.error(
                "%s | id=%d | detención proveedor/límite: %s",
                nombre,
                doctor_id,
                detalle,
            )
            if _logger_nlp:
                registrar_evento_llm(
                    _logger_nlp, doctor_id, nombre, "error_fatal_modelo", detalle
                )
            marcar_error(doctor_id, f"Error fatal/límite en modelo: {detalle}")
            return _resultado(
                doctor_id,
                nombre,
                "error",
                detalle,
                requests_antes,
                requests_despues,
                fatal=isinstance(exc, ErrorProveedorFatal),
            )
        except Exception as exc:
            requests_despues = modelo.requests_remotos_realizados
            logger.error(
                "%s | id=%d | Error en modelo: %s", nombre, doctor_id, str(exc)
            )
            if _logger_nlp:
                registrar_evento_llm(
                    _logger_nlp, doctor_id, nombre, "error_modelo", str(exc)
                )
            marcar_error(doctor_id, f"Error en modelo: {str(exc)}")
            return _resultado(
                doctor_id, nombre, "error", str(exc), requests_antes, requests_despues
            )

        try:
            resultado_ia = modelo.parsear_respuesta(respuesta_raw)
            if _logger_nlp:
                registrar_evento_llm(_logger_nlp, doctor_id, nombre, "parse_ok")
            if _logger_nlp and respuesta_raw:
                registrar_respuesta_cruda(
                    _logger_nlp, doctor_id, nombre, respuesta_raw, exito=True
                )
        except ValueError:
            if _logger_nlp and respuesta_raw:
                registrar_respuesta_cruda(
                    _logger_nlp, doctor_id, nombre, respuesta_raw, exito=False
                )
            logger.warning(
                "%s | id=%d | JSON inválido, reintentando...", nombre, doctor_id
            )
            if _logger_nlp:
                registrar_evento_llm(
                    _logger_nlp,
                    doctor_id,
                    nombre,
                    "json_invalido",
                    "primer intento no pudo parsearse",
                )
            try:
                if _logger_nlp:
                    registrar_evento_llm(
                        _logger_nlp, doctor_id, nombre, "reintento_inicio"
                    )
                respuesta_raw = modelo.analizar(prompt_sistema, prompt_usuario)
                resultado_ia = modelo.parsear_respuesta(respuesta_raw)
                if _logger_nlp and respuesta_raw:
                    registrar_respuesta_cruda(
                        _logger_nlp, doctor_id, nombre, respuesta_raw, exito=True
                    )
            except (ErrorProveedorFatal, LimiteRequestsLLMAlcanzado) as exc:
                requests_despues = modelo.requests_remotos_realizados
                if _logger_nlp:
                    registrar_evento_llm(
                        _logger_nlp,
                        doctor_id,
                        nombre,
                        "error_fatal_reintento",
                        str(exc),
                    )
                marcar_error(doctor_id, f"Error fatal/límite en reintento: {str(exc)}")
                return _resultado(
                    doctor_id,
                    nombre,
                    "error",
                    str(exc),
                    requests_antes,
                    requests_despues,
                    fatal=isinstance(exc, ErrorProveedorFatal),
                )
            except Exception as exc:
                requests_despues = modelo.requests_remotos_realizados
                if _logger_nlp and respuesta_raw:
                    registrar_respuesta_cruda(
                        _logger_nlp, doctor_id, nombre, respuesta_raw, exito=False
                    )
                if _logger_nlp:
                    registrar_evento_llm(
                        _logger_nlp, doctor_id, nombre, "error_reintento", str(exc)
                    )
                marcar_error(doctor_id, f"JSON inválido tras reintento: {str(exc)}")
                return _resultado(
                    doctor_id,
                    nombre,
                    "error",
                    f"JSON inválido: {str(exc)}",
                    requests_antes,
                    requests_despues,
                )

        resultado_ia = reforzar_resultado_analisis(resultado_ia, datos)
        doc_guardar = _doc_base(
            especialista,
            doctor_id,
            nombre,
            "completado",
            datos,
            resultado_ia,
            modelo.nombre_modelo().split(" ")[0],
        )
        guardar_analisis(doc_guardar)

        score = resultado_ia.get("puntuacion_recomendacion", "N/A")
        confiabilidad = resultado_ia.get("confiabilidad_opiniones", "N/A")
        _log_success(
            f"{nombre} | id={doctor_id} | score={score} | confiabilidad={confiabilidad}"
        )
        return _resultado(
            doctor_id,
            nombre,
            "completado",
            f"score={score}",
            requests_antes,
            modelo.requests_remotos_realizados,
        )

    except Exception as exc:
        logger.error("%s | id=%d | Error inesperado: %s", nombre, doctor_id, str(exc))
        if _logger_nlp:
            registrar_evento_llm(
                _logger_nlp, doctor_id, nombre, "error_inesperado", str(exc)
            )
        marcar_error(doctor_id, f"Error inesperado: {str(exc)}")
        return _resultado(
            doctor_id,
            nombre,
            "error",
            str(exc),
            requests_antes,
            modelo.requests_remotos_realizados,
        )


def _stats_dict(
    stats: EstadisticasNLP, tiempo_total: float, modelo_nombre: str, modo: str
) -> dict:
    data = asdict(stats)
    data.update(
        {
            "total": stats.candidatos_revisados,
            "tiempo_segundos": tiempo_total,
            "modelo": modelo_nombre,
            "modo": modo,
        }
    )
    return data


def main() -> None:
    global _logger_nlp

    args = _parsear_argumentos()
    limite_llm = _limite_efectivo(args)

    logger.info("Analizador de opiniones — Iniciando")
    modelo = obtener_modelo(args.modelo)
    modelo.configurar_limite_requests(limite_llm)
    logger.info("Modelo activo: %s", modelo.nombre_modelo())

    if args.prueba:
        modo = f"prueba | Límite requests LLM: {limite_llm}"
        modo_log = "prueba"
    elif args.reintentar_errores:
        modo = f"reintentar errores | Límite requests LLM: {limite_llm or 'sin límite'}"
        modo_log = "reintentar"
    elif args.especialidad:
        modo = f"especialidad: {args.especialidad} | Límite requests LLM: {limite_llm or 'sin límite'}"
        modo_log = "especialidad"
    elif args.todos:
        modo = f"todos los especialistas | Límite requests LLM: {limite_llm or 'sin límite'}"
        modo_log = "masivo"
    else:
        modo = f"limitado | Límite requests LLM: {limite_llm}"
        modo_log = "limitado"
    logger.info("Modo: %s", modo)
    logger.info("Mínimo opiniones para IA: %d", args.min_opiniones_ia)
    if args.reanalizar_sospecha_fraude:
        logger.info("Reanálisis de estado=sospecha_fraude habilitado")

    modelo_corto = modelo.nombre_modelo().split(" ")[0]
    _logger_nlp = iniciar_sesion_log(
        modelo=modelo_corto, modo=modo_log, particion="completo"
    )
    _logger_nlp.info("Modelo activo: %s", modelo.nombre_modelo())
    _logger_nlp.info("Modo: %s", modo)
    _logger_nlp.info("Mínimo opiniones para IA: %d", args.min_opiniones_ia)
    if args.reanalizar_sospecha_fraude:
        _logger_nlp.info("Reanálisis de estado=sospecha_fraude habilitado")

    estado_persistido = cargar_estado()
    analisis_finalizados = set()
    if not args.reanalizar_sospecha_fraude:
        analisis_finalizados.update(
            estado_persistido.get("nlp", {}).get("analisis_finalizados", [])
        )
    estados_finalizados = ("completado", "sin_opiniones")
    if not args.reanalizar_sospecha_fraude:
        estados_finalizados = ("completado", "sospecha_fraude", "sin_opiniones")
    analisis_finalizados.update(
        listar_ids_finalizados_recientes(estados_finalizados=estados_finalizados)
    )
    logger.info(
        "Análisis finalizados recientes precargados: %d", len(analisis_finalizados)
    )
    _logger_nlp.info(
        "Análisis finalizados recientes precargados: %d", len(analisis_finalizados)
    )
    especialistas = _obtener_especialistas(args, limite_llm)
    logger.info("Candidatos cargados para revisión: %d", len(especialistas))
    _logger_nlp.info("Candidatos cargados para revisión: %d", len(especialistas))
    if not especialistas:
        logger.info("No hay especialistas para procesar. Finalizando.")
        return

    prompt_sistema = construir_prompt_sistema()
    stats = EstadisticasNLP(limite_requests_llm=limite_llm)
    tiempo_inicio = time.time()
    exit_code = 0

    for especialista in especialistas:
        if limite_llm is not None and modelo.requests_remotos_realizados >= limite_llm:
            stats.detenido_por = "limite_requests_llm_alcanzado"
            estado_persistido = marcar_detencion_nlp(
                estado_persistido, stats.detenido_por
            )
            break

        stats.candidatos_revisados += 1
        resultado = _procesar_especialista(
            especialista,
            modelo,
            prompt_sistema,
            analisis_finalizados,
            args.forzar_reanalisis,
            args.min_opiniones_ia,
        )
        actualizar_estadisticas(stats, resultado)

        if _logger_nlp:
            registrar_evento_candidato(_logger_nlp, resultado)

        if resultado.get("estado") in (
            "completado",
            "sin_opiniones",
            "sospecha_fraude",
        ):
            doctor_id_finalizado = resultado["doctor_id"]
            if doctor_id_finalizado not in analisis_finalizados:
                analisis_finalizados.add(doctor_id_finalizado)
                finalizados_estado = estado_persistido.setdefault("nlp", {}).setdefault(
                    "analisis_finalizados", []
                )
                if doctor_id_finalizado not in finalizados_estado:
                    finalizados_estado.append(doctor_id_finalizado)

        tiempo_total = time.time() - tiempo_inicio
        debe_persistir_estado = (
            stats.candidatos_revisados % PERSISTIR_ESTADO_CADA_CANDIDATOS == 0
            or resultado.get("fatal_proveedor")
        )
        if debe_persistir_estado:
            estado_persistido = guardar_resumen_nlp(
                estado_persistido,
                _stats_dict(stats, tiempo_total, modelo.nombre_modelo(), modo),
            )

        if resultado.get("fatal_proveedor"):
            stats.detenido_por = f"fatal_proveedor: {resultado.get('detalle')}"
            estado_persistido = marcar_detencion_nlp(
                estado_persistido, stats.detenido_por, fatal_proveedor=True
            )
            exit_code = 2
            break

        if resultado.get("llm_realizado") and args.pausa_entre_lotes > 0:
            time.sleep(args.pausa_entre_lotes)

        if stats.candidatos_revisados % 50 == 0:
            logger.info(
                "Progreso: revisados=%d | LLM=%d | locales=%d | skips=%d | errores=%d | requests=%d%s",
                stats.candidatos_revisados,
                stats.procesados_llm,
                stats.procesados_localmente,
                stats.skips,
                stats.errores,
                stats.requests_llm_realizados,
                f"/{limite_llm}" if limite_llm is not None else "",
            )
            if _logger_nlp:
                registrar_progreso(_logger_nlp, asdict(stats), limite_llm)

    tiempo_total = time.time() - tiempo_inicio
    stats.requests_llm_realizados = modelo.requests_remotos_realizados
    resumen = _stats_dict(stats, tiempo_total, modelo.nombre_modelo(), modo)
    estado_persistido = guardar_resumen_nlp(estado_persistido, resumen)

    minutos = int(tiempo_total // 60)
    segundos = int(tiempo_total % 60)
    logger.info("══════════════════════════════════")
    tipo_fin = "PRUEBA FINALIZADA" if args.prueba else "PROCESAMIENTO FINALIZADO"
    if stats.detenido_por:
        tipo_fin = f"{tipo_fin} CON CORTE CONTROLADO"
    _log_success(f"{tipo_fin} — candidatos revisados: {stats.candidatos_revisados}")
    logger.info(
        "Procesados por LLM: %d | Locales sin LLM: %d | Skips: %d | Errores: %d",
        stats.procesados_llm,
        stats.procesados_localmente,
        stats.skips,
        stats.errores,
    )
    logger.info(
        "Requests reales al modelo: %d%s | exitosos: %d | fallidos: %d",
        stats.requests_llm_realizados,
        f"/{limite_llm}" if limite_llm is not None else "",
        stats.requests_llm_exitosos,
        stats.requests_llm_fallidos,
    )
    if stats.detenido_por:
        logger.error("Detenido por: %s", stats.detenido_por)
    logger.info("Tiempo total: %dm %02ds", minutos, segundos)

    registrar_resumen_final(_logger_nlp, resumen)
    if exit_code:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
