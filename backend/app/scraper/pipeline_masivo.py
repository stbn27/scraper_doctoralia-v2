"""
Pipeline masivo de scraping Doctoralia.

Ejecutar con::

    python -m app.scraper.pipeline_masivo [opciones]

Fases:
  1. Cargar catálogo desde fixtures/catalogo_doctoralia.json a Mongo (colección catalogos)
  2. Scrapear listados por especialidad+ciudad (todas las páginas)
  3. Scrapear perfil individual de cada médico del listado
  4. Scrapear opiniones de cada médico persistido

Uso::

    # Prueba con una especialidad (modo seguro):
    python -m app.scraper.pipeline_masivo --prueba --especialidad endodoncia --ciudad ciudad-de-mexico

    # Todo el catálogo:
    python -m app.scraper.pipeline_masivo --todo

    # Solo una fase:
    python -m app.scraper.pipeline_masivo --fase catalogo
    python -m app.scraper.pipeline_masivo --fase listados --especialidad endodoncia --ciudad ciudad-de-mexico

    # Reanudar:
    python -m app.scraper.pipeline_masivo --reanudar

    # Resetear estado y empezar desde cero:
    python -m app.scraper.pipeline_masivo --resetear-estado
"""

import asyncio
import json
import os
import random
import socket
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Autodetectar entorno local vs Docker para MongoDB ---
if not os.getenv("MONGO_URL"):
    try:
        socket.gethostbyname("mongodb")
    except socket.gaierror:
        # Fuera del contenedor de Docker (en la máquina host)
        os.environ["MONGO_URL"] = "mongodb://localhost:27017"

# pyrefly: ignore [missing-import]
import httpx

from app.scraper.utils.logger import obtener_logger
from app.scraper.utils.estado_pipeline import (
    cargar_estado,
    guardar_estado,
    resetear_estado,
    marcar_listado_completado,
    marcar_perfil_completado,
    marcar_opiniones_completadas,
    registrar_error,
    listado_ya_completado,
    establecer_sufijo_estado,
    perfil_ya_completado,
    opiniones_ya_completadas,
    guardar_cola_perfiles,
)
from app.scraper.utils.base import espera_humana, get_user_agent
from app.scraper.utils.rate_limiter import RateLimiter
from app.scraper.listing_scraper import scrape_listing_async
from app.scraper.doctoralia import fetch_and_parse_profile_async
from app.scraper.reviews_scraper import construir_resultado_opiniones
from app.db.repositorios.catalogos_repo import upsert_catalogos
from app.db.repositorios.doctor_profiles_repo import (
    upsert_perfil,
    buscar_por_id_doctoralia,
)
from app.db.repositorios.opiniones_repo import (
    insertar_opiniones_masivo,
    contar_opiniones_por_doctor,
)

# ---------------------------------------------------------------------------
# Rutas del proyecto
# ---------------------------------------------------------------------------
_RAIZ = Path(__file__).resolve().parents[2]
_FIXTURES = _RAIZ / "fixtures"
_CATALOGO_PATH = _FIXTURES / "catalogo_doctoralia.json"

# ---------------------------------------------------------------------------
# Rate limiter global (10 solicitudes / 60 segundos)
# ---------------------------------------------------------------------------
_rate_limiter = RateLimiter(max_requests=10, ventana_segundos=60)


# ===========================================================================
# FASE 1 — Catálogo
# ===========================================================================
async def fase_catalogo(estado: dict, log) -> dict:
    """Carga el catálogo local a la colección MongoDB ``catalogos``.

    Lee ``fixtures/catalogo_doctoralia.json``, extrae todos los pares
    presenciales y online y los sube a Mongo mediante upsert. Si el catálogo
    ya fue marcado como cargado en el estado, omite la fase.

    Args:
        estado: Estado actual del pipeline.
        log: Logger configurado del pipeline.

    Returns:
        Estado actualizado con ``catalogos_cargados = True``.
    """
    if estado.get("catalogos_cargados"):
        log.info("FASE 1 — Catálogo ya cargado anteriormente, omitiendo.")
        return estado

    log.info("FASE 1 — Cargando catálogo a Mongo...")

    if not _CATALOGO_PATH.exists():
        log.error(f"FASE 1 — Archivo no encontrado: {_CATALOGO_PATH}")
        return estado

    with _CATALOGO_PATH.open("r", encoding="utf-8") as f:
        catalogo = json.load(f)

    documentos = []
    for par in catalogo.get("pares_presencial", []):
        documentos.append({**par, "modalidad": "presencial"})
    for par in catalogo.get("pares_online", []):
        documentos.append({**par, "modalidad": "online"})

    if not documentos:
        log.warning("FASE 1 — El catálogo no tiene pares.")
        return estado

    try:
        resultado = await upsert_catalogos(documentos)
        log.success(  # type: ignore[attr-defined]
            f"Catálogo: {resultado['insertados']} pares insertados, "
            f"{resultado['actualizados']} ya existían"
        )
        estado["catalogos_cargados"] = True
        guardar_estado(estado)
    except Exception as exc:
        log.error(f"FASE 1 — Error al cargar catálogo: {exc}")

    return estado


# ===========================================================================
# FASE 2 — Listados
# ===========================================================================
async def _scrapear_par(
    par: dict,
    estado: dict,
    log,
    semaforo: asyncio.Semaphore,
    max_paginas: int | None,
) -> tuple[dict, list[dict]]:
    """Scrapea todas las páginas de un par especialidad+ciudad.

    Args:
        par: Diccionario con ``especialidad_slug``, ``ciudad_slug`` y ``url``.
        estado: Estado actual del pipeline.
        log: Logger configurado.
        semaforo: Semáforo asyncio para limitar concurrencia.
        max_paginas: Límite de páginas (para modo prueba). ``None`` = sin límite.

    Returns:
        Tupla ``(estado_actualizado, cola_perfiles)`` donde ``cola_perfiles``
        es la lista de médicos encontrados en el listado.
    """
    especialidad = par["especialidad_slug"]
    ciudad = par["ciudad_slug"]
    clave = f"{especialidad}/{ciudad}"
    cola: list[dict] = []

    if listado_ya_completado(estado, clave):
        log.info(f"Listado ya completado (omitiendo): {clave}")
        return estado, cola

    try:
        async with semaforo:
            await _rate_limiter.esperar_si_necesario()
            resultado, total_paginas = await scrape_listing_async(especialidad, ciudad, 1)

        doctores_pagina = resultado.get("doctores", [])
        total_paginas = total_paginas or 1
        if max_paginas:
            total_paginas = min(total_paginas, max_paginas)

        log.info(
            f"{clave} | Página 1/{total_paginas} — {len(doctores_pagina)} médicos"
        )
        for doc in doctores_pagina:
            if doc.get("doctoralia_id") and doc.get("url_perfil"):
                cola.append({
                    "doctoralia_id": doc["doctoralia_id"],
                    "url_perfil": doc["url_perfil"],
                    "nombre": doc.get("nombre") or "Desconocido",
                })

        for pagina in range(2, total_paginas + 1):
            await espera_humana(2.0, 5.0)
            try:
                async with semaforo:
                    await _rate_limiter.esperar_si_necesario()
                    resultado, _ = await scrape_listing_async(especialidad, ciudad, pagina)
                doctores_pagina = resultado.get("doctores", [])
                log.info(
                    f"{clave} | Página {pagina}/{total_paginas} — {len(doctores_pagina)} médicos"
                )
                for doc in doctores_pagina:
                    if doc.get("doctoralia_id") and doc.get("url_perfil"):
                        cola.append({
                            "doctoralia_id": doc["doctoralia_id"],
                            "url_perfil": doc["url_perfil"],
                            "nombre": doc.get("nombre") or "Desconocido",
                        })
            except Exception as exc:
                log.error(f"{clave} | Error en página {pagina}: {exc}")
                estado = registrar_error(estado, "listados", f"{clave}/p{pagina}", str(exc))

        log.success(  # type: ignore[attr-defined]
            f"Listado completado: {clave} — {len(cola)} médicos en cola"
        )
        estado = marcar_listado_completado(estado, clave)

    except Exception as exc:
        log.error(f"Error fatal en listado {clave}: {exc}")
        estado = registrar_error(estado, "listados", clave, str(exc))

    return estado, cola


async def fase_listados(
    estado: dict,
    log,
    pares: list[dict],
    semaforo: asyncio.Semaphore,
    max_paginas: int | None = None,
) -> tuple[dict, list[dict]]:
    """Scrapea los listados de médicos para todos los pares del catálogo.

    Itera secuencialmente por cada par especialidad+ciudad. Entre pares aplica
    una pausa de 60 segundos para no saturar el servidor. La cola de perfiles
    resultante es una lista en memoria con los datos mínimos para la Fase 3.

    Args:
        estado: Estado actual del pipeline.
        log: Logger configurado.
        pares: Lista de pares ``{especialidad_slug, ciudad_slug, url}``.
        semaforo: Semáforo asyncio para limitar concurrencia.
        max_paginas: Límite de páginas por par (para modo prueba).

    Returns:
        Tupla ``(estado_actualizado, cola_perfiles_total)``.
    """
    log.info(f"FASE 2 — Scraping listados ({len(pares)} pares)...")
    cola_total: list[dict] = []

    for i, par in enumerate(pares):
        estado, cola_par = await _scrapear_par(par, estado, log, semaforo, max_paginas)
        cola_total.extend(cola_par)

        # Pausa entre especialidades (excepto después del último, y solo si se realizó scraping real)
        if i < len(pares) - 1 and len(cola_par) > 0:
            log.info("Pausa entre especialidades — 60 segundos...")
            await asyncio.sleep(60)

    # Deduplicar por doctoralia_id
    vistos: set[int] = set()
    cola_unica: list[dict] = []
    for item in cola_total:
        did = item["doctoralia_id"]
        if did not in vistos:
            vistos.add(did)
            cola_unica.append(item)

    log.info(f"FASE 2 completada — {len(cola_unica)} médicos únicos en cola")

    # Persistir la cola en el estado para sobrevivir reinicios, pero no sobreescribir con una vacía si ya tenía perfiles importados
    if cola_unica:
        estado = guardar_cola_perfiles(estado, cola_unica)
    elif not estado.get("cola_perfiles"):
        estado = guardar_cola_perfiles(estado, [])

    return estado, cola_unica


# ===========================================================================
# FASE 3 — Perfiles
# ===========================================================================
async def _scrapear_perfil(
    item: dict,
    estado: dict,
    log,
    semaforo: asyncio.Semaphore,
) -> tuple[dict, bool]:
    """Descarga y persiste el perfil de un medico en ``doctor_profiles``.

    Construye el documento con la nueva estructura anidada (doctor, metadata,
    queue_meta) y lo guarda en la coleccion ``doctor_profiles`` de la BD
    Doctoralia (27017).

    Args:
        item: Diccionario con ``doctoralia_id``, ``url_perfil``, ``nombre`` y
            opcionalmente ``fuente_busqueda`` y ``discovery_sources``.
        estado: Estado actual del pipeline.
        log: Logger configurado.
        semaforo: Semaforo asyncio.

    Returns:
        Tupla ``(estado_actualizado, guardado)`` donde ``guardado`` es ``True``
        si el perfil se proceso (nuevo o actualizado), ``False`` si se omitio.
    """
    doctoralia_id = item["doctoralia_id"]
    url_perfil = item["url_perfil"]
    nombre = item.get("nombre", "Desconocido")
    fuente_busqueda = item.get("fuente_busqueda")
    discovery_sources = item.get("discovery_sources") or []

    if perfil_ya_completado(estado, doctoralia_id):
        log.info(f"Perfil omitido (estado): {nombre} | id={doctoralia_id}")
        return estado, False

    # Verificar antigüedad en Mongo (coleccion doctor_profiles)
    try:
        existente = await buscar_por_id_doctoralia(doctoralia_id)
        if existente:
            fecha_raw = (existente.get("metadata") or {}).get("fecha_consulta")
            if fecha_raw:
                try:
                    # fecha_consulta es string YYYY-MM-DD HH:MM:SS
                    from datetime import timedelta
                    fecha_consulta = datetime.strptime(fecha_raw, "%Y-%m-%d %H:%M:%S")
                    fecha_consulta = fecha_consulta.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) - fecha_consulta < timedelta(days=7):
                        log.warning(  # type: ignore[attr-defined]
                            f"Perfil omitido (reciente): {nombre} | id={doctoralia_id}"
                        )
                        estado = marcar_perfil_completado(estado, doctoralia_id)
                        return estado, False
                except (ValueError, TypeError):
                    pass
    except Exception:
        pass

    # Derivar priority_score del item (total_opiniones del listado)
    priority_score = item.get("total_opiniones") or item.get("num_opiniones") or 0
    # Fuente de busqueda como discovery source
    source_key = item.get("source_key")
    if source_key and source_key not in discovery_sources:
        discovery_sources = [*discovery_sources, source_key]

    # Reintentar ante HTTP 429
    for intento in range(2):
        try:
            async with semaforo:
                await _rate_limiter.esperar_si_necesario()
                datos = await fetch_and_parse_profile_async(
                    url_perfil,
                    id_doctoralia=doctoralia_id,
                    fuente_busqueda=fuente_busqueda,
                    discovery_sources=discovery_sources,
                    priority_score=priority_score,
                )

            await upsert_perfil(datos)
            log.success(  # type: ignore[attr-defined]
                f"Perfil guardado: {nombre} | id={doctoralia_id}"
            )
            estado = marcar_perfil_completado(estado, doctoralia_id)
            return estado, True

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 and intento == 0:
                log.warning(  # type: ignore[attr-defined]
                    f"HTTP 429 en perfil id={doctoralia_id} — pausa 5 min y reintento"
                )
                await asyncio.sleep(300)
                continue
            log.error(f"Error HTTP perfil id={doctoralia_id} | url={url_perfil} — {exc}")
            estado = registrar_error(estado, "perfiles", url_perfil, str(exc))
            return estado, False

        except Exception as exc:
            log.error(f"Error perfil id={doctoralia_id} | url={url_perfil} — {exc}")
            estado = registrar_error(estado, "perfiles", url_perfil, str(exc))
            return estado, False

    return estado, False


async def fase_perfiles(
    estado: dict,
    log,
    cola_perfiles: list[dict],
    semaforo: asyncio.Semaphore,
    max_perfiles: int | None = None,
) -> dict:
    """Descarga y persiste el perfil completo de cada médico en la cola.

    Aplica pausas humanas entre perfiles y una pausa mayor cada 20 perfiles
    procesados para evitar bloqueos. El modo prueba limita el número máximo.

    Args:
        estado: Estado actual del pipeline.
        log: Logger configurado.
        cola_perfiles: Lista de médicos a procesar.
        semaforo: Semáforo asyncio.
        max_perfiles: Límite de perfiles (para modo prueba). ``None`` = sin límite.

    Returns:
        Estado actualizado tras procesar todos los perfiles.
    """
    if max_perfiles:
        cola_perfiles = cola_perfiles[:max_perfiles]

    log.info(f"FASE 3 — Scraping perfiles ({len(cola_perfiles)} en cola)...")
    total_nuevos = 0
    total_omitidos = 0
    total_errores = 0

    for i, item in enumerate(cola_perfiles):
        estado, guardado = await _scrapear_perfil(item, estado, log, semaforo)

        if guardado:
            total_nuevos += 1
        else:
            total_omitidos += 1

        # Pausa entre perfiles (solo si realmente se realizó scraping web)
        if guardado and i < len(cola_perfiles) - 1:
            await espera_humana(1.0, 2.5)

        # Pausa de seguridad cada 60 perfiles descargados realmente en esta ejecución
        if guardado and total_nuevos > 0 and total_nuevos % 60 == 0 and i < len(cola_perfiles) - 1:
            log.info("Pausa de seguridad cada 60 perfiles nuevos — 30 segundos...")
            await asyncio.sleep(30)

    total_errores = len([e for e in estado.get("errores", []) if e.get("fase") == "perfiles"])
    log.info(
        f"FASE 3 completada — Nuevos: {total_nuevos} | "
        f"Omitidos: {total_omitidos} | Errores: {total_errores}"
    )
    return estado


# ===========================================================================
# FASE 4 — Opiniones
# ===========================================================================
async def _scrapear_opiniones_medico(
    medico: dict,
    estado: dict,
    log,
    limite_opiniones: int,
) -> tuple[dict, int, bool]:
    """Descarga y persiste las opiniones de un medico en ``doctor_opinions``.

    Las opiniones se insertan con la nueva estructura que incluye
    ``scraping_meta``, ``fecha_publicacion`` y ``_id`` canonico.

    Args:
        medico: Diccionario con ``doctoralia_id``, ``total_opiniones`` y
            ``nombre``.
        estado: Estado actual del pipeline.
        log: Logger configurado.
        limite_opiniones: Maximo de opiniones a descargar.

    Returns:
        Tupla ``(estado_actualizado, cantidad_guardadas, real_scrape)``.
    """
    doctoralia_id = medico.get("doctoralia_id")
    total_opiniones = medico.get("total_opiniones") or 0
    nombre = medico.get("nombre", "Desconocido")

    if opiniones_ya_completadas(estado, doctoralia_id):
        log.info(f"Opiniones omitidas (estado): {nombre} | id={doctoralia_id}")
        return estado, 0, False

    # Verificar si ya tiene opiniones en Mongo
    try:
        cantidad_existente = await contar_opiniones_por_doctor(doctoralia_id)
        if cantidad_existente > 0:
            log.info(
                f"Opiniones omitidas (ya en Mongo: {cantidad_existente}): "
                f"{nombre} | id={doctoralia_id}"
            )
            estado = marcar_opiniones_completadas(estado, doctoralia_id)
            return estado, 0, False
    except Exception:
        pass

    try:
        # construir_resultado_opiniones ya agrega doctor_id y scraping_meta
        resultado = construir_resultado_opiniones(
            doctoralia_id, total_opiniones, max_opiniones=limite_opiniones
        )
        opiniones = resultado.get("opiniones", [])

        guardadas = await insertar_opiniones_masivo(opiniones)
        log.success(  # type: ignore[attr-defined]
            f"Opiniones guardadas: id={doctoralia_id} — {guardadas} opiniones"
        )
        estado = marcar_opiniones_completadas(estado, doctoralia_id)
        return estado, guardadas, True

    except Exception as exc:
        log.error(f"Error opiniones id={doctoralia_id}: {exc}")
        estado = registrar_error(estado, "opiniones", str(doctoralia_id), str(exc))
        return estado, 0, True


async def fase_opiniones(
    estado: dict,
    log,
    limite_opiniones: int,
    semaforo: asyncio.Semaphore,
    max_medicos: int | None = None,
    partes: int | None = None,
    parte_id: int | None = None,
) -> dict:
    """Descarga y persiste las opiniones de todos los médicos en Mongo.

    Consulta la colección ``especialistas`` para obtener médicos con
    ``total_opiniones > 0`` y ``doctoralia_id`` definido. Aplica pausas entre
    médicos y cada 20 médicos procesados.

    Args:
        estado: Estado actual del pipeline.
        log: Logger configurado.
        limite_opiniones: Máximo de opiniones por médico.
        semaforo: Semáforo asyncio (reservado para uso futuro).
        max_medicos: Límite de médicos (para modo prueba).
        partes: Número total de segmentos paralelos.
        parte_id: ID de la parte asignada.

    Returns:
        Estado actualizado tras procesar las opiniones.
    """
    from app.db.mongo import get_doctoralia_async_db

    log.info("FASE 4 — Scraping opiniones...")

    try:
        db = get_doctoralia_async_db()
        coleccion = db["doctor_profiles"]
        cursor = coleccion.find(
            {"doctor.id_doctoralia": {"$ne": None}, "total_opiniones": {"$gt": 0}},
            {"doctor.id_doctoralia": 1, "total_opiniones": 1, "doctor.nombre": 1},
        )
        medicos_raw = [doc async for doc in cursor]
        # Normalizar para que el resto del codigo use las mismas claves
        medicos = [
            {
                "doctoralia_id": doc.get("doctor", {}).get("id_doctoralia"),
                "total_opiniones": doc.get("total_opiniones", 0),
                "nombre": (doc.get("doctor") or {}).get("nombre", "Desconocido"),
            }
            for doc in medicos_raw
            if (doc.get("doctor") or {}).get("id_doctoralia") is not None
        ]
    except Exception as exc:
        log.error(f"FASE 4 — No se pudo conectar a Mongo: {exc}")
        return estado

    # Filtrar los que ya tienen opiniones en el estado
    medicos = [
        m for m in medicos
        if not opiniones_ya_completadas(estado, m.get("doctoralia_id"))
    ]

    # Aplicar Sharding determinista en Fase 4
    if partes is not None and parte_id is not None:
        medicos = [
            m for m in medicos
            if int(m.get("doctoralia_id", 0)) % partes == parte_id
        ]
        log.info(
            f"FASE 4 SHARDING: Procesando segmento {parte_id} de {partes} "
            f"({len(medicos)} médicos asignados a esta parte)"
        )

    if max_medicos:
        medicos = medicos[:max_medicos]

    log.info(f"FASE 4 — {len(medicos)} médicos a procesar")
    total_guardadas = 0
    total_reales = 0

    for i, medico in enumerate(medicos):
        estado, guardadas, real_scrape = await _scrapear_opiniones_medico(
            medico, estado, log, limite_opiniones
        )
        total_guardadas += guardadas
        if real_scrape:
            total_reales += 1

        # Pausa entre médicos (solo si realmente se realizó scraping web)
        if real_scrape and i < len(medicos) - 1:
            await asyncio.sleep(random.uniform(1.5, 4.0))

        # Pausa de seguridad cada 60 médicos descargados realmente en esta ejecución
        if real_scrape and total_reales > 0 and total_reales % 60 == 0 and i < len(medicos) - 1:
            log.info("Pausa de seguridad cada 60 médicos nuevos — 30 segundos...")
            await asyncio.sleep(30)

    log.info(f"FASE 4 completada — {total_guardadas} opiniones nuevas guardadas")
    return estado


# ===========================================================================
# Orquestador principal
# ===========================================================================
async def ejecutar_pipeline(args) -> None:
    """Punto de entrada del pipeline. Orquesta las 4 fases secuencialmente.

    Carga o resetea el estado según los argumentos. Construye la lista de pares
    a procesar y ejecuta solo las fases solicitadas.

    Args:
        args: Namespace de argparse con todos los argumentos CLI parseados.
    """
    log = obtener_logger("pipeline")
    inicio = time.monotonic()

    # --- Encabezado ---
    log.info("═" * 47)
    log.info("PIPELINE MASIVO DOCTORALIA — Iniciando")
    if args.prueba:
        log.info(
            f"Modo: prueba | Especialidad: {args.especialidad} | Ciudad: {args.ciudad}"
        )
    elif args.todo:
        log.info("Modo: completo (todo el catálogo)")
    else:
        log.info(f"Modo: fase={args.fase}")
    log.info("═" * 47)

    # --- Sufijo de estado dinámico para Sharding ---
    if args.partes is not None and args.parte_id is not None:
        establecer_sufijo_estado(f"parte{args.parte_id}")
        log.info(f"Segmento de estado activo: parte{args.parte_id}")
    else:
        establecer_sufijo_estado("")

    # --- Estado ---
    if args.resetear_estado:
        estado = resetear_estado()
        log.success("Estado reseteado — archivo de estado limpiado")  # type: ignore[attr-defined]
        return
    elif args.reanudar:
        estado = cargar_estado()
        log.info("Reanudando desde estado guardado")
    else:
        estado = cargar_estado()

    # --- Semáforo de concurrencia ---
    semaforo = asyncio.Semaphore(args.max_concurrencia)

    # --- Construir lista de pares ---
    if not _CATALOGO_PATH.exists():
        log.error(f"Catálogo no encontrado: {_CATALOGO_PATH}")
        return

    with _CATALOGO_PATH.open("r", encoding="utf-8") as f:
        catalogo = json.load(f)

    todos_los_pares = catalogo.get("pares_presencial", [])

    if args.prueba or (args.especialidad and args.ciudad):
        pares = [
            p for p in todos_los_pares
            if p["especialidad_slug"] == args.especialidad
            and p["ciudad_slug"] == args.ciudad
        ]
        if not pares:
            pares = [{
                "especialidad_slug": args.especialidad,
                "ciudad_slug": args.ciudad,
                "url": f"https://www.doctoralia.com.mx/{args.especialidad}/{args.ciudad}",
            }]
    elif args.todo:
        pares = todos_los_pares
    else:
        pares = todos_los_pares

    # --- Aplicar Sharding determinista al catálogo ---
    if args.partes is not None and args.parte_id is not None:
        # Ordenamos determinísticamente para asegurar que todas las instancias coincidan en el orden
        todos_pares_ordenados = sorted(
            pares,
            key=lambda x: (x.get("especialidad_slug", ""), x.get("ciudad_slug", ""))
        )
        # Seleccionar por índice módulo parte_id
        pares = [
            todos_pares_ordenados[i]
            for i in range(len(todos_pares_ordenados))
            if i % args.partes == args.parte_id
        ]
        log.info(
            f"SHARDING ACTIVO: Procesando segmento {args.parte_id} de {args.partes} "
            f"({len(pares)} pares del catálogo asignados de forma equitativa)"
        )

    # --- Límites en modo prueba ---
    max_paginas = 2 if args.prueba else None
    max_perfiles = 5 if args.prueba else None
    max_medicos = 5 if args.prueba else None
    limite_opiniones = 10 if args.prueba else args.limite_opiniones

    fase = args.fase if not args.prueba else "todas"

    # --- Importación inteligente de Cola de Perfiles Maestra ---
    # Si estamos en modo sharding paralelo, y el estado local de esta parte aún no tiene
    # su cola de perfiles construida, pero existe el archivo de estado maestro general
    # (fixtures/pipeline_estado.json) con los 200,000 médicos ya identificados en la Fase 2,
    # podemos importar esa cola shardéandola directamente por ID. Esto permite a todas
    # las partes saltarse la Fase 2 (listados) por completo, ahorrando ~2 horas.
    if args.partes is not None and args.parte_id is not None and not estado.get("cola_perfiles") and not args.prueba:
        ruta_maestra = _FIXTURES / "pipeline_estado.json"
        if ruta_maestra.exists():
            try:
                with ruta_maestra.open("r", encoding="utf-8") as f:
                    estado_maestro = json.load(f)
                cola_maestra = estado_maestro.get("cola_perfiles", [])
                if cola_maestra:
                    # Sharding determinista basado en el ID de Doctoralia
                    cola_perfiles_sharded = [
                        item for item in cola_maestra
                        if int(item.get("doctoralia_id", 0)) % args.partes == args.parte_id
                    ]
                    estado["cola_perfiles"] = cola_perfiles_sharded
                    # Marcar todos los listados asignados como completados para omitir la Fase 2
                    estado["listados_completados"] = [
                        f"{p['especialidad_slug']}/{p['ciudad_slug']}" for p in pares
                    ]
                    estado["fase_actual"] = "perfiles"
                    guardar_estado(estado)
                    log.success(
                        f"¡OPTIMIZACIÓN DETECTADA! Se importaron {len(cola_perfiles_sharded)} perfiles "
                        f"de la cola maestra ({len(cola_maestra)} perfiles) para la parte {args.parte_id}. "
                        f"La Fase 2 de listados se omitirá por completo en esta parte."
                    )  # type: ignore[attr-defined]
            except Exception as e:
                log.warning(f"No se pudo importar la cola de perfiles del archivo maestro: {e}")

    cola_perfiles: list[dict] = []

    # --- FASE 1 ---
    if fase in ("catalogo", "todas"):
        estado = await fase_catalogo(estado, log)

    # --- FASE 2 ---
    if fase in ("listados", "todas"):
        estado, cola_perfiles = await fase_listados(
            estado, log, pares, semaforo, max_paginas=max_paginas
        )

    # --- FASE 3 ---
    if fase in ("perfiles", "todas"):
        # Si la cola en memoria está vacía, restaurar desde el estado persistido
        if not cola_perfiles:
            cola_perfiles = estado.get("cola_perfiles", [])
            if cola_perfiles:
                log.info(
                    f"FASE 3 — Cola restaurada desde estado: {len(cola_perfiles)} médicos"
                )

        if not cola_perfiles:
            log.info("FASE 3 — Cola vacía, no hay perfiles que scrapear en esta ejecución.")
        else:
            estado = await fase_perfiles(
                estado, log, cola_perfiles, semaforo, max_perfiles=max_perfiles
            )

    # --- FASE 4 ---
    if fase in ("opiniones", "todas"):
        estado = await fase_opiniones(
            estado,
            log,
            limite_opiniones,
            semaforo,
            max_medicos=max_medicos,
            partes=args.partes,
            parte_id=args.parte_id,
        )

    # --- Resumen final ---
    elapsed = time.monotonic() - inicio
    minutos = int(elapsed // 60)
    segundos = int(elapsed % 60)
    errores_total = len(estado.get("errores", []))

    log.info("═" * 47)
    log.success(  # type: ignore[attr-defined]
        f"PIPELINE FINALIZADO — Tiempo total: {minutos}m {segundos}s"
    )
    log.info(f"Perfiles completados: {len(estado.get('perfiles_completados', []))}")
    log.info(f"Opiniones completadas: {len(estado.get('opiniones_completadas', []))}")
    log.info(f"Errores registrados: {errores_total}")
    log.info(f"Estado guardado en: fixtures/pipeline_estado.json")
    log.info(f"Log guardado en: logs/pipeline_<fecha>.log")
    log.info("═" * 47)


# ===========================================================================
# Punto de entrada CLI
# ===========================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Pipeline masivo de scraping Doctoralia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--todo",
        action="store_true",
        default=False,
        help="Procesa todo el catálogo (todas las especialidades y ciudades).",
    )
    parser.add_argument(
        "--especialidad",
        type=str,
        default=None,
        help="Slug de especialidad, ej: endodoncia.",
    )
    parser.add_argument(
        "--ciudad",
        type=str,
        default=None,
        help="Slug de ciudad, ej: ciudad-de-mexico.",
    )
    parser.add_argument(
        "--fase",
        type=str,
        default="todas",
        choices=["catalogo", "listados", "perfiles", "opiniones", "todas"],
        help="Fase específica a ejecutar (default: todas).",
    )
    parser.add_argument(
        "--limite-opiniones",
        type=int,
        default=30,
        dest="limite_opiniones",
        help="Máximo de opiniones a scrapear por médico (default: 30).",
    )
    parser.add_argument(
        "--reanudar",
        action="store_true",
        default=False,
        help="Lee el estado guardado y omite lo ya completado.",
    )
    parser.add_argument(
        "--resetear-estado",
        action="store_true",
        default=False,
        dest="resetear_estado",
        help="Borra el estado y empieza desde cero.",
    )
    parser.add_argument(
        "--max-concurrencia",
        type=int,
        default=3,
        dest="max_concurrencia",
        help="Máximo de corrutinas async simultáneas (default: 3).",
    )
    parser.add_argument(
        "--partes",
        type=int,
        default=None,
        help="Número de segmentos (shards) en los que dividir el catálogo para paralelización.",
    )
    parser.add_argument(
        "--parte-id",
        type=int,
        default=None,
        dest="parte_id",
        help="ID de la parte a procesar (de 0 a partes-1).",
    )
    parser.add_argument(
        "--prueba",
        action="store_true",
        default=False,
        help=(
            "Modo prueba: máximo 2 páginas, 5 perfiles y 10 opiniones. "
            "Requiere --especialidad y --ciudad."
        ),
    )

    args = parser.parse_args()

    # Validación de modo prueba
    if args.prueba and (not args.especialidad or not args.ciudad):
        parser.error("--prueba requiere --especialidad y --ciudad.")

    # Validación de sharding (Partes Autónomas)
    if (args.partes is not None) != (args.parte_id is not None):
        parser.error("Debes especificar tanto --partes como --parte-id para usar sharding.")

    if args.partes is not None and (args.parte_id < 0 or args.parte_id >= args.partes):
        parser.error(f"--parte-id debe ser un entero entre 0 y {args.partes - 1}.")

    asyncio.run(ejecutar_pipeline(args))
