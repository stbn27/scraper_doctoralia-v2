"""
Constructor de prompts — Construye instrucciones y payload para el análisis NLP.
"""

import json
import re


def construir_prompt_sistema() -> str:
    """Retorna el prompt del sistema con reglas críticas y formato JSON."""
    return """Eres un sistema experto en evaluación de calidad de atención médica.
Analiza especialistas médicos cruzando opiniones, servicios, precios, consultorios,
perfil profesional, flags de pacientes, métricas locales y metadatos de muestreo.

CRITERIOS DE PUNTUACIÓN (escala 1-10):
- Sube la puntuación: opiniones recientes, verificadas, detalladas, diversas en fechas,
  menciones concretas de dolor, explicación, puntualidad, trato, seguimiento, servicios
  bien descritos, consultorio identificable y precios publicados.
- Baja la puntuación: opiniones antiguas, textos demasiado cortos, no verificadas,
  concentración temporal, calificaciones excesivamente perfectas, inconsistencias entre
  reseñas y perfil, servicios duplicados o mal estructurados, perfil incompleto, ausencia
  de consultorio, ausencia de precios, y sospecha de manipulación.
- La puntuacion_recomendacion NO debe ser el promedio de ratings. Debe reflejar calidad,
  confiabilidad y utilidad real de la evidencia.

REGLAS DE RESUMEN:
1. La primera oración NO debe repetir el nombre completo del médico ni la especialidad;
   esos datos ya están en metadatos. Inicia con una conclusión analítica del patrón.
2. El resumen es para el usuario final: debe ayudarle a decidir si vale la pena revisar
   el perfil o agendar. Usa lenguaje claro, natural y accionable, no tono de auditoría.
3. Puede tener hasta 5 oraciones/líneas cuando la evidencia lo justifique. Incluye lo bueno,
   lo malo y una cautela práctica si aplica.
4. Cruza opiniones + servicios + perfil. No resumas solo las reseñas.
5. Si hay precios concretos, menciónalos como transparencia cuando aplique e invita a revisar
   costos finales en el perfil.
6. Si casi no hay precios, menciona falta de transparencia.
7. Siempre menciona en el resumen la población atendida cuando el perfil la detalle: niños, adultos y/o adolescentes.
   Si solo aparece adultos, aclara que según el perfil solo atiende adultos.
8. Si atiende_ninos, atiende_adultos y atiende_adolescentes son false, NO concluyas que
   no atiende a esos grupos. Escribe: "el perfil no detalla qué tipos de pacientes atiende".
9. Evita saturar el resumen con porcentajes si no son necesarios; prioriza significado práctico.

REGLAS DE PUNTOS DÉBILES:
- Deben variar entre especialistas y estar anclados en evidencia concreta.
- Evita fórmulas repetidas como "ausencia de menciones sobre tiempos de espera" o
  "faltan más opiniones para concluir" salvo que sea el hallazgo central.
- Prioriza hallazgos verificables: falta de precios, pocas verificadas, concentración de
  opiniones, servicios poco claros, perfil incompleto, contradicciones perfil/reseñas,
  homogeneidad excesiva, señales comerciales raras, población atendida no detallada,
  consultorio ausente, servicios duplicados o sospecha de incentivación.

REGLAS DE EVIDENCIA:
- Cada salida debe citar hallazgos concretos del input: porcentajes de verificación,
  fechas/antigüedad, ratings, servicios y precios, completitud del perfil y patrones
  textuales de opiniones.
- Responde ÚNICAMENTE con el JSON solicitado, sin texto adicional."""


def construir_prompt_usuario(datos_preparados: dict) -> str:
    """Construye el prompt de usuario con payload compacto y trazable."""
    perfil = datos_preparados["perfil_limpio"]
    metricas = datos_preparados["metricas_locales"]
    opiniones = datos_preparados["opiniones_procesadas"]
    alertas = datos_preparados.get("alertas", [])
    metadatos_muestreo = datos_preparados.get("metadatos_muestreo", {})

    nota_muestreo = _construir_nota_muestreo(metadatos_muestreo)
    payload = {
        "perfil": perfil,
        "metricas_locales": metricas,
        "metadatos_muestreo": metadatos_muestreo,
        "nota_muestreo": nota_muestreo,
        "alertas_preprocesamiento": alertas,
        "opiniones": opiniones,
    }

    return f"""DATOS PARA ANALIZAR
{json.dumps(payload, ensure_ascii=False, indent=2)}

INSTRUCCIONES ESPECÍFICAS PARA ESTE CASO
- Usa la nota de muestreo para no confundir el subconjunto enviado con el volumen real.
- Si hay muestra parcial, evalúa representatividad y menciona el total real de opiniones.
- Si `perfil.perfil_detalla_pacientes` es false, escribe literalmente que el perfil no detalla qué tipos de pacientes atiende.
- Si `perfil.perfil_detalla_pacientes` es true, menciona en el resumen los grupos que sí aparecen como atendidos; si solo atiende adultos, dilo explícitamente.
- Evalúa transparencia de precios con `perfil.integridad_perfil.servicios_con_precio` y `servicios_sin_precio`.
- Si hay servicios con precio, explica que puede revisar esos precios en el perfil; si faltan muchos precios, úsalo como cautela.
- No inventes datos clínicos ni poblaciones atendidas.

RESPONDE EXACTAMENTE CON ESTE JSON:
{{
  "puntuacion_recomendacion": float (1.0-10.0),
  "resumen": "string de máximo 5 oraciones/líneas, específico y útil para usuario final; la primera no repite nombre completo ni especialidad",
  "puntos_fuertes": ["máximo 4 puntos concretos"],
  "puntos_debiles": ["mínimo 1, máximo 4 puntos concretos y variables"],
  "confiabilidad_opiniones": "alta|media|baja|sospechosa",
  "justificacion_puntuacion": "string breve explicando el score asignado con evidencia"
}}"""


def construir_analisis_minimo(especialista: dict, razon: str) -> dict:
    """Genera un análisis sin IA para médicos no aptos."""
    nombre = especialista.get("nombre", "Sin nombre")
    especialidad = especialista.get("especialidad", "Sin especialidad")

    mensajes_razon = {
        "sin_opiniones_suficientes": (
            f"El perfil no tiene suficientes opiniones para sostener una evaluación útil. "
            f"{nombre} ({especialidad}) requiere más evidencia verificable antes de asignar recomendación."
        ),
    }

    resumen = mensajes_razon.get(
        razon,
        f"El perfil no pudo ser analizado localmente por la razón: {razon}.",
    )

    return {
        "puntuacion_recomendacion": 0.0,
        "resumen": resumen,
        "puntos_fuertes": [],
        "puntos_debiles": [
            "Información insuficiente para evaluar calidad, consistencia y representatividad de la atención"
        ],
        "confiabilidad_opiniones": "baja",
        "justificacion_puntuacion": (
            f"No se asigna puntuación por {razon.replace('_', ' ')}."
        ),
    }


def construir_analisis_fraude_local(datos_preparados: dict) -> dict:
    """Genera un análisis local cuando la evidencia activa sospecha de fraude."""
    perfil = datos_preparados.get("perfil_limpio", {})
    metricas = datos_preparados.get("metricas_locales", {})
    razones = metricas.get("razones_fraude", [])
    total = metricas.get("total_opiniones_bd", 0)
    pct_corto = metricas.get("porcentaje_texto_corto", 0)
    pct_verif = metricas.get("porcentaje_verificadas", 0)
    integridad = perfil.get("integridad_perfil", {})

    puntos_debiles = [f"Sospecha de manipulación: {razon}" for razon in razones[:2]]
    if pct_corto:
        puntos_debiles.append(f"{pct_corto}% de las opiniones son muy cortas, lo que reduce profundidad útil.")
    if integridad.get("servicios_sin_precio", 0) > integridad.get("servicios_con_precio", 0):
        puntos_debiles.append("La mayoría de servicios no publica precio, limitando transparencia comercial.")
    if not perfil.get("perfil_detalla_pacientes"):
        puntos_debiles.append("El perfil no detalla qué tipos de pacientes atiende.")

    puntos_debiles = list(dict.fromkeys(puntos_debiles))[:4] or [
        "La evidencia local activa sospecha de fraude y no debe tratarse como reputación confiable."
    ]

    puntos_fuertes = []
    if pct_verif:
        puntos_fuertes.append(f"{pct_verif}% de opiniones declaran algún tipo de verificación.")
    if integridad.get("servicios_con_precio", 0) > 0:
        puntos_fuertes.append(f"Publica precios en {integridad.get('servicios_con_precio')} servicios.")
    puntos_fuertes = puntos_fuertes[:4]

    resumen = (
        f"El patrón de reseñas no es confiable para recomendar sin cautela: {total} opiniones activan señales locales de manipulación. "
        f"La evaluación queda penalizada por {', '.join(razones[:2]) if razones else 'homogeneidad anómala de reseñas'} y debe revisarse antes de usarla en ranking."
    )

    return reforzar_resultado_analisis({
        "puntuacion_recomendacion": 3.0,
        "resumen": resumen,
        "puntos_fuertes": puntos_fuertes,
        "puntos_debiles": puntos_debiles,
        "confiabilidad_opiniones": "sospechosa",
        "justificacion_puntuacion": (
            "La puntuación se mantiene baja porque la detección local de fraude pesa más "
            "que los ratings positivos o la verificación declarada."
        ),
    }, datos_preparados)


def _frase_pacientes(perfil: dict) -> str:
    grupos = []
    if perfil.get("atiende_ninos"):
        grupos.append("niños")
    if perfil.get("atiende_adultos"):
        grupos.append("adultos")
    if perfil.get("atiende_adolescentes"):
        grupos.append("adolescentes")

    if not grupos:
        return ""
    if grupos == ["adultos"]:
        return "Según su perfil, este especialista solo atiende adultos; considera esto si buscas atención para niños o adolescentes."
    if len(grupos) == 1:
        return f"Según su perfil, este especialista atiende {grupos[0]}."
    if len(grupos) == 2:
        grupos_txt = " y ".join(grupos)
    else:
        grupos_txt = ", ".join(grupos[:-1]) + f" y {grupos[-1]}"
    return f"Según su perfil, este especialista atiende {grupos_txt}."


def _limitar_resumen(resumen: str, max_oraciones: int = 5) -> str:
    partes = [p.strip() for p in re.split(r"(?<=[.!?])\s+", resumen.strip()) if p.strip()]
    if len(partes) <= max_oraciones:
        return resumen.strip()
    return " ".join(partes[:max_oraciones]).strip()


def reforzar_resultado_analisis(resultado: dict, datos_preparados: dict) -> dict:
    """
    Refuerza hallazgos objetivos para evitar salidas ambiguas del proveedor.

    Mantiene compatibilidad con la estructura actual y solo añade evidencia que
    ya existe en el payload: pacientes no detallados, precios y duplicados.
    """
    perfil = datos_preparados.get("perfil_limpio", {})
    integridad = perfil.get("integridad_perfil", {})
    resumen = str(resultado.get("resumen") or "").strip()
    debiles = [str(p).strip() for p in resultado.get("puntos_debiles", []) if str(p).strip()]
    fuertes = [str(p).strip() for p in resultado.get("puntos_fuertes", []) if str(p).strip()]

    if not perfil.get("perfil_detalla_pacientes"):
        frase = "el perfil no detalla qué tipos de pacientes atiende"
        if frase not in resumen.lower():
            resumen = f"{resumen} El perfil no detalla qué tipos de pacientes atiende.".strip()
        debiles.append("El perfil no detalla qué tipos de pacientes atiende.")
    else:
        frase = _frase_pacientes(perfil)
        resumen_lower = resumen.lower()
        menciona_pacientes = "atiende" in resumen_lower or "paciente" in resumen_lower
        if frase and not menciona_pacientes:
            resumen = f"{resumen} {frase}".strip()

    con_precio = int(integridad.get("servicios_con_precio") or 0)
    sin_precio = int(integridad.get("servicios_sin_precio") or 0)
    if con_precio > 0:
        frase_precio = f"Publica precios en {con_precio} servicios, una señal concreta de transparencia que puedes revisar en su perfil."
        if "precio" not in resumen.lower() and "transparen" not in resumen.lower():
            resumen = f"{resumen} {frase_precio}".strip()
        fuertes.append(frase_precio)
    if sin_precio > con_precio and sin_precio > 0:
        debiles.append(f"{sin_precio} servicios no muestran precio, lo que reduce transparencia para comparar costos.")

    duplicados = integridad.get("servicios_duplicados_detectados") or []
    if duplicados:
        muestra = ", ".join(duplicados[:3])
        debiles.append(f"Servicios duplicados o mal estructurados detectados: {muestra}.")

    resultado["resumen"] = _limitar_resumen(resumen, max_oraciones=5)
    resultado["puntos_fuertes"] = list(dict.fromkeys(fuertes))[:4]
    resultado["puntos_debiles"] = list(dict.fromkeys(debiles))[:4] or [
        "No hay suficientes señales específicas para identificar debilidades distintas."
    ]
    return resultado


def _construir_nota_muestreo(metadatos: dict) -> str:
    total = metadatos.get("total_opiniones_original", 0)
    enviadas = metadatos.get("total_opiniones_enviadas", 0)
    bloques = metadatos.get("bloques_muestreo", {}) or {}
    estrategia = metadatos.get("estrategia_muestreo", "sin_muestreo")
    partes = []
    for clave in ("recientes", "largas", "no_verificadas", "antiguas", "relleno"):
        cantidad = bloques.get(clave, 0)
        if cantidad:
            partes.append(f"{cantidad} {clave.replace('_', ' ')}")
    detalle = ", ".join(partes) if partes else estrategia
    nota = (
        f"El médico tiene {total} opiniones totales. Se comparten {enviadas} "
        f"seleccionadas mediante muestreo estratificado: {detalle}."
    )
    if bloques.get("antiguas", 0):
        nota += f" Se incluyen {bloques['antiguas']} opiniones antiguas para detectar consistencia histórica."
    return nota
