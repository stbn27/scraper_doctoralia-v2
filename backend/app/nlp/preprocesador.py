"""
Preprocesador local — Limpieza y filtrado de datos ANTES de llamar a la IA.

Funciones principales:
    - preparar_datos_para_analisis: Punto de entrada principal.
    - detectar_sospecha_fraude: Detección local de opiniones falsas.
"""

from datetime import datetime, timezone
from collections import Counter


def preparar_datos_para_analisis(
    especialista: dict,
    opiniones: list[dict],
) -> dict:
    """
    Prepara y limpia los datos de un especialista y sus opiniones
    para ser enviados al modelo de IA.

    Retorna un dict con:
    {
        "apto_para_ia": bool,
        "razon_no_apto": str | None,
        "perfil_limpio": dict,
        "opiniones_procesadas": list[dict],
        "metricas_locales": dict,
        "alertas": list[str],
    }
    """
    alertas: list[str] = []
    ahora = datetime.now(timezone.utc)
    total_opiniones = len(opiniones)

    # ── Regla 1: Mínimo de opiniones ──
    if total_opiniones < 3:
        perfil = _limpiar_perfil(especialista, total_opiniones)
        return {
            "apto_para_ia": False,
            "razon_no_apto": "sin_opiniones_suficientes",
            "perfil_limpio": perfil,
            "opiniones_procesadas": [],
            "metricas_locales": _calcular_metricas(
                opiniones, [], {"sospecha": False, "razones": []}, ahora
            ),
            "alertas": alertas,
        }

    if total_opiniones < 15:
        alertas.append(
            f"muestra_reducida: solo {total_opiniones} opiniones disponibles"
        )

    # ── Limpieza de opiniones ──
    opiniones_limpias = _limpiar_opiniones(opiniones, ahora)

    # ── Regla 2: Recencia ──
    recientes = [o for o in opiniones_limpias if o["dias_antiguedad"] <= 180]
    if len(recientes) == 0:
        alertas.append(
            "opiniones_desactualizadas: todas tienen más de 6 meses"
        )

    # ── Regla 3: Longitud mínima ──
    cortas = [o for o in opiniones_limpias if o["texto_corto"]]
    if total_opiniones > 0 and (len(cortas) / total_opiniones) > 0.6:
        alertas.append(
            f"mayoría_opiniones_cortas: {len(cortas)} de "
            f"{total_opiniones} tienen menos de 15 palabras"
        )

    # ── Regla 4: Detección de fraude ──
    fraude = detectar_sospecha_fraude(opiniones)

    # ── Muestreo inteligente ──
    opiniones_enviadas = _muestreo_inteligente(opiniones_limpias, total_opiniones)

    # ── Métricas locales ──
    metricas = _calcular_metricas(opiniones, opiniones_enviadas, fraude, ahora)

    # ── Perfil limpio ──
    perfil = _limpiar_perfil(especialista, total_opiniones)

    return {
        "apto_para_ia": True,
        "razon_no_apto": None,
        "perfil_limpio": perfil,
        "opiniones_procesadas": opiniones_enviadas,
        "metricas_locales": metricas,
        "alertas": alertas,
    }


def detectar_sospecha_fraude(opiniones: list[dict]) -> dict:
    """
    Detecta patrones de opiniones falsas localmente.

    Criterios:
    1. Rating 5.0 en 100% con más de 5 opiniones
    2. Longitudes de texto muy similares (80%+ en rango ±10 palabras)
    3. Nombres de autor duplicados o muy similares con cercanía temporal
    4. Múltiples opiniones del mismo autor en < 24 horas

    Retorna {"sospecha": bool, "razones": list[str]}
    """
    razones: list[str] = []

    if len(opiniones) < 2:
        return {"sospecha": False, "razones": []}

    # Criterio 1: Rating 5.0 en 100% con más de 5 opiniones
    ratings = [o.get("rating", 0) for o in opiniones if o.get("rating") is not None]
    if len(ratings) > 5 and all(r == 5.0 for r in ratings):
        razones.append(f"100% de ratings son 5.0 en {len(ratings)} opiniones")

    # Criterio 2: Longitudes muy similares
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

    # Criterio 3: Nombres de autor duplicados o muy similares
    autores = [o.get("autor", "").strip().lower() for o in opiniones if o.get("autor")]
    conteo_autores = Counter(autores)

    for autor, cantidad in conteo_autores.items():
        if cantidad > 1 and autor:
            razones.append(f"Nombre '{autor}' aparece {cantidad} veces")

    # Nombres subconjunto con menos de 30 min de diferencia
    opiniones_con_autor = [
        o for o in opiniones if o.get("autor") and (o.get("fecha") or o.get("fecha_publicacion"))
    ]
    for i, op_a in enumerate(opiniones_con_autor):
        for op_b in opiniones_con_autor[i + 1:]:
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

    # Criterio 4: Múltiples opiniones del mismo autor en < 24h
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

    # Eliminar duplicados manteniendo orden
    razones_unicas: list[str] = list(dict.fromkeys(razones))

    return {"sospecha": len(razones_unicas) > 0, "razones": razones_unicas}


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


def _limpiar_perfil(especialista: dict, total_opiniones: int) -> dict:
    """
    Limpia el perfil del especialista conservando solo campos necesarios.

    Del documento del especialista conserva: nombre, especialidad,
    experiencia (máx 4), servicios normalizados, flags de atención
    y total de opiniones. No incluye _id, rating_global, etc.
    """
    # Procesar servicios
    servicios_raw = especialista.get("servicios", []) or []
    servicios_procesados: list[str] = []
    nombres_vistos: set[str] = set()

    for servicio in servicios_raw:
        if isinstance(servicio, dict):
            nombre = (servicio.get("nombre") or "").strip()
            precio_desde = servicio.get("precio_desde")
            precio_texto = servicio.get("precio_texto")
            if nombre:
                nombre_norm = nombre.lower()
                if nombre_norm not in nombres_vistos:
                    nombres_vistos.add(nombre_norm)
                    if precio_desde:
                        servicios_procesados.append(f"{nombre} - desde ${precio_desde}")
                    elif precio_texto:
                        servicios_procesados.append(f"{nombre} - {precio_texto}")
                    else:
                        servicios_procesados.append(nombre)
        elif isinstance(servicio, str):
            nombre = servicio.strip()
            if nombre:
                nombre_norm = nombre.lower()
                if nombre_norm not in nombres_vistos:
                    nombres_vistos.add(nombre_norm)
                    servicios_procesados.append(nombre)

    # Experiencia: máximo 6 líneas
    experiencia_raw = especialista.get("experiencia", []) or []
    if isinstance(experiencia_raw, str):
        experiencia_raw = [experiencia_raw]
    experiencia = [str(e).strip() for e in experiencia_raw[:6] if e]
    pacientes = especialista.get("pacientes") or {}

    # Solo incluir si realmente ofrece atención (al menos un rango válido)
    atiende_ninos = bool(pacientes.get("atiende_ninos", False))
    atiende_adultos = bool(pacientes.get("atiende_adultos", False))
    atiende_adolescentes = bool(pacientes.get("atiende_adolescentes", False))

    # TODO: Pendiente agregar el rango de edades
    # Si los tres en false, agregar un texto que diga que no especifica el rango de pacientes
    if not atiende_ninos and not atiende_adultos and not atiende_adolescentes:
        servicios_procesados.append("No especifica el rango de pacientes")
    
    return {
        "nombre": especialista.get("nombre", "Sin nombre"),
        "especialidad": especialista.get("especialidad", "Sin especialidad"),
        "experiencia": experiencia,
        "servicios": servicios_procesados,
        "atiende_ninos": bool(pacientes.get("atiende_ninos", False)),
        "atiende_adultos": bool(pacientes.get("atiende_adultos", False)),
        "atiende_adolescentes": bool(pacientes.get("atiende_adolescentes", False)),
        "total_opiniones_en_bd": total_opiniones,
    }


def _limpiar_opiniones(opiniones: list[dict], ahora: datetime) -> list[dict]:
    """
    Limpia opiniones conservando solo campos necesarios para el análisis.

    No incluye _id, opinion_id, autor, doctor_id, rating individual, etc.
    """
    resultado: list[dict] = []

    for op in opiniones:
        texto = (op.get("texto") or "").strip()
        if not texto:
            continue

        fecha_pub = _parsear_fecha(op.get("fecha") or op.get("fecha_publicacion"))
        dias_antiguedad = (ahora - fecha_pub).days if fecha_pub else 999

        tipo_verif = (op.get("tipo_verificacion") or "").strip()
        es_verificada = tipo_verif in [
            "Cita verificada", "Número de teléfono verificado"
        ]

        palabras = len(texto.split())

        resultado.append({
            "texto": texto,
            "dias_antiguedad": max(dias_antiguedad, 0),
            "es_verificada": es_verificada,
            "texto_corto": palabras < 15,
            "antigua": dias_antiguedad > 180,
            "_palabras": palabras,  # auxiliar para muestreo, se elimina después
        })

    return resultado


def _muestreo_inteligente(
    opiniones_limpias: list[dict], total_original: int
) -> list[dict]:
    """
    Aplica muestreo inteligente si hay demasiadas opiniones.

    Estrategia:
    - <= 30: enviar todas.
    - 31-100: 20 recientes + 10 largas + 5 no verificadas recientes.
    - > 100: 25 recientes + 10 largas + 5 no verificadas + 5 antiguas.
    """
    total = len(opiniones_limpias)

    if total <= 30:
        return _eliminar_campo_auxiliar(opiniones_limpias)

    por_recencia = sorted(opiniones_limpias, key=lambda o: o["dias_antiguedad"])
    por_longitud = sorted(opiniones_limpias, key=lambda o: o["_palabras"], reverse=True)
    no_verificadas = sorted(
        [o for o in opiniones_limpias if not o["es_verificada"]],
        key=lambda o: o["dias_antiguedad"],
    )

    seleccionadas: list[dict] = []
    ids_vistos: set[int] = set()

    def _agregar(lista: list[dict], cantidad: int) -> None:
        """Agrega hasta `cantidad` opiniones únicas."""
        agregadas = 0
        for op in lista:
            if agregadas >= cantidad:
                break
            id_op = id(op)
            if id_op not in ids_vistos:
                ids_vistos.add(id_op)
                seleccionadas.append(op)
                agregadas += 1

    if total <= 100:
        _agregar(por_recencia, 20)
        _agregar(por_longitud, 10)
        _agregar(no_verificadas, 5)
    else:
        _agregar(por_recencia, 25)
        _agregar(por_longitud, 10)
        _agregar(no_verificadas, 5)
        por_antiguedad = sorted(
            opiniones_limpias, key=lambda o: o["dias_antiguedad"], reverse=True
        )
        _agregar(por_antiguedad, 5)

    seleccionadas.sort(key=lambda o: o["dias_antiguedad"])
    return _eliminar_campo_auxiliar(seleccionadas)


def _eliminar_campo_auxiliar(opiniones: list[dict]) -> list[dict]:
    """Elimina el campo auxiliar `_palabras` de cada opinión."""
    return [{k: v for k, v in op.items() if k != "_palabras"} for op in opiniones]


def _calcular_metricas(
    opiniones_originales: list[dict],
    opiniones_enviadas: list[dict],
    fraude: dict,
    ahora: datetime,
) -> dict:
    """
    Calcula métricas locales sobre las opiniones para incluir en el análisis.

    Retorna dict con: totales, porcentajes de verificación, recencia,
    longitud promedio, texto corto, rating y datos de fraude.
    """
    total = len(opiniones_originales)

    if total == 0:
        return {
            "total_opiniones_bd": 0,
            "opiniones_enviadas_al_modelo": len(opiniones_enviadas),
            "porcentaje_verificadas": 0.0,
            "recencia_promedio_dias": 0.0,
            "longitud_promedio_palabras": 0.0,
            "porcentaje_texto_corto": 0.0,
            "porcentaje_ultimos_6_meses": 0.0,
            "rating_promedio": 0.0,
            "sospecha_fraude": fraude.get("sospecha", False),
            "razones_fraude": fraude.get("razones", []),
        }

    # Porcentaje de verificadas
    verificadas = sum(
        1 for o in opiniones_originales
        if (o.get("tipo_verificacion") or "").strip() in [
            "Cita verificada", "Número de teléfono verificado"
        ]
    )
    pct_verificadas = round((verificadas / total) * 100, 1)

    # Recencia promedio
    dias_lista: list[int] = []
    recientes_6m = 0
    for o in opiniones_originales:
        fecha = _parsear_fecha(o.get("fecha_publicacion"))
        if fecha:
            dias = max((ahora - fecha).days, 0)
            dias_lista.append(dias)
            if dias <= 180:
                recientes_6m += 1

    recencia_prom = round(sum(dias_lista) / len(dias_lista), 1) if dias_lista else 0.0
    pct_6m = round((recientes_6m / total) * 100, 1)

    # Longitud promedio y texto corto
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

    # Rating promedio
    ratings = [o.get("rating", 0) for o in opiniones_originales if o.get("rating") is not None]
    rating_prom = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

    return {
        "total_opiniones_bd": total,
        "opiniones_enviadas_al_modelo": len(opiniones_enviadas),
        "porcentaje_verificadas": pct_verificadas,
        "recencia_promedio_dias": recencia_prom,
        "longitud_promedio_palabras": long_prom,
        "porcentaje_texto_corto": pct_corto,
        "porcentaje_ultimos_6_meses": pct_6m,
        "rating_promedio": rating_prom,
        "sospecha_fraude": fraude.get("sospecha", False),
        "razones_fraude": fraude.get("razones", []),
    }
