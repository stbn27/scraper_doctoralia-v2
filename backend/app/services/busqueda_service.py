"""
Servicio de búsqueda avanzada de especialistas con filtros, paginación y análisis IA.

Orquesta la consulta a MongoDB aplicando todos los filtros disponibles y enriquece
los resultados con datos de `analisis_especialistas` usando batch queries.
No dispara scraping. Solo consulta datos ya almacenados.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any, Optional

from app.db.mongo import get_mongo_async_db
from app.db.repositorios import analisis_repo


def _normalizar(texto: str) -> str:
    """
    Convierte texto a minúsculas sin acentos para comparación normalizada.

    Parámetros
    ----------
    texto : str
        Texto a normalizar.

    Retorna
    -------
    str
        Texto normalizado sin acentos ni mayúsculas.

    Ejemplo
    -------
    >>> _normalizar("Ginecólogo")
    'ginecologo'
    """
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower().strip()


def _regex_ci(valor: str) -> dict:
    """
    Construye filtro MongoDB de regex case-insensitive tolerante a acentos,
    guiones/espacios y caracteres corruptos de codificación (como ).

    Parámetros
    ----------
    valor : str
        Texto a buscar.

    Retorna
    -------
    dict
        Filtro MongoDB `{$regex: ..., $options: 'i'}`.
    """
    # Reemplazar guiones por espacios y limpiar
    valor_limpio = valor.lower().replace("-", " ").strip()

    patron = ""
    for char in valor_limpio:
        if char in "aeiouáéíóúü":
            # Reemplazar cualquier vocal por clase de caracteres para evitar falsos positivos con consonantes
            patron += "[aeiouáéíóúü\uFFFD]"
        elif char == " ":
            # Espacios coinciden con espacios, guiones o cualquier carácter de unión
            patron += ".*"
        else:
            patron += re.escape(char)

    return {"$regex": patron, "$options": "i"}


# Mapa de aliases de ciudad frecuentes
_ALIASES_CIUDAD = {
    "cdmx": "ciudad de mexico",
    "df": "ciudad de mexico",
    "ciudad de mexico": "ciudad de mexico",
    "ciudad de méxico": "ciudad de mexico",
    "guadalajara": "guadalajara",
    "monterrey": "monterrey",
}

# Mapa de ordenamientos a campos MongoDB
_SORT_MAP = {
    "opiniones_desc": ("total_opiniones", -1),
    "opiniones_asc": ("total_opiniones", 1),
    "rating_desc": ("rating_global", -1),
    "rating_asc": ("rating_global", 1),
    "nombre_asc": ("nombre", 1),
    "nombre_desc": ("nombre", -1),
}


def _construir_filtro_especialistas(params: dict) -> dict:
    """
    Construye el filtro MongoDB para la colección `especialistas` a partir de parámetros de búsqueda.

    Parámetros
    ----------
    params : dict
        Diccionario con todos los parámetros de búsqueda del endpoint GET /especialistas.

    Retorna
    -------
    dict
        Filtro MongoDB listo para usar en `find()` o `aggregate()`.
    """
    filtro: dict[str, Any] = {}

    # --- Especialidad ---
    esp = params.get("especialidad") or params.get("especialidad_slug")
    if esp:
        esp_norm = _normalizar(esp)
        filtro["especialidad"] = _regex_ci(esp_norm)

    # --- Ciudad ---
    ciu = params.get("ciudad") or params.get("ciudad_slug")
    if ciu:
        ciu_norm = _ALIASES_CIUDAD.get(_normalizar(ciu), _normalizar(ciu))
        filtro["$or"] = [
            {"ciudad": _regex_ci(ciu_norm)},
            {"consultorios.direccion": _regex_ci(ciu_norm)},
            {"scraping_meta.url_origen": _regex_ci(ciu_norm)},
        ]

    # --- Búsqueda textual ---
    q = params.get("q")
    if q:
        filtro["nombre"] = _regex_ci(q)

    # --- Pacientes ---
    if params.get("atiende_ninos") is True:
        filtro["pacientes.atiende_ninos"] = True
    if params.get("atiende_adultos") is True:
        filtro["pacientes.atiende_adultos"] = True
    if params.get("atiende_adolescentes") is True:
        filtro["pacientes.atiende_adolescentes"] = True

    # --- Opiniones ---
    if params.get("solo_con_opiniones"):
        filtro["total_opiniones"] = {"$gt": 0}

    min_op = params.get("min_opiniones")
    max_op = params.get("max_opiniones")
    if min_op is not None or max_op is not None:
        rango: dict = {}
        if min_op is not None:
            rango["$gte"] = min_op
        if max_op is not None:
            rango["$lte"] = max_op
        filtro["total_opiniones"] = rango

    # --- Rating ---
    rating_min = params.get("rating_min")
    rating_max = params.get("rating_max")
    if rating_min is not None or rating_max is not None:
        rango_rating: dict = {}
        if rating_min is not None:
            rango_rating["$gte"] = rating_min
        if rating_max is not None:
            rango_rating["$lte"] = rating_max
        filtro["rating_global"] = rango_rating

    # --- Foto, cédula, consultorio ---
    if params.get("solo_con_foto"):
        filtro["foto_perfil_url"] = {"$nin": [None, ""]}
    if params.get("solo_con_cedula"):
        filtro["$or"] = filtro.get("$or", []) + [
            {"cedula": {"$nin": [None, ""]}},
            {"cedulas": {"$exists": True, "$not": {"$size": 0}}},
        ]
    if params.get("solo_con_consultorio"):
        filtro["consultorios"] = {"$exists": True, "$not": {"$size": 0}}

    # --- Precio ---
    if params.get("solo_con_precio"):
        filtro["servicios.precio_desde"] = {"$nin": [None]}
    precio_min = params.get("precio_min")
    precio_max = params.get("precio_max")
    if precio_min is not None or precio_max is not None:
        rango_precio: dict = {}
        if precio_min is not None:
            rango_precio["$gte"] = precio_min
        if precio_max is not None:
            rango_precio["$lte"] = precio_max
        filtro["servicios.precio_desde"] = rango_precio

    # --- Servicio específico ---
    servicio = params.get("servicio")
    if servicio:
        filtro["servicios.nombre"] = _regex_ci(servicio)

    # --- Alcaldía / municipio ---
    alcaldia = params.get("alcaldia_o_municipio")
    if alcaldia:
        filtro["consultorios.direccion"] = _regex_ci(alcaldia)

    return filtro


def _construir_sort(orden: Optional[str]) -> list[tuple]:
    """
    Traduce el parámetro `orden` a instrucción de sort para MongoDB.

    Parámetros
    ----------
    orden : str o None
        Nombre del criterio de orden (ej. 'puntuacion_desc').

    Retorna
    -------
    list[tuple]
        Lista de tuplas `(campo, dirección)` para pymongo.
    """
    if orden in _SORT_MAP:
        campo, direccion = _SORT_MAP[orden]
        return [(campo, direccion)]
    # Por defecto: opiniones descendente
    return [("total_opiniones", -1)]


def _serializar_id(doc: dict) -> dict:
    """Convierte `_id` ObjectId a string para serialización JSON."""
    if "_id" in doc and doc["_id"] is not None:
        doc["_id"] = str(doc["_id"])
    return doc


def _extraer_analisis_resumen(analisis_doc: Optional[dict]) -> Optional[dict]:
    """
    Extrae el resumen de análisis IA para incluir en la card de especialista.

    Parámetros
    ----------
    analisis_doc : dict o None
        Documento completo de `analisis_especialistas`.

    Retorna
    -------
    dict o None
        Resumen de análisis listo para la respuesta de card, o None.
    """
    if not analisis_doc:
        return None

    resultado_ia = analisis_doc.get("resultado_ia") or {}
    metricas = analisis_doc.get("metricas_locales") or {}

    return {
        "estado": analisis_doc.get("estado"),
        "modelo_usado": analisis_doc.get("modelo_usado"),
        "fecha_analisis": str(analisis_doc.get("fecha_analisis", "")),
        "puntuacion_recomendacion": resultado_ia.get("puntuacion_recomendacion"),
        "resumen": resultado_ia.get("resumen"),
        "confiabilidad_opiniones": resultado_ia.get("confiabilidad_opiniones"),
        "sospecha_fraude": metricas.get("sospecha_fraude"),
        "razones_fraude": metricas.get("razones_fraude") or [],
        "metricas_locales": {
            "total_opiniones_bd": metricas.get("total_opiniones_bd"),
            "porcentaje_verificadas": metricas.get("porcentaje_verificadas"),
            "rating_promedio": metricas.get("rating_promedio"),
            "recencia_promedio_dias": metricas.get("recencia_promedio_dias"),
        },
    }


def _construir_card(especialista: dict, analisis_doc: Optional[dict]) -> dict:
    """
    Construye la representación de card de un especialista enriquecida con análisis IA.

    Parámetros
    ----------
    especialista : dict
        Documento de la colección `especialistas`.
    analisis_doc : dict o None
        Documento de análisis IA correspondiente, si existe.

    Retorna
    -------
    dict
        Diccionario con todos los campos de EspecialistaCardResponse.
    """
    consultorios = especialista.get("consultorios") or []
    consultorio_principal = consultorios[0] if consultorios else None

    servicios = especialista.get("servicios") or []
    precios_validos = [s["precio_desde"] for s in servicios if s.get("precio_desde")]
    precio_minimo = min(precios_validos) if precios_validos else None

    analisis_resumen = _extraer_analisis_resumen(analisis_doc)

    return {
        "_id": str(especialista.get("_id", "")),
        "doctoralia_id": especialista.get("doctoralia_id"),
        "nombre": especialista.get("nombre", ""),
        "especialidad": especialista.get("especialidad"),
        "ciudad": especialista.get("ciudad"),
        "rating_global": especialista.get("rating_global"),
        "total_opiniones": especialista.get("total_opiniones"),
        "foto_perfil_url": especialista.get("foto_perfil_url"),
        "cedula": especialista.get("cedula"),
        "consultorio_principal": consultorio_principal,
        "pacientes": especialista.get("pacientes"),
        "precio_minimo": precio_minimo,
        "servicios_destacados": servicios[:3],
        "tiene_analisis": analisis_doc is not None,
        "analisis": analisis_resumen,
    }


async def buscar_especialistas_paginado(
    params: dict,
    page: int = 1,
    limit: int = 12,
) -> dict:
    """
    Ejecuta búsqueda avanzada de especialistas con filtros, paginación y enriquecimiento con análisis IA.

    Esta función construye el filtro MongoDB, aplica ordenamiento, pagina los resultados
    y enriquece cada especialista con su análisis IA usando una batch query a `analisis_especialistas`.

    Para filtros que requieren datos de análisis (solo_analizados, estado_analisis,
    confiabilidad, sospecha_fraude, puntuacion_*), se hace un pre-filtro en `analisis_especialistas`
    para obtener los IDs válidos y luego filtrar `especialistas` por esos IDs.

    Parámetros
    ----------
    params : dict
        Parámetros de búsqueda extraídos del request (especialidad, ciudad, orden, etc.).
    page : int
        Página actual (1-indexed). Por defecto 1.
    limit : int
        Documentos por página. Por defecto 12, máximo 50.

    Retorna
    -------
    dict
        Respuesta completa con total, paginación y lista de especialistas con análisis.
    """
    db = get_mongo_async_db()
    col_esp = db["especialistas"]
    col_ana = db["analisis_especialistas"]

    # Filtros que requieren join con analisis
    solo_analizados = params.get("solo_analizados", False)
    estado_analisis = params.get("estado_analisis")
    confiabilidad = params.get("confiabilidad")
    sospecha_fraude_param = params.get("sospecha_fraude")
    puntuacion_min = params.get("puntuacion_min")
    puntuacion_max = params.get("puntuacion_max")
    orden = params.get("orden", "opiniones_desc")

    # Si hay filtros de análisis, pre-filtrar IDs de analisis_especialistas
    ids_con_analisis: Optional[set[int]] = None
    if any(
        [
            solo_analizados,
            estado_analisis,
            confiabilidad,
            sospecha_fraude_param is not None,
            puntuacion_min,
            puntuacion_max,
        ]
    ):
        filtro_ana: dict[str, Any] = {}
        if estado_analisis:
            filtro_ana["estado"] = estado_analisis
        if confiabilidad:
            filtro_ana["resultado_ia.confiabilidad_opiniones"] = confiabilidad
        if sospecha_fraude_param is not None:
            filtro_ana["metricas_locales.sospecha_fraude"] = sospecha_fraude_param
        if puntuacion_min is not None:
            filtro_ana.setdefault("resultado_ia.puntuacion_recomendacion", {})[
                "$gte"
            ] = puntuacion_min
        if puntuacion_max is not None:
            filtro_ana.setdefault("resultado_ia.puntuacion_recomendacion", {})[
                "$lte"
            ] = puntuacion_max

        cursor_ana = col_ana.find(filtro_ana, {"doctoralia_id": 1, "doctor_id": 1})
        ids_con_analisis = set()
        async for doc in cursor_ana:
            did = doc.get("doctoralia_id") or doc.get("doctor_id")
            if did:
                ids_con_analisis.add(did)

    # Construir filtro principal de especialistas
    filtro = _construir_filtro_especialistas(params)

    # Aplicar IDs de análisis como filtro si es necesario
    if ids_con_analisis is not None:
        filtro["doctoralia_id"] = {"$in": list(ids_con_analisis)}

    # Determinar sort
    sort_por_puntuacion = orden in ("puntuacion_desc", "puntuacion_asc")
    sort_por_recencia = orden == "recencia_analisis_desc"

    if sort_por_puntuacion or sort_por_recencia:
        sort_instruccion = [("total_opiniones", -1)]
    else:
        sort_instruccion = _construir_sort(orden)

    # Contar total
    total = await col_esp.count_documents(filtro)

    # Si no hay resultados
    if total == 0:
        return _respuesta_vacia(params, page, limit)

    skip = (page - 1) * limit
    cursor = col_esp.find(filtro).sort(sort_instruccion).skip(skip).limit(limit)
    docs = [doc async for doc in cursor]

    # Obtener análisis en batch
    doctoralia_ids = [d.get("doctoralia_id") for d in docs if d.get("doctoralia_id")]
    mapa_analisis = await analisis_repo.obtener_por_doctoralia_ids(doctoralia_ids)

    # Construir cards
    results = []
    for doc in docs:
        did = doc.get("doctoralia_id")
        analisis_doc = mapa_analisis.get(did) if did else None
        card = _construir_card(_serializar_id(doc), analisis_doc)
        results.append(card)

    # Ordenar por puntuación en memoria si es necesario
    if sort_por_puntuacion:
        rev = orden == "puntuacion_desc"
        results.sort(
            key=lambda c: (c.get("analisis", {}) or {}).get("puntuacion_recomendacion")
            or -1,
            reverse=rev,
        )
    elif sort_por_recencia:
        results.sort(
            key=lambda c: ((c.get("analisis", {}) or {}).get("fecha_analisis") or ""),
            reverse=True,
        )

    pages = math.ceil(total / limit) if limit else 1

    # Filtros aplicados para respuesta
    filters_applied = {
        k: v for k, v in params.items() if v is not None and v is not False and v != ""
    }

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
        "filters_applied": filters_applied,
        "results": results,
    }


def _respuesta_vacia(params: dict, page: int, limit: int) -> dict:
    """Construye respuesta vacía con mensaje orientativo."""
    tiene_filtros = any(
        v
        for k, v in params.items()
        if k not in ("page", "limit") and v is not None and v is not False
    )
    return {
        "total": 0,
        "page": page,
        "limit": limit,
        "pages": 0,
        "has_next": False,
        "has_prev": False,
        "filters_applied": {},
        "results": [],
        "message": (
            "No se encontraron especialistas con los filtros aplicados."
            if tiene_filtros
            else "Agrega al menos un filtro para buscar especialistas."
        ),
    }
