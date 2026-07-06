"""
Servicio de búsqueda avanzada de especialistas con filtros, paginación y análisis IA.

Consulta la colección ``doctor_profiles`` de la BD Doctoralia (27017) y enriquece
los resultados con datos de ``analisis_especialistas``.

Los especialistas CON análisis siempre se muestran antes que los que no tienen.
No dispara scraping. Solo consulta datos ya almacenados.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any, Optional

from app.db.mongo import get_doctoralia_async_db
from app.db.repositorios import analisis_repo


# =============================================================================
# Utilidades de normalización
# =============================================================================


def _normalizar(texto) -> str:
    """
    Convierte texto a minúsculas sin acentos para comparación normalizada.

    Acepta None o cualquier tipo no-str y retorna string vacío de forma segura,
    evitando TypeError cuando campos de MongoDB llegan como null.

    Parámetros
    ----------
    texto : str | None | Any
        Texto a normalizar.

    Retorna
    -------
    str
        Texto normalizado sin acentos ni mayúsculas, o '' si la entrada es None.

    Ejemplo
    -------
    >>> _normalizar("Ginecólogo")
    'ginecologo'
    >>> _normalizar(None)
    ''
    """
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower().strip()


def _regex_ci(valor: str) -> dict:
    """
    Construye filtro MongoDB de regex case-insensitive tolerante a acentos.

    Parámetros
    ----------
    valor : str
        Texto a buscar.

    Retorna
    -------
    dict
        Filtro MongoDB ``{$regex: ..., $options: 'i'}``.
    """
    valor_limpio = valor.lower().replace("-", " ").strip()
    patron = ""
    vocal_map = {
        "a": "[aáAÁ]", "á": "[aáAÁ]",
        "e": "[eéEÉ]", "é": "[eéEÉ]",
        "i": "[iíIÍ]", "í": "[iíIÍ]",
        "o": "[oóOÓ]", "ó": "[oóOÓ]",
        "u": "[uúüUÚÜ]", "ú": "[uúüUÚÜ]", "ü": "[uúüUÚÜ]"
    }
    for char in valor_limpio:
        if char in vocal_map:
            patron += vocal_map[char]
        elif char == " ":
            patron += ".*"
        else:
            patron += re.escape(char)
    return {"$regex": patron, "$options": "i"}


# Mapa de ordenamientos a campos MongoDB para doctor_profiles
_SORT_MAP = {
    "opiniones_desc": ("total_opiniones", -1),
    "opiniones_asc": ("total_opiniones", 1),
    "nombre_asc": ("doctor.nombre", 1),
    "nombre_desc": ("doctor.nombre", -1),
}


# =============================================================================
# Construcción de filtros para doctor_profiles
# =============================================================================


def _construir_filtro_doctor_profiles(params: dict) -> dict:
    """
    Construye el filtro MongoDB para la colección ``doctor_profiles``.

    El esquema de ``doctor_profiles`` tiene campos anidados bajo ``doctor.*``:
    - ``doctor.nombre``, ``doctor.especialidades[]``, ``doctor.direcciones[]``.

    Parámetros
    ----------
    params : dict
        Diccionario con parámetros de búsqueda del endpoint GET /especialistas.

    Retorna
    -------
    dict
        Filtro MongoDB listo para usar en ``find()`` o ``aggregate()``.
    """
    filtro: dict[str, Any] = {}

    # --- Especialidad ---
    esp = params.get("especialidad") or params.get("especialidad_slug")
    if esp:
        esp_norm = _normalizar(esp)
        filtro["doctor.especialidades"] = _regex_ci(esp_norm)

    # --- Ciudad / Ubicación ---
    ciu = params.get("ciudad") or params.get("ciudad_slug")
    if ciu:
        ciu_norm = _normalizar(ciu)
        filtro["$or"] = [
            {"doctor.direcciones.ciudad": _regex_ci(ciu_norm)},
            {"doctor.direcciones.calle": _regex_ci(ciu_norm)},
            {"doctor.estado": _regex_ci(ciu_norm)},
        ]

    # --- Búsqueda textual por nombre ---
    q = params.get("q")
    if q:
        filtro["doctor.nombre"] = _regex_ci(q)

    # --- Pacientes ---
    if params.get("atiende_ninos") is True:
        filtro["doctor.pacientes_que_atiende.ninos"] = True
    if params.get("atiende_adultos") is True:
        filtro["doctor.pacientes_que_atiende.adultos"] = True
    if params.get("atiende_adolescentes") is True:
        filtro["doctor.pacientes_que_atiende.adolescentes"] = True

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

    # --- Foto de perfil ---
    if params.get("solo_con_foto"):
        filtro["doctor.foto_perfil"] = {"$nin": [None, ""]}

    # --- Cédula ---
    if params.get("solo_con_cedula"):
        filtro["doctor.cedulas"] = {"$exists": True, "$not": {"$size": 0}}

    # --- Consultorio ---
    if params.get("solo_con_consultorio"):
        filtro["doctor.direcciones"] = {"$exists": True, "$not": {"$size": 0}}

    # --- Precio ---
    if params.get("solo_con_precio"):
        filtro["doctor.servicios_y_precios.precio"] = {
            "$nin": [None, ""],
            "$exists": True,
        }

    # --- Servicio específico ---
    servicio = params.get("servicio")
    if servicio:
        filtro["doctor.servicios_y_precios.servicio"] = _regex_ci(servicio)

    # --- Alcaldía / municipio ---
    alcaldia = params.get("alcaldia_o_municipio")
    if alcaldia:
        filtro["doctor.direcciones.calle"] = _regex_ci(_normalizar(alcaldia))

    return filtro


def _construir_sort(orden: Optional[str]) -> list[tuple]:
    """
    Traduce el parámetro ``orden`` a instrucción de sort para MongoDB.

    Parámetros
    ----------
    orden : str o None
        Nombre del criterio de orden.

    Retorna
    -------
    list[tuple]
        Lista de tuplas ``(campo, dirección)`` para pymongo.
    """
    if orden in _SORT_MAP:
        campo, direccion = _SORT_MAP[orden]
        return [(campo, direccion)]
    return [("total_opiniones", -1)]


# =============================================================================
# Serialización y construcción de cards
# =============================================================================


def _serializar_id(doc: dict) -> dict:
    """Convierte ``_id`` ObjectId a string para serialización JSON."""
    if "_id" in doc and doc["_id"] is not None:
        doc["_id"] = str(doc["_id"])
    return doc


def _extraer_analisis_resumen(analisis_doc: Optional[dict]) -> Optional[dict]:
    """
    Extrae resumen del análisis IA para la card de especialista.

    Adapta el nuevo esquema de ``analisis_especialistas`` donde los campos
    están en ``analisis.*`` y ``metadata_opiniones.*`` en lugar de
    ``resultado_ia.*`` y ``metricas_locales.*``.

    Parámetros
    ----------
    analisis_doc : dict o None
        Documento completo de ``analisis_especialistas``.

    Retorna
    -------
    dict o None
        Resumen del análisis listo para la respuesta de card, o None.
    """
    if not analisis_doc:
        return None

    analisis = analisis_doc.get("analisis") or {}
    meta_op = analisis_doc.get("metadata_opiniones") or {}

    return {
        "estado": analisis_doc.get("estatus_analisis"),
        "modelo_usado": analisis_doc.get("modelo_usado"),
        "fecha_analisis": str(
            analisis_doc.get("metadata_analisis", {}).get("fecha", "")
        ),
        "puntuacion_recomendacion": analisis.get("puntuacion"),
        "resumen": analisis.get("resumen"),
        "confiabilidad_opiniones": analisis.get("confiabilidad"),
        "sospecha_fraude": meta_op.get("sospecha_fraude"),
        "razones_fraude": meta_op.get("razones_fraude") or [],
        "metricas_locales": {
            "total_opiniones_bd": meta_op.get("opiniones_bd"),
            "porcentaje_verificadas": meta_op.get("verificadas"),
            "rating_promedio": meta_op.get("rating_promedio"),
            "recencia_promedio_dias": meta_op.get("recencia_promedio_dias"),
        },
    }


def _construir_card(doctor_doc: dict, analisis_doc: Optional[dict], ciudad_buscada: Optional[str] = None) -> dict:
    """
    Construye la representación de card de un especialista (doctor_profiles)
    enriquecida con análisis IA.

    Parámetros
    ----------
    doctor_doc : dict
        Documento de la colección ``doctor_profiles`` con ``_id`` ya serializado.
    analisis_doc : dict o None
        Documento de análisis IA correspondiente, si existe.

    Retorna
    -------
    dict
        Diccionario con todos los campos del card de especialista.
    """
    doctor = doctor_doc.get("doctor") or {}
    direcciones = doctor.get("direcciones") or []

    # Filtrar direcciones con datos válidos
    direcciones_validas = [d for d in direcciones if d.get("ciudad") or d.get("calle")]
    direccion_principal = direcciones_validas[0] if direcciones_validas else None

    if direccion_principal and ciudad_buscada:
        ciu_norm = _normalizar(ciudad_buscada)
        for d in direcciones_validas:
            c = d.get("ciudad", "")
            calle = d.get("calle", "")
            if ciu_norm in _normalizar(c) or ciu_norm in _normalizar(calle):
                direccion_principal = d
                break

    # Especialidad principal
    especialidades = doctor.get("especialidades") or []
    especialidad_principal = especialidades[0] if especialidades else None

    # Ciudad principal
    ciudad_principal = None
    if direccion_principal:
        ciudad_principal = direccion_principal.get("ciudad")
    if not ciudad_principal and doctor.get("estado"):
        estados = doctor.get("estado") or []
        ciudad_principal = estados[0] if estados else None

    # Precio mínimo desde servicios_y_precios
    servicios = doctor.get("servicios_y_precios") or []
    precio_minimo = None
    for s in servicios:
        precio_str = s.get("precio")
        if precio_str and "Desde $" in precio_str:
            try:
                valor = int(precio_str.replace("Desde $", "").replace(",", "").strip())
                if precio_minimo is None or valor < precio_minimo:
                    precio_minimo = valor
            except ValueError:
                pass

    analisis_resumen = _extraer_analisis_resumen(analisis_doc)

    return {
        "_id": str(doctor_doc.get("_id", "")),
        "doctoralia_id": doctor.get("id_doctoralia"),
        "nombre": doctor.get("nombre", ""),
        "especialidad": especialidad_principal,
        "especialidades": especialidades,
        "ciudad": ciudad_principal,
        "estado": doctor.get("estado") or [],
        "foto_perfil_url": doctor.get("foto_perfil"),
        "cedulas": doctor.get("cedulas") or [],
        "cedula": (doctor.get("cedulas") or [None])[0],
        "total_opiniones": doctor_doc.get("total_opiniones", 0),
        "rating_global": doctor_doc.get("calificacion_global") or doctor_doc.get("rating_global"),
        "direccion_principal": direccion_principal,
        "consultorios": direcciones_validas,
        "pacientes": doctor.get("pacientes_que_atiende"),
        "precio_minimo": precio_minimo,
        "servicios_destacados": servicios[:3],
        "tipos_consulta": doctor.get("tipos_de_consulta") or [],
        "tiene_analisis": analisis_doc is not None,
        "analisis": analisis_resumen,
    }


# =============================================================================
# Función principal de búsqueda paginada
# =============================================================================


async def buscar_especialistas_paginado(
    params: dict,
    page: int = 1,
    limit: int = 12,
) -> dict:
    """
    Ejecuta búsqueda avanzada de especialistas con filtros, paginación y análisis IA.

    Consulta ``doctor_profiles`` en la BD Doctoralia. Los especialistas con análisis
    siempre aparecen antes que los sin análisis (ordenamiento por prioridad).
    Para filtros basados en análisis (confiabilidad, puntuacion, etc.) hace un
    pre-filtro en ``analisis_especialistas``.

    Parámetros
    ----------
    params : dict
        Parámetros de búsqueda del endpoint GET /especialistas.
    page : int
        Página actual (1-indexed).
    limit : int
        Documentos por página.

    Retorna
    -------
    dict
        ``{total, page, limit, pages, has_next, has_prev, filters_applied, results}``
    """
    db = get_doctoralia_async_db()
    col_doc = db["doctor_profiles"]
    col_ana = db["analisis_especialistas"]

    orden = params.get("orden", "opiniones_desc")
    solo_analizados = params.get("solo_analizados", False)
    estado_analisis = params.get("estado_analisis")
    confiabilidad = params.get("confiabilidad")
    sospecha_fraude_param = params.get("sospecha_fraude")
    puntuacion_min = params.get("puntuacion_min")
    puntuacion_max = params.get("puntuacion_max")

    # Pre-filtro por analisis si es necesario
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
            filtro_ana["estatus_analisis"] = estado_analisis
        if confiabilidad:
            filtro_ana["analisis.confiabilidad"] = confiabilidad
        if sospecha_fraude_param is not None:
            filtro_ana["metadata_opiniones.sospecha_fraude"] = sospecha_fraude_param
        if puntuacion_min is not None:
            filtro_ana.setdefault("analisis.puntuacion", {})["$gte"] = puntuacion_min
        if puntuacion_max is not None:
            filtro_ana.setdefault("analisis.puntuacion", {})["$lte"] = puntuacion_max

        ids_con_analisis = set()
        async for doc in col_ana.find(filtro_ana, {"id_doctoralia": 1}):
            did = doc.get("id_doctoralia")
            if did:
                ids_con_analisis.add(did)

    # Construir filtro principal
    filtro = _construir_filtro_doctor_profiles(params)
    if ids_con_analisis is not None:
        filtro["doctor.id_doctoralia"] = {"$in": list(ids_con_analisis)}

    # Ordenamiento en MongoDB
    sort_instruccion = _construir_sort(orden)

    # Contar total
    total = await col_doc.count_documents(filtro)
    if total == 0:
        return _respuesta_vacia(params, page, limit)

    skip = (page - 1) * limit
    docs = [
        doc
        async for doc in col_doc.find(filtro)
        .sort(sort_instruccion)
        .skip(skip)
        .limit(limit)
    ]

    # Obtener IDs de doctoralia para batch de análisis
    doctoralia_ids = [
        (d.get("doctor") or {}).get("id_doctoralia")
        for d in docs
        if (d.get("doctor") or {}).get("id_doctoralia")
    ]
    mapa_analisis = await _obtener_analisis_batch(col_ana, doctoralia_ids)

    # Construir cards
    results = []
    ciudad_buscada = params.get("ciudad") or params.get("ciudad_slug")
    for doc in docs:
        did = (doc.get("doctor") or {}).get("id_doctoralia")
        analisis_doc = mapa_analisis.get(did) if did else None
        card = _construir_card(_serializar_id(dict(doc)), analisis_doc, ciudad_buscada=ciudad_buscada)
        results.append(card)

    # Reordenar: analizados primero, luego por puntuacion/orden en memoria
    sort_por_puntuacion = orden in ("puntuacion_desc", "puntuacion_asc")
    sort_por_recencia = orden == "recencia_analisis_desc"

    if sort_por_puntuacion:
        rev = orden == "puntuacion_desc"
        results.sort(
            key=lambda c: (
                0 if c.get("tiene_analisis") else 1,
                (
                    -((c.get("analisis") or {}).get("puntuacion_recomendacion") or 0)
                    if rev
                    else (
                        (c.get("analisis") or {}).get("puntuacion_recomendacion") or 0
                    )
                ),
            )
        )
    elif sort_por_recencia:
        results.sort(
            key=lambda c: (
                0 if c.get("tiene_analisis") else 1,
                (c.get("analisis") or {}).get("fecha_analisis") or "",
            ),
            reverse=True,
        )
    else:
        # Para otros ordenes, siempre poner analizados primero
        results.sort(key=lambda c: 0 if c.get("tiene_analisis") else 1)

    pages = math.ceil(total / limit) if limit else 1
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


async def _obtener_analisis_batch(col_ana, doctoralia_ids: list) -> dict:
    """
    Obtiene un mapa de análisis IA indexado por id_doctoralia en batch.

    Parámetros
    ----------
    col_ana : AsyncIOMotorCollection
        Colección ``analisis_especialistas``.
    doctoralia_ids : list[int]
        Lista de IDs de doctoralia a consultar.

    Retorna
    -------
    dict
        ``{id_doctoralia: documento_analisis}``.
    """
    if not doctoralia_ids:
        return {}
    mapa: dict = {}
    async for doc in col_ana.find({"id_doctoralia": {"$in": doctoralia_ids}}):
        did = doc.get("id_doctoralia")
        if did:
            mapa[did] = doc
    return mapa


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
