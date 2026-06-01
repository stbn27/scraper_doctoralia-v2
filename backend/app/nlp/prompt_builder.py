"""
Constructor de prompts — Construye el prompt del sistema y del usuario para el análisis.

Funciones principales:
    - construir_prompt_sistema: Prompt con el rol e instrucciones del modelo.
    - construir_prompt_usuario: Prompt con perfil, métricas y opiniones.
    - construir_analisis_minimo: Análisis sin IA para médicos no aptos.
"""

from datetime import datetime, timezone


def construir_prompt_sistema() -> str:
    """
    Retorna el prompt del sistema (rol e instrucciones del modelo).

    Incluye criterios de puntuación, factores que aumentan/reducen
    la puntuación, y reglas obligatorias para la respuesta.

    Retorna
    -------
    str
        Prompt del sistema completo.
    """
    return """Eres un sistema experto en evaluación de calidad de atención médica.
Tu tarea es analizar las opiniones de pacientes sobre un especialista médico
y generar una evaluación objetiva y estructurada.

CRITERIOS DE PUNTUACIÓN (escala 1-10):

- Factores que AUMENTAN la puntuación:
  1. Opiniones recientes (menos de 3 meses): peso alto
  2. Opiniones verificadas (cita o teléfono verificado): peso alto
  3. Textos largos y detallados (más de 30 palabras): peso medio
  4. Menciones específicas de profesionalismo, explicación del procedimiento, puntualidad, trato humano
  5. Diversidad de fechas (actividad sostenida en el tiempo)
  6. Múltiples servicios ofrecidos con precios transparentes

- Factores que REDUCEN la puntuación:
  1. Opiniones con más de 180 días de antigüedad: penalización moderada
  2. Opiniones con más de 365 días: penalización alta
  3. Textos muy cortos (menos de 15 palabras): penalización leve
  4. Opiniones no verificadas: penalización leve
  5. Alerta de sospecha de fraude detectada: penalización severa (-2 puntos mínimo)
  6. Muestra de opiniones muy reducida (menos de 5): penalización moderada

- REGLAS OBLIGATORIAS:
  1. La puntuacion_recomendacion NO debe ser el promedio de ratings de Doctoralia.
     Debe reflejar la calidad real de las opiniones según los criterios anteriores.
  2. puntos_debiles SIEMPRE debe tener contenido. Si todas las opiniones son positivas,
     busca ausencias: ¿no se menciona el precio? ¿no se habla del tiempo de espera?
     ¿las opiniones son muy cortas para ser concluyentes? Indícalo explícitamente.
  3. El resumen debe ser específico al especialista, mencionando su especialidad
     y al menos un detalle concreto de sus opiniones. Nunca frases genéricas.
  4. Si hay alerta de sospecha_fraude, mencionarlo explícitamente en el resumen.
  5. Responder ÚNICAMENTE con el JSON solicitado, sin texto adicional."""


def construir_prompt_usuario(datos_preparados: dict) -> str:
    """
    Construye el prompt del usuario con el perfil y opiniones limpios.

    Parámetros
    ----------
    datos_preparados : dict
        Dict retornado por preparar_datos_para_analisis() con claves:
        perfil_limpio, opiniones_procesadas, metricas_locales, alertas.

    Retorna
    -------
    str
        Prompt del usuario formateado con perfil, métricas y opiniones.
    """
    perfil = datos_preparados["perfil_limpio"]
    metricas = datos_preparados["metricas_locales"]
    opiniones = datos_preparados["opiniones_procesadas"]
    alertas = datos_preparados.get("alertas", [])

    # ── Sección PERFIL ──
    atiende_partes = []
    if perfil.get("atiende_ninos"):
        atiende_partes.append("niños")
    if perfil.get("atiende_adolescentes"):
        atiende_partes.append("adolescentes")
    if perfil.get("atiende_adultos"):
        atiende_partes.append("adultos")
    atiende_texto = ", ".join(atiende_partes) if atiende_partes else "No especificado"

    servicios = perfil.get("servicios", [])
    servicios_texto = ", ".join(servicios) if servicios else "No especificados"

    experiencia = perfil.get("experiencia", [])
    experiencia_texto = "; ".join(experiencia) if experiencia else "No especificada"

    # ── Sección ALERTAS ──
    alertas_bloque = ""
    if alertas:
        alertas_lineas = "\n".join(f"  ⚠️ {a}" for a in alertas)
        alertas_bloque = f"\nALERTAS DETECTADAS:\n{alertas_lineas}"

    # ── Sección FRAUDE ──
    fraude_bloque = ""
    if metricas.get("sospecha_fraude"):
        razones = metricas.get("razones_fraude", [])
        razones_texto = "\n".join(f"  🚨 {r}" for r in razones)
        fraude_bloque = (
            f"\n⚠️ SOSPECHA DE FRAUDE DETECTADA:\n{razones_texto}"
        )

    # ── Sección OPINIONES ──
    opiniones_formateadas: list[str] = []
    for i, op in enumerate(opiniones, 1):
        verificada = "Sí" if op.get("es_verificada") else "No"
        texto_corto = "Sí" if op.get("texto_corto") else "No"
        bloque = (
            f"--- OPINIÓN {i} ---\n"
            f"Antigüedad: {op['dias_antiguedad']} días | "
            f"Verificada: {verificada} | Texto corto: {texto_corto}\n"
            f"\"{op['texto']}\""
        )
        opiniones_formateadas.append(bloque)

    lista_opiniones = "\n\n".join(opiniones_formateadas)
    total_bd = metricas.get("total_opiniones_bd", 0)

    prompt = f"""PERFIL
Nombre: {perfil['nombre']}
Especialidad: {perfil['especialidad']}
Atiende: {atiende_texto}
Servicios: {servicios_texto}
Experiencia: {experiencia_texto}

MÉTRICAS CALCULADAS
- Total de opiniones en base de datos: {total_bd}
- Opiniones analizadas: {metricas.get('opiniones_enviadas_al_modelo', 0)}
- Promedio de antigüedad: {metricas.get('recencia_promedio_dias', 0)} días
- Porcentaje de opiniones verificadas: {metricas.get('porcentaje_verificadas', 0)}%
- Porcentaje de últimos 6 meses: {metricas.get('porcentaje_ultimos_6_meses', 0)}%
- Porcentaje de textos cortos (<15 palabras): {metricas.get('porcentaje_texto_corto', 0)}%{alertas_bloque}{fraude_bloque}

OPINIONES ({len(opiniones)} de {total_bd} en base de datos)
{lista_opiniones}

RESPONDE EXACTAMENTE CON ESTE JSON:
{{
  "puntuacion_recomendacion": float (1.0-10.0),
  "resumen": "string de 2-3 oraciones específicas",
  "puntos_fuertes": ["máximo 4 puntos concretos"],
  "puntos_debiles": ["mínimo 1, máximo 4 puntos concretos"],
  "confiabilidad_opiniones": "alta|media|baja|sospechosa",
  "justificacion_puntuacion": "string breve explicando el score asignado"
}}"""

    return prompt


def construir_analisis_minimo(especialista: dict, razon: str) -> dict:
    """
    Genera un análisis sin llamar a la IA para médicos no aptos.

    Usado cuando apto_para_ia = False (ej: menos de 3 opiniones).

    Parámetros
    ----------
    especialista : dict
        Documento completo del especialista desde MongoDB.
    razon : str
        Razón por la que no es apto (ej: "sin_opiniones_suficientes").

    Retorna
    -------
    dict
        Análisis mínimo con la estructura completa esperada por
        el repositorio analisis_repo.
    """
    nombre = especialista.get("nombre", "Sin nombre")
    especialidad = especialista.get("especialidad", "Sin especialidad")

    mensajes_razon = {
        "sin_opiniones_suficientes": (
            f"{nombre} ({especialidad}) no cuenta con suficientes opiniones "
            f"para generar un análisis significativo."
        ),
    }

    resumen = mensajes_razon.get(
        razon,
        f"{nombre} ({especialidad}) no pudo ser analizado: {razon}."
    )

    return {
        "puntuacion_recomendacion": 0.0,
        "resumen": resumen,
        "puntos_fuertes": [],
        "puntos_debiles": [
            "Información insuficiente para evaluar la calidad de atención"
        ],
        "confiabilidad_opiniones": "baja",
        "justificacion_puntuacion": (
            f"No se asigna puntuación por {razon.replace('_', ' ')}."
        ),
    }
