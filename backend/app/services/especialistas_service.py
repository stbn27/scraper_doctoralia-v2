"""Servicio de negocio para orquestar scraping y acceso a MongoDB."""

import asyncio
import json
import math
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from app.db.repositorios import catalogos_repo, especialistas_repo
from app.scraper import (
    catalog_extractor,
    catalog_refresher,
    doctoralia,
    listing_scraper,
)
from app.scraper.utils.rate_limiter import RateLimiter

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT_DIR / "fixtures"
CATALOGO_PATH = FIXTURES_DIR / "catalogo_doctoralia.json"


def _normalizar_slug(texto: str) -> str:
    """Convierte un texto a slug en minusculas sin acentos.
    Ejemplo: "Clínica Médica" -> "clinica-medica"."""

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower().strip()
    texto = "-".join(texto.split())
    return texto


def _es_reciente(fecha_iso: str | None, dias_max: int = 7) -> bool:
    """Evalua si una fecha ISO esta dentro del rango de dias permitidos.
    Ejemplo: si fecha_iso es:
    - "2026-06-01T12:00:00+00:00" y hoy es 2026-06-05, devuelve True.
    - "2026-05-20T12:00:00+00:00" y hoy es 2026-06-05, devuelve False."""

    if not fecha_iso:
        return False
    try:
        fecha = datetime.fromisoformat(fecha_iso)
    except ValueError:
        return False
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - fecha <= timedelta(days=dias_max)


def _cargar_catalogo_local(especialidad_slug: str, ciudad_slug: str) -> dict | None:
    """Busca un par especialidad-ciudad en el catalogo local. Requiere que en el directorio __fixtures__ existe
    el archivo de la variable _CATALOGO_PATH_ con la estructura adecuada. Esto es util para evitar hacer scraping
    en combinaciones que sabemos que no existen."""

    if not CATALOGO_PATH.exists():
        return None

    payload = json.loads(CATALOGO_PATH.read_text(encoding="utf-8"))
    especialidades = {
        e.get("slug"): e.get("nombre") for e in payload.get("especialidades", [])
    }
    for par in payload.get("pares_presencial", []):
        if (
            par.get("especialidad_slug") == especialidad_slug
            and par.get("ciudad_slug") == ciudad_slug
        ):
            return {
                "especialidad_slug": especialidad_slug,
                "especialidad_nombre": especialidades.get(especialidad_slug),
                "ciudad_slug": ciudad_slug,
                "ciudad_nombre": par.get("texto_enlace"),
                "url": par.get("url"),
                "ultima_actualizacion": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
            }
    return None


async def cargar_catalogo_desde_fixture(especialidad: str, ciudad: str) -> dict:
    """Carga un catalogo desde fixtures si no existe en Mongo."""
    especialidad_slug = _normalizar_slug(especialidad)
    ciudad_slug = _normalizar_slug(ciudad)

    existente = await catalogos_repo.obtener_catalogo_por_especialidad_ciudad(
        especialidad_slug, ciudad_slug
    )
    if existente:
        return {"insertado": False, "url": existente.get("url")}

    catalogo = _cargar_catalogo_local(especialidad_slug, ciudad_slug)
    if not catalogo:
        raise ValueError("Catalogo no encontrado para la combinacion indicada")

    await catalogos_repo.insertar_catalogo(catalogo)
    return {"insertado": True, "url": catalogo.get("url")}


async def actualizar_catalogo_desde_web() -> dict:
    """Scrapea el catalogo completo desde la web y lo persiste en Mongo."""
    html_text = await asyncio.to_thread(
        catalog_refresher.download_html, catalog_refresher.SEARCH_URL
    )
    soup = BeautifulSoup(html_text, "html.parser")
    especialidades = catalog_extractor.extract_specialties(soup)
    slugs_validos = {e.get("slug") for e in especialidades if e.get("slug")}
    pares_presencial, _ = catalog_extractor.extract_pairs(soup, slugs_validos)

    mapa_nombres = {e.get("slug"): e.get("nombre") for e in especialidades}
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    documentos = []
    for par in pares_presencial:
        documentos.append(
            {
                "especialidad_slug": par.get("especialidad_slug"),
                "especialidad_nombre": mapa_nombres.get(par.get("especialidad_slug")),
                "ciudad_slug": par.get("ciudad_slug"),
                "ciudad_nombre": par.get("texto_enlace"),
                "url": par.get("url"),
                "ultima_actualizacion": timestamp,
            }
        )

    resumen = await catalogos_repo.upsert_catalogos(documentos)
    return {
        "insertados": resumen.get("insertados", 0),
        "actualizados": resumen.get("actualizados", 0),
        "procesados": resumen.get("procesados", 0),
    }


def _mapear_perfil_a_doc(
    perfil: dict,
    doctoralia_id: int,
    especialidad: str,
    ciudad: str,
) -> dict:
    """Convierte el perfil parseado en el esquema de especialista esperado."""
    scraping_meta = perfil.get("scraping_meta") or {}
    info_meta = perfil.get("info_meta") or perfil.get("info") or {}
    servicios = perfil.get("servicios") or []
    consultorios = perfil.get("consultorios") or []
    pacientes = perfil.get("pacientes") or {}

    return {
        "doctoralia_id": doctoralia_id,
        "nombre": perfil.get("nombre"),
        "foto_perfil_url": perfil.get("foto_perfil_url"),
        "especialidad": perfil.get("especialidad") or especialidad,
        "ciudad": perfil.get("ciudad") or ciudad,
        "rating_global": perfil.get("rating_global"),
        "total_opiniones": perfil.get("total_opiniones"),
        "cedula": perfil.get("cedula"),
        "cedulas": perfil.get("cedulas") or [],
        "experiencia": perfil.get("experiencia") or [],
        "servicios": servicios,
        "consultorios": consultorios,
        "info_meta": {
            "total_servicios": info_meta.get("total_servicios", len(servicios)),
            "total_consultorios": info_meta.get(
                "total_consultorios", len(consultorios)
            ),
        },
        "pacientes": {
            "atiende_ninos": pacientes.get("atiende_ninos", False),
            "atiende_adultos": pacientes.get("atiende_adultos", True),
            "atiende_adolescentes": pacientes.get("atiende_adolescentes", False),
        },
        "scraping_meta": {
            "url_origen": scraping_meta.get("url_origen"),
            "fecha_consulta": scraping_meta.get("fecha_consulta"),
            "total_servicios": scraping_meta.get("total_servicios", len(servicios)),
            "total_consultorios": scraping_meta.get(
                "total_consultorios", len(consultorios)
            ),
        },
    }


async def buscar_o_scrapear_especialistas(
    especialidad: str,
    ciudad: str,
    limite: int = 20,
    forzar_scraping: bool = False,
) -> dict:
    """Busca especialistas en Mongo o dispara scraping si es necesario."""
    especialidad_slug = _normalizar_slug(especialidad)
    ciudad_slug = _normalizar_slug(ciudad)

    catalogo = await catalogos_repo.obtener_catalogo_por_especialidad_ciudad(
        especialidad_slug, ciudad_slug
    )
    if not catalogo:
        catalogo_local = _cargar_catalogo_local(especialidad_slug, ciudad_slug)
        if not catalogo_local:
            raise ValueError("Catalogo no encontrado para la combinacion indicada")
        await catalogos_repo.insertar_catalogo(catalogo_local)
        catalogo = catalogo_local

    especialistas_db = await especialistas_repo.obtener_por_especialidad_y_ciudad(
        especialidad, ciudad
    )
    especialistas_db = especialistas_db[:limite]

    if len(especialistas_db) >= limite and not forzar_scraping:
        return {
            "fuente": "mongo",
            "total": len(especialistas_db),
            "especialidad": especialidad,
            "ciudad": ciudad,
            "especialistas": especialistas_db,
        }

    rate_limiter = RateLimiter()
    doctores_listado: list[dict] = []
    paginas_objetivo = max(1, math.ceil(limite / 17))
    total_paginas = None

    for pagina in range(1, paginas_objetivo + 1):
        await rate_limiter.esperar_si_necesario()
        resultado, total_paginas = await asyncio.to_thread(
            listing_scraper.scrape_listing, especialidad_slug, ciudad_slug, pagina
        )
        doctores_listado.extend(resultado.get("doctores", []))
        if total_paginas:
            paginas_objetivo = min(paginas_objetivo, total_paginas)
        if len(doctores_listado) >= limite:
            break

    doctores_listado = doctores_listado[:limite]

    especialistas_final: list[dict] = []
    vistos: set[int] = set()

    for doctor in doctores_listado:
        doctoralia_id = doctor.get("doctoralia_id")
        url_perfil = doctor.get("url_perfil")
        if not doctoralia_id or not url_perfil:
            continue

        existente = await especialistas_repo.buscar_por_doctoralia_id(doctoralia_id)
        necesita_refrescar = True
        if existente and not forzar_scraping:
            fecha = (existente.get("scraping_meta") or {}).get("fecha_consulta")
            necesita_refrescar = not _es_reciente(fecha)

        if not existente:
            perfil = await asyncio.to_thread(
                doctoralia.fetch_and_parse_profile, url_perfil
            )
            doc = _mapear_perfil_a_doc(perfil, doctoralia_id, especialidad, ciudad)
            await especialistas_repo.insertar_especialista(doc)
        elif necesita_refrescar:
            perfil = await asyncio.to_thread(
                doctoralia.fetch_and_parse_profile, url_perfil
            )
            doc = _mapear_perfil_a_doc(perfil, doctoralia_id, especialidad, ciudad)
            await especialistas_repo.actualizar_especialista(doctoralia_id, doc)

        actual = await especialistas_repo.buscar_por_doctoralia_id(doctoralia_id)
        if actual:
            especialistas_final.append(actual)
            vistos.add(doctoralia_id)

    if len(especialistas_final) < limite:
        for doc in especialistas_db:
            doctoralia_id = doc.get("doctoralia_id")
            if doctoralia_id and doctoralia_id in vistos:
                continue
            especialistas_final.append(doc)
            if len(especialistas_final) >= limite:
                break

    uso_mongo = len(especialistas_db) > 0
    uso_scraping = len(doctores_listado) > 0
    if uso_mongo and uso_scraping:
        fuente = "mixto"
    elif uso_scraping:
        fuente = "scraping"
    else:
        fuente = "mongo"

    return {
        "fuente": fuente,
        "total": len(especialistas_final),
        "especialidad": especialidad,
        "ciudad": ciudad,
        "especialistas": especialistas_final,
    }
