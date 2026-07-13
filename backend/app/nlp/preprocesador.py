"""
Preprocesador local — Limpieza y filtrado de datos ANTES de llamar a la IA.

Funciones principales:
    - preparar_datos_para_analisis: Punto de entrada principal.
    - detectar_sospecha_fraude: Detección local de opiniones falsas.
"""

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone


VENTANA_RECIENTE_DIAS = 180
MAX_OPINIONES_MODELO = 50
MIN_OPINIONES_IA = 5


def preparar_datos_para_analisis(
    especialista: dict,
    opiniones: list[dict],
    min_opiniones_ia: int = MIN_OPINIONES_IA,
) -> dict:
    """
    Prepara y limpia los datos de un especialista y sus opiniones
    para ser enviados al modelo de IA.

    Retorna un dict con perfil normalizado, opiniones seleccionadas,
    métricas locales y metadatos descriptivos del muestreo.
    """
    esp_data = {**especialista, **especialista.get("doctor", {})} if "doctor" in especialista and isinstance(especialista.get("doctor"), dict) else especialista

    alertas: list[str] = []
    ahora = datetime.now(timezone.utc)
    total_opiniones = len(opiniones)
    total_reportado_perfil = _entero_seguro(esp_data.get("total_opiniones"))

    if total_opiniones < min_opiniones_ia:
        perfil = _limpiar_perfil(esp_data, total_opiniones, total_reportado_perfil)
        return {
            "apto_para_ia": False,
            "razon_no_apto": "sin_opiniones_suficientes",
            "perfil_limpio": perfil,
            "opiniones_procesadas": [],
            "metricas_locales": _calcular_metricas(
                opiniones,
                [],
                {"sospecha": False, "razones": [], "severidad": "ninguna"},
                ahora,
                total_reportado_perfil,
            ),
            "metadatos_muestreo": _metadatos_muestreo_vacio(
                total_opiniones, total_reportado_perfil
            ),
            "alertas": alertas,
        }

    if total_opiniones < 15:
        alertas.append(
            f"muestra_reducida: solo {total_opiniones} opiniones disponibles"
        )

    opiniones_limpias = _deduplicar_opiniones(_limpiar_opiniones(opiniones, ahora))

    recientes = [
        o for o in opiniones_limpias if o["dias_antiguedad"] <= VENTANA_RECIENTE_DIAS
    ]
    if len(recientes) == 0:
        alertas.append("opiniones_desactualizadas: todas tienen más de 6 meses")

    cortas = [o for o in opiniones_limpias if o["texto_corto"]]
    if total_opiniones > 0 and (len(cortas) / total_opiniones) > 0.6:
        alertas.append(
            f"mayoría_opiniones_cortas: {len(cortas)} de "
            f"{total_opiniones} tienen menos de 15 palabras"
        )

    fraude = detectar_sospecha_fraude(opiniones)

    resultado_muestreo = _muestreo_inteligente(
        opiniones_limpias,
        total_opiniones,
        total_reportado_perfil,
    )
    opiniones_enviadas = resultado_muestreo["opiniones"]

    metricas = _calcular_metricas(
        opiniones, opiniones_enviadas, fraude, ahora, total_reportado_perfil
    )
    perfil = _limpiar_perfil(especialista, total_opiniones, total_reportado_perfil)

    return {
        "apto_para_ia": True,
        "razon_no_apto": None,
        "perfil_limpio": perfil,
        "opiniones_procesadas": opiniones_enviadas,
        "metricas_locales": metricas,
        "metadatos_muestreo": resultado_muestreo["metadatos"],
        "alertas": alertas,
    }


def detectar_sospecha_fraude(opiniones: list[dict]) -> dict:
    """
    Detecta patrones de opiniones falsas localmente.

    Criterios:
    1. Rating 5.0 en 100% con más de 5 opiniones.
    2. Longitudes de texto muy similares (80%+ en rango ±10 palabras).
    3. Nombres de autor duplicados o muy similares con cercanía temporal.
    4. Múltiples opiniones del mismo autor en < 24 horas.
    """
    razones: list[str] = []

    if len(opiniones) < 2:
        return {"sospecha": False, "razones": []}

    ratings = [o.get("rating", 0) for o in opiniones if o.get("rating") is not None]
    if len(ratings) > 5 and all(r == 5.0 for r in ratings):
        razones.append(f"100% de ratings son 5.0 en {len(ratings)} opiniones")

    textos = [o.get("texto", "") for o in opiniones if o.get("texto")]
    longitudes = [len(t.split()) for t in textos]

    if len(longitudes) >= 5:
        mediana = sorted(longitudes)[len(longitudes) // 2]
        en_rango = sum(1 for lg in longitudes if abs(lg - mediana) <= 10)
        porcentaje_en_rango = en_rango / len(longitudes)
        if porcentaje_en_rango >= 0.8:
            razones.append(
                f"{en_rango}/{len(longitudes)} opiniones tienen longitud "
                f"similar (±10 palabras de la mediana {mediana})"
            )

    autores = [o.get("autor", "").strip().lower() for o in opiniones if o.get("autor")]
    conteo_autores = Counter(autores)

    for autor, cantidad in conteo_autores.items():
        if cantidad > 1 and autor:
            razones.append(f"Nombre '{autor}' aparece {cantidad} veces")

    opiniones_con_autor = [
        o
        for o in opiniones
        if o.get("autor") and (o.get("fecha") or o.get("fecha_publicacion"))
    ]
    for i, op_a in enumerate(opiniones_con_autor):
        for op_b in opiniones_con_autor[i + 1 :]:
            nombre_a = op_a["autor"].strip().lower()
            nombre_b = op_b["autor"].strip().lower()
            if nombre_a == nombre_b:
                continue
            es_subconjunto = nombre_a in nombre_b or nombre_b in nombre_a
            if not es_subconjunto:
                continue
            fecha_a = _parsear_fecha(op_a.get("fecha") or op_a.get("fecha_publicacion"))
            fecha_b = _parsear_fecha(op_b.get("fecha") or op_b.get("fecha_publicacion"))
            if fecha_a and fecha_b:
                diferencia = abs((fecha_a - fecha_b).total_seconds())
                if diferencia < 1800:
                    razones.append(
                        f"Nombres similares '{op_a['autor']}' y "
                        f"'{op_b['autor']}' con menos de 30 min de diferencia"
                    )

    autores_con_fechas: dict[str, list[datetime]] = {}
    for op in opiniones:
        autor = (op.get("autor") or "").strip().lower()
        fecha = _parsear_fecha(op.get("fecha") or op.get("fecha_publicacion"))
        if autor and fecha:
            autores_con_fechas.setdefault(autor, []).append(fecha)

    for autor, fechas in autores_con_fechas.items():
        if len(fechas) < 2:
            continue
        fechas_ord = sorted(fechas)
        for i in range(len(fechas_ord) - 1):
            dif_horas = (fechas_ord[i + 1] - fechas_ord[i]).total_seconds() / 3600
            if dif_horas < 24:
                razones.append(
                    f"Autor '{autor}' publicó múltiples opiniones en menos de 24 horas"
                )
                break

    razones_unicas: list[str] = list(dict.fromkeys(razones))
    severidad = "ninguna"
    if len(razones_unicas) >= 2:
        severidad = "media"
    if len(razones_unicas) >= 3:
        severidad = "alta"
    return {
        "sospecha": len(razones_unicas) > 0,
        "razones": razones_unicas,
        "severidad": severidad,
    }


def _parsear_fecha(valor) -> datetime | None:
    """Convierte un valor de fecha a datetime con timezone UTC."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            return valor.replace(tzinfo=timezone.utc)
        return valor
    if isinstance(valor, str):
        try:
            fecha = datetime.fromisoformat(valor)
            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=timezone.utc)
            return fecha
        except (ValueError, TypeError):
            return None
    return None


def _limpiar_perfil(
    especialista: dict,
    total_opiniones_disponibles: int,
    total_opiniones_reportadas: int | None = None,
) -> dict:
    """Normaliza el perfil conservando campos útiles para el análisis."""
    servicios_raw = especialista.get("servicios", []) or especialista.get("servicios_y_precios", []) or []
    servicios_normalizados = _normalizar_servicios(servicios_raw)
    servicios_procesados: list[dict] = []
    servicios_duplicados: list[str] = []
    nombres_vistos: set[str] = set()

    for servicio in servicios_normalizados:
        nombre = (servicio.get("nombre") or servicio.get("servicio") or "").strip()
        if not nombre:
            continue
        nombre_norm = _normalizar_texto(nombre)
        if nombre_norm in nombres_vistos:
            servicios_duplicados.append(nombre)
            continue
        nombres_vistos.add(nombre_norm)
        precio_desde = servicio.get("precio_desde")
        precio_texto = servicio.get("precio_texto") or servicio.get("precio")
        servicios_procesados.append(
            {
                "nombre": nombre,
                "precio_desde": precio_desde,
                "precio_texto": precio_texto,
                "tiene_precio": bool(precio_desde or precio_texto),
            }
        )

    experiencia_raw = especialista.get("experiencia", []) or []
    if isinstance(experiencia_raw, str):
        experiencia_raw = _normalizar_experiencia_string(experiencia_raw)
    experiencia = [str(e).strip() for e in experiencia_raw[:6] if e]

    pacientes = _normalizar_pacientes(especialista.get("pacientes") or especialista.get("pacientes_que_atiende") or {})
    atiende_ninos = bool(pacientes.get("atiende_ninos", pacientes.get("ninos", False)))
    atiende_adultos = bool(pacientes.get("atiende_adultos", pacientes.get("adultos", False)))
    atiende_adolescentes = bool(pacientes.get("atiende_adolescentes", pacientes.get("adolescentes", False)))
    perfil_detalla_pacientes = atiende_ninos or atiende_adultos or atiende_adolescentes

    consultorios_raw = especialista.get("consultorios", []) or especialista.get("direcciones", []) or []
    consultorios = _normalizar_consultorios(consultorios_raw)
    servicios_con_precio = sum(1 for s in servicios_procesados if s["tiene_precio"])
    servicios_sin_precio = len(servicios_procesados) - servicios_con_precio

    integridad = {
        "total_servicios": len(servicios_procesados),
        "servicios_con_precio": servicios_con_precio,
        "servicios_sin_precio": servicios_sin_precio,
        "servicios_duplicados_detectados": list(dict.fromkeys(servicios_duplicados)),
        "total_consultorios": len(consultorios),
        "perfil_detalla_pacientes": perfil_detalla_pacientes,
        "tiene_experiencia": bool(experiencia),
        "tiene_rating_global": especialista.get("rating_global") is not None,
    }

    especialidades_lista = especialista.get("especialidades")
    especialidad_nom = especialista.get("especialidad") or (
        especialidades_lista[0] if isinstance(especialidades_lista, list) and especialidades_lista else "Sin especialidad"
    )
    if isinstance(especialidad_nom, list) and especialidad_nom:
        especialidad_nom = especialidad_nom[0]

    return {
        "nombre": especialista.get("nombre", "Sin nombre"),
        "especialidad": str(especialidad_nom),
        "ciudad": especialista.get("ciudad") or (especialista.get("estado", [None])[0] if isinstance(especialista.get("estado"), list) else especialista.get("estado")),
        "rating_global": especialista.get("rating_global"),
        "experiencia": experiencia,
        "servicios": servicios_procesados,
        "consultorios": consultorios,
        "atiende_ninos": atiende_ninos,
        "atiende_adultos": atiende_adultos,
        "atiende_adolescentes": atiende_adolescentes,
        "perfil_detalla_pacientes": perfil_detalla_pacientes,
        "integridad_perfil": integridad,
        "opiniones_disponibles_en_bd": total_opiniones_disponibles,
        "total_opiniones_reportadas_perfil": total_opiniones_reportadas,
    }


def _limpiar_opiniones(opiniones: list[dict], ahora: datetime) -> list[dict]:
    """Limpia opiniones conservando campos útiles y una clave estable."""
    resultado: list[dict] = []

    for op in opiniones:
        texto = (op.get("texto") or "").strip()
        if not texto:
            continue

        fecha_pub = _parsear_fecha(op.get("fecha") or op.get("fecha_publicacion"))
        dias_antiguedad = (ahora - fecha_pub).days if fecha_pub else 999

        tipo_verif = (op.get("tipo_verificacion") or "").strip()
        es_verificada = tipo_verif in [
            "Cita verificada",
            "Número de teléfono verificado",
        ]
        palabras = len(texto.split())

        resultado.append(
            {
                "opinion_id": op.get("opinion_id"),
                "autor": op.get("autor"),
                "rating": op.get("rating"),
                "texto": texto,
                "fecha_publicacion": fecha_pub.isoformat() if fecha_pub else None,
                "dias_antiguedad": max(dias_antiguedad, 0),
                "es_verificada": es_verificada,
                "tipo_verificacion": tipo_verif or None,
                "servicio_consultado": op.get("servicio_consultado"),
                "consultorio": op.get("consultorio"),
                "texto_corto": palabras < 15,
                "antigua": dias_antiguedad > VENTANA_RECIENTE_DIAS,
                "_dedup_key": _clave_opinion_estable(op),
                "_fecha_orden": fecha_pub.timestamp() if fecha_pub else 0,
                "_palabras": palabras,
            }
        )

    return resultado


def _muestreo_inteligente(
    opiniones_limpias: list[dict],
    total_original: int,
    total_reportado_perfil: int | None = None,
) -> dict:
    """
    Selecciona máximo 50 opiniones con muestreo estratificado.

    - <= 50: todas.
    - 51-120: 30 recientes + 15 largas + 5 no verificadas recientes.
    - > 120: 25 recientes + 10 largas + 5 no verificadas + 10 antiguas.

    La salida queda ordenada por recencia descendente: más recientes primero.
    Si un bloque no alcanza su cuota, se rellena con las mejores restantes.
    """
    opiniones_unicas = _deduplicar_opiniones(opiniones_limpias)
    total = len(opiniones_unicas)

    if total <= MAX_OPINIONES_MODELO:
        seleccionadas = sorted(opiniones_unicas, key=lambda o: o["dias_antiguedad"])
        bloques = {
            "recientes": len(seleccionadas),
            "largas": 0,
            "no_verificadas": 0,
            "antiguas": 0,
            "relleno": 0,
        }
        return {
            "opiniones": _eliminar_campos_auxiliares(seleccionadas),
            "metadatos": _construir_metadatos_muestreo(
                total_original,
                len(seleccionadas),
                "todas_las_opiniones_disponibles",
                bloques,
                total_reportado_perfil,
            ),
        }

    por_recencia = sorted(opiniones_unicas, key=lambda o: o["dias_antiguedad"])
    por_longitud = sorted(opiniones_unicas, key=lambda o: o["_palabras"], reverse=True)
    no_verificadas = sorted(
        [o for o in opiniones_unicas if not o["es_verificada"]],
        key=lambda o: o["dias_antiguedad"],
    )
    por_antiguedad = sorted(
        opiniones_unicas, key=lambda o: o["dias_antiguedad"], reverse=True
    )

    seleccionadas: list[dict] = []
    claves_vistas: set[str] = set()
    bloques = {
        "recientes": 0,
        "largas": 0,
        "no_verificadas": 0,
        "antiguas": 0,
        "relleno": 0,
    }

    def agregar(lista: list[dict], cantidad: int, bloque: str) -> None:
        agregadas = 0
        for op in lista:
            if agregadas >= cantidad or len(seleccionadas) >= MAX_OPINIONES_MODELO:
                break
            clave = op["_dedup_key"]
            if clave in claves_vistas:
                continue
            claves_vistas.add(clave)
            seleccionadas.append(op)
            agregadas += 1
            bloques[bloque] += 1

    if total <= 120:
        estrategia = "30_recientes + 15_largas + 5_no_verificadas"
        # Reservar minorías primero evita que queden absorbidas por el bloque reciente.
        agregar(no_verificadas, 5, "no_verificadas")
        agregar(por_recencia, 30, "recientes")
        agregar(por_longitud, 15, "largas")
    else:
        estrategia = "25_recientes + 10_largas + 5_no_verificadas + 10_antiguas"
        agregar(no_verificadas, 5, "no_verificadas")
        agregar(por_antiguedad, 10, "antiguas")
        agregar(por_recencia, 25, "recientes")
        agregar(por_longitud, 10, "largas")

    if len(seleccionadas) < MAX_OPINIONES_MODELO:
        agregar(por_recencia, MAX_OPINIONES_MODELO - len(seleccionadas), "relleno")
    if len(seleccionadas) < MAX_OPINIONES_MODELO:
        agregar(por_longitud, MAX_OPINIONES_MODELO - len(seleccionadas), "relleno")

    seleccionadas = sorted(seleccionadas, key=lambda o: o["dias_antiguedad"])
    return {
        "opiniones": _eliminar_campos_auxiliares(seleccionadas),
        "metadatos": _construir_metadatos_muestreo(
            total_original,
            len(seleccionadas),
            estrategia,
            bloques,
            total_reportado_perfil,
        ),
    }


def _deduplicar_opiniones(opiniones: list[dict]) -> list[dict]:
    """Deduplica por opinion_id o hash estable de contenido manteniendo orden."""
    resultado: list[dict] = []
    vistas: set[str] = set()
    for op in opiniones:
        clave = op.get("_dedup_key") or _clave_opinion_estable(op)
        if clave in vistas:
            continue
        vistas.add(clave)
        op["_dedup_key"] = clave
        resultado.append(op)
    return resultado


def _eliminar_campos_auxiliares(opiniones: list[dict]) -> list[dict]:
    auxiliares = {"_palabras", "_dedup_key", "_fecha_orden"}
    return [{k: v for k, v in op.items() if k not in auxiliares} for op in opiniones]


def _clave_opinion_estable(opinion: dict) -> str:
    opinion_id = opinion.get("opinion_id")
    if opinion_id not in (None, ""):
        return f"opinion_id:{opinion_id}"
    partes = [
        str(opinion.get("doctor_id") or ""),
        _normalizar_texto(opinion.get("autor") or ""),
        _normalizar_texto(opinion.get("texto") or ""),
        str(opinion.get("fecha") or opinion.get("fecha_publicacion") or ""),
        str(opinion.get("rating") or ""),
    ]
    digest = hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()
    return f"hash:{digest}"


def _construir_metadatos_muestreo(
    total_original: int,
    total_enviadas: int,
    estrategia: str,
    bloques: dict,
    total_reportado_perfil: int | None = None,
) -> dict:
    return {
        "total_opiniones_original": total_original,
        "opiniones_disponibles_en_bd": total_original,
        "total_opiniones_reportadas_perfil": total_reportado_perfil,
        "total_opiniones_enviadas": total_enviadas,
        "estrategia_muestreo": estrategia,
        "bloques_muestreo": bloques,
        "ventana_reciente_dias": VENTANA_RECIENTE_DIAS,
        "hay_muestra_parcial": total_enviadas < total_original,
        "orden_salida": "recencia_descendente_mas_recientes_primero",
    }


def _metadatos_muestreo_vacio(
    total_original: int, total_reportado_perfil: int | None = None
) -> dict:
    return _construir_metadatos_muestreo(
        total_original,
        0,
        "sin_muestreo_no_apto_para_ia",
        {"recientes": 0, "largas": 0, "no_verificadas": 0, "antiguas": 0, "relleno": 0},
        total_reportado_perfil,
    )


def _calcular_metricas(
    opiniones_originales: list[dict],
    opiniones_enviadas: list[dict],
    fraude: dict,
    ahora: datetime,
    total_reportado_perfil: int | None = None,
) -> dict:
    """Calcula métricas locales para incluir en el análisis y persistencia."""
    total = len(opiniones_originales)

    if total == 0:
        return {
            "total_opiniones_bd": 0,
            "opiniones_disponibles_en_bd": 0,
            "total_opiniones_reportadas_perfil": total_reportado_perfil,
            "opiniones_enviadas_al_modelo": len(opiniones_enviadas),
            "porcentaje_verificadas": 0.0,
            "recencia_promedio_dias": 0.0,
            "longitud_promedio_palabras": 0.0,
            "porcentaje_texto_corto": 0.0,
            "porcentaje_ultimos_6_meses": 0.0,
            "rating_promedio": 0.0,
            "sospecha_fraude": fraude.get("sospecha", False),
            "razones_fraude": fraude.get("razones", []),
            "severidad_sospecha_fraude": fraude.get("severidad", "ninguna"),
        }

    verificadas = sum(
        1
        for o in opiniones_originales
        if (o.get("tipo_verificacion") or "").strip()
        in ["Cita verificada", "Número de teléfono verificado"]
    )
    pct_verificadas = round((verificadas / total) * 100, 1)

    dias_lista: list[int] = []
    recientes_6m = 0
    for o in opiniones_originales:
        fecha = _parsear_fecha(o.get("fecha") or o.get("fecha_publicacion"))
        if fecha:
            dias = max((ahora - fecha).days, 0)
            dias_lista.append(dias)
            if dias <= VENTANA_RECIENTE_DIAS:
                recientes_6m += 1

    recencia_prom = round(sum(dias_lista) / len(dias_lista), 1) if dias_lista else 0.0
    pct_6m = round((recientes_6m / total) * 100, 1)

    longitudes: list[int] = []
    textos_cortos = 0
    for o in opiniones_originales:
        texto = (o.get("texto") or "").strip()
        if texto:
            palabras = len(texto.split())
            longitudes.append(palabras)
            if palabras < 15:
                textos_cortos += 1

    long_prom = round(sum(longitudes) / len(longitudes), 1) if longitudes else 0.0
    pct_corto = round((textos_cortos / total) * 100, 1)

    ratings = [
        o.get("rating", 0) for o in opiniones_originales if o.get("rating") is not None
    ]
    rating_prom = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

    return {
        "total_opiniones_bd": total,
        "opiniones_disponibles_en_bd": total,
        "total_opiniones_reportadas_perfil": total_reportado_perfil,
        "opiniones_enviadas_al_modelo": len(opiniones_enviadas),
        "porcentaje_verificadas": pct_verificadas,
        "recencia_promedio_dias": recencia_prom,
        "longitud_promedio_palabras": long_prom,
        "porcentaje_texto_corto": pct_corto,
        "porcentaje_ultimos_6_meses": pct_6m,
        "rating_promedio": rating_prom,
        "sospecha_fraude": fraude.get("sospecha", False),
        "razones_fraude": fraude.get("razones", []),
        "severidad_sospecha_fraude": fraude.get("severidad", "ninguna"),
    }


def _entero_seguro(valor) -> int | None:
    if valor in (None, ""):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _normalizar_texto(valor: str) -> str:
    return re.sub(r"\s+", " ", str(valor).strip().lower())


def _normalizar_experiencia_string(valor: str) -> list[str]:
    texto = valor.strip()
    if texto.startswith("[") and texto.endswith("]"):
        texto = texto[1:-1]
    partes = re.split(r"\.\s*,\s*|,\s*(?=[A-ZÁÉÍÓÚÑ])", texto)
    return [p.strip() for p in partes if p.strip()][:6]


def _normalizar_servicios(servicios_raw) -> list[dict]:
    if isinstance(servicios_raw, list):
        return servicios_raw
    if not isinstance(servicios_raw, str):
        return []
    servicios: list[dict] = []
    for bloque in re.findall(r"\{([^{}]+)\}", servicios_raw):
        nombre = _extraer_campo_bloque(bloque, "nombre", "precio_desde")
        precio_desde_raw = _extraer_campo_bloque(bloque, "precio_desde", "precio_texto")
        precio_texto = _extraer_campo_bloque(bloque, "precio_texto", None)
        precio_desde = None
        if precio_desde_raw and precio_desde_raw.lower() != "null":
            try:
                precio_desde = int(float(precio_desde_raw.replace(",", "")))
            except ValueError:
                precio_desde = None
        servicios.append(
            {
                "nombre": None if not nombre or nombre.lower() == "null" else nombre,
                "precio_desde": precio_desde,
                "precio_texto": (
                    None
                    if not precio_texto or precio_texto.lower() == "null"
                    else precio_texto
                ),
            }
        )
    return servicios


def _normalizar_consultorios(consultorios_raw) -> list[dict]:
    if isinstance(consultorios_raw, list):
        return consultorios_raw
    if not isinstance(consultorios_raw, str):
        return []
    consultorios: list[dict] = []
    for bloque in re.findall(r"\{([^{}]+)\}", consultorios_raw):
        direccion = _extraer_campo_bloque(bloque, "direccion", "clinica")
        clinica = _extraer_campo_bloque(bloque, "clinica", None)
        consultorios.append(
            {
                "direccion": (
                    None if not direccion or direccion.lower() == "null" else direccion
                ),
                "clinica": (
                    None if not clinica or clinica.lower() == "null" else clinica
                ),
            }
        )
    return consultorios


def _normalizar_pacientes(pacientes_raw) -> dict:
    if isinstance(pacientes_raw, dict):
        return pacientes_raw
    if not isinstance(pacientes_raw, str):
        return {}
    return {
        "atiende_ninos": _parse_bool(
            _extraer_campo_bloque(pacientes_raw, "atiende_ninos", "atiende_adultos")
        ),
        "atiende_adultos": _parse_bool(
            _extraer_campo_bloque(
                pacientes_raw, "atiende_adultos", "atiende_adolescentes"
            )
        ),
        "atiende_adolescentes": _parse_bool(
            _extraer_campo_bloque(pacientes_raw, "atiende_adolescentes", None)
        ),
    }


def _extraer_campo_bloque(bloque: str, campo: str, siguiente: str | None) -> str | None:
    if siguiente:
        patron = rf"{re.escape(campo)}=(.*?)(?:,\s*{re.escape(siguiente)}=|$)"
    else:
        patron = rf"{re.escape(campo)}=(.*)$"
    match = re.search(patron, bloque)
    return match.group(1).strip() if match else None


def _parse_bool(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower().strip("}") == "true"
