# Pipeline NLP — uso, arquitectura y ajustes

Esta guía documenta el pipeline que analiza especialistas médicos con opiniones de MongoDB y modelos remotos. El objetivo operativo actual es procesar en masa sin gastar tokens en casos locales, mantener trazabilidad y reanudar sin recalcular análisis válidos.

## Flujo general

1. `backend/app/nlp/analizador_pipeline.py` carga especialistas desde MongoDB.
2. Para cada candidato consulta opiniones en `opiniones` por `doctor_id`.
3. `backend/app/nlp/preprocesador.py` limpia perfil/opiniones, detecta fraude local, calcula métricas y selecciona una muestra representativa.
4. Si el caso no es apto por pocas opiniones descargadas, se guarda análisis local sin llamar al LLM.
5. Si hay sospecha de fraude local pero alcanza el mínimo de opiniones, la señal se envía al LLM como contexto de cautela, no como cierre automático.
6. Si el caso requiere IA, `backend/app/nlp/prompt_builder.py` construye el prompt con perfil, servicios, precios, consultorios, métricas y metadatos de muestreo.
7. `backend/app/nlp/modelos/*_modelo.py` invoca al proveedor remoto y registra cada request real antes de hacer HTTP.
8. `backend/app/nlp/repositorios/analisis_repo.py` guarda el resultado en `analisis_especialistas`.
9. `backend/app/scraper/utils/estado_pipeline.py` persiste progreso NLP en `fixtures/pipeline_estado*.json` para reanudar.
10. `backend/app/nlp/nlp_logger.py` escribe logs y resumen final en `backend/logs/nlp/`.

## Comandos

Ejecutar desde `backend/`:

```bash
python -m app.nlp.analizador_pipeline --prueba --limite 5
python -m app.nlp.analizador_pipeline --especialidad Endodoncia --limite 50
python -m app.nlp.analizador_pipeline --todos --modelo gemini --limite 1000
python -m app.nlp.analizador_pipeline --reintentar-errores --limite 100
python -m app.nlp.analizador_pipeline --todos --modelo deepseek --reanalizar-sospecha-fraude --min-opiniones-ia 5
```

`--limite` ahora significa requests reales al proveedor remoto, no candidatos revisados. No se descuenta por skips, fraude local, sin opiniones suficientes, errores previos al request o análisis ya finalizados.

`--forzar-reanalisis` recalcula aunque exista análisis finalizado reciente. Úsalo solo cuando cambie el prompt, el modelo o quieras regenerar resultados válidos.

`--reanalizar-sospecha-fraude` permite regenerar con IA perfiles que antes quedaron cerrados localmente como `sospecha_fraude`. Mantiene como finalizados recientes los estados `completado` y `sin_opiniones`.

`--min-opiniones-ia` define cuántas opiniones descargadas en Mongo se requieren para llamar al modelo. El valor por defecto es `5`.

`--concurrencia` se mantiene por compatibilidad CLI, pero el pipeline NLP ejecuta el corte por requests de forma secuencial para no sobrepasar el límite con trabajos ya programados.

## Contadores operativos

Los contadores viven en `backend/app/nlp/estado_ejecucion.py`:

- `candidatos_revisados`: especialistas inspeccionados por el pipeline.
- `procesados_llm`: casos con análisis exitoso por LLM.
- `procesados_localmente`: casos resueltos sin LLM (`sin_opiniones`, `sospecha_fraude`).
- `skips`: clínicas, análisis recientes o ya finalizados.
- `errores`: fallos persistidos.
- `requests_llm_realizados`: invocaciones reales al proveedor remoto.
- `requests_llm_exitosos`: análisis remotos exitosos.
- `requests_llm_fallidos`: requests que no terminaron en análisis válido.

Ejemplo de resumen final:

```text
Procesados por LLM: 10 | Locales sin LLM: 6 | Skips: 2 | Errores: 0
Requests reales al modelo: 10/10 | exitosos: 10 | fallidos: 0
```

## Muestreo de opiniones

Archivo: `backend/app/nlp/preprocesador.py`

Función principal: `_muestreo_inteligente(opiniones_limpias, total_original)`

Reglas actuales:

- `<= 50`: se envían todas.
- `51 a 120`: 5 no verificadas recientes, 30 recientes, 15 largas; total máximo 50.
- `> 120`: 5 no verificadas recientes, 10 antiguas, 25 recientes, 10 largas; total máximo 50.
- Siempre deduplica por `opinion_id`; si no existe, usa hash estable de `doctor_id`, autor, texto, fecha y rating.
- La salida se ordena por recencia descendente: más recientes primero.
- Si un bloque no tiene suficientes opiniones, se rellena con mejores restantes sin duplicar.

Constantes relevantes:

```python
VENTANA_RECIENTE_DIAS = 180
MAX_OPINIONES_MODELO = 50
```

Para pasar de 30 opiniones recientes a 100 opiniones recientes de los últimos 6 meses, modifica `backend/app/nlp/preprocesador.py`:

1. Cambia `MAX_OPINIONES_MODELO = 50` a `100` o más.
2. En `_muestreo_inteligente`, ajusta las cuotas de `agregar(...)`, por ejemplo `agregar(por_recencia, 100, "recientes")`.
3. Mantén `VENTANA_RECIENTE_DIAS = 180` si quieres “últimos 6 meses”; cámbialo si la ventana cambia.
4. Actualiza las pruebas en `backend/tests/nlp/test_preprocesador.py` para reflejar la nueva distribución.

Metadatos generados:

```json
{
  "total_opiniones_original": 160,
  "total_opiniones_enviadas": 50,
  "estrategia_muestreo": "25_recientes + 10_largas + 5_no_verificadas + 10_antiguas",
  "bloques_muestreo": {
    "recientes": 25,
    "largas": 10,
    "no_verificadas": 5,
    "antiguas": 10,
    "relleno": 0
  },
  "ventana_reciente_dias": 180,
  "hay_muestra_parcial": true,
  "orden_salida": "recencia_descendente_mas_recientes_primero"
}
```

## Payload enviado al modelo

Archivo: `backend/app/nlp/prompt_builder.py`

El prompt de usuario incluye JSON compacto con:

- `perfil`: nombre, especialidad, ciudad, rating global, experiencia, servicios normalizados con precio, consultorios, flags de pacientes e integridad del perfil.
- `metricas_locales`: totales, opiniones enviadas, verificación, recencia, textos cortos, rating promedio y fraude local.
- `metadatos_muestreo`: distribución y estrategia.
- `nota_muestreo`: explicación legible para el modelo.
- `alertas_preprocesamiento`.
- `opiniones`: texto, rating, fecha, antigüedad, servicio consultado, consultorio y verificación.

Ejemplo abreviado:

```json
{
  "perfil": {
    "nombre": "Dra. María de Lourdes Aquino Quinto",
    "especialidad": "Endodoncia",
    "rating_global": 5,
    "servicios": [
      {"nombre": "Tratamiento de Endodoncia", "precio_desde": 3000, "precio_texto": "Desde $3,000", "tiene_precio": true}
    ],
    "consultorios": [{"direccion": "Morelos 2, Iztapalapa", "clinica": null}],
    "atiende_ninos": true,
    "atiende_adultos": true,
    "atiende_adolescentes": false,
    "perfil_detalla_pacientes": true,
    "integridad_perfil": {"servicios_con_precio": 6, "servicios_sin_precio": 4, "total_consultorios": 1}
  },
  "metricas_locales": {
    "total_opiniones_bd": 160,
    "opiniones_enviadas_al_modelo": 50,
    "porcentaje_verificadas": 92.5,
    "porcentaje_ultimos_6_meses": 70.0,
    "sospecha_fraude": false
  },
  "nota_muestreo": "El médico tiene 160 opiniones totales. Se comparten 50 seleccionadas mediante muestreo estratificado: 25 recientes, 10 largas, 5 no verificadas, 10 antiguas. Se incluyen 10 opiniones antiguas para detectar consistencia histórica.",
  "opiniones": [
    {"rating": 5, "fecha_publicacion": "2026-05-18T19:35:24-06:00", "servicio_consultado": "Endodoncia", "es_verificada": true, "texto": "..."}
  ]
}
```

## Prompt y estilo del análisis

Archivo: `backend/app/nlp/prompt_builder.py`

Funciones relevantes:

- `construir_prompt_sistema()`: reglas de evaluación, tono, evidencia y formato JSON.
- `construir_prompt_usuario(datos_preparados)`: payload estructurado.
- `reforzar_resultado_analisis(resultado, datos_preparados)`: añade hallazgos objetivos que no deben depender del proveedor.
- `construir_analisis_minimo(...)`: salida local para menos de 3 opiniones.
- `construir_analisis_fraude_local(...)`: salida local para sospecha de fraude.

Reglas actuales del resumen:

- La primera oración no debe repetir nombre completo ni especialidad.
- Debe empezar con una conclusión analítica.
- Debe cruzar opiniones, servicios, precios y perfil.
- Si los tres flags de pacientes son `false`, debe decir que el perfil no detalla qué tipos de pacientes atiende.
- Si hay precios, se usan como señal de transparencia.
- Si faltan precios, se refleja como debilidad.

## Errores fatales de proveedor

Archivo base: `backend/app/nlp/modelos/base_modelo.py`

Clases y helpers:

- `ErrorProveedorFatal`: cuota/créditos/billing/cuenta deshabilitada.
- `LimiteRequestsLLMAlcanzado`: evita otra llamada si se llegó al límite.
- `es_error_fatal_proveedor(error)`: detecta cuota agotada y tokens/créditos insuficientes.
- `es_rate_limit_recuperable(error)`: permite retry solo si no es fatal.

Los modelos `gemini_modelo.py`, `deepseek_modelo.py` y `groq_modelo.py` llaman `_registrar_request_remoto()` justo antes del request HTTP. Si el proveedor devuelve cuota agotada, el pipeline:

1. marca `fatal_proveedor=true` en estado;
2. persiste resumen y motivo en `fixtures/pipeline_estado*.json`;
3. guarda error en `analisis_especialistas`;
4. imprime resumen final;
5. sale con código `2`.

## Persistencia y reanudación

Archivo: `backend/app/scraper/utils/estado_pipeline.py`

El estado existente del scraper se conserva. Se agrega un bloque compatible:

```json
{
  "nlp": {
    "analisis_finalizados": [355439, 479140],
    "ultimo_resumen": {
      "candidatos_revisados": 18,
      "procesados_llm": 10,
      "procesados_localmente": 6,
      "skips": 2,
      "requests_llm_realizados": 10
    },
    "detenido_por": "limite_requests_llm_alcanzado",
    "fatal_proveedor": false
  }
}
```

Además, `backend/app/nlp/repositorios/analisis_repo.py` considera finalizados recientes los estados:

- `completado`
- `sospecha_fraude`
- `sin_opiniones`

No se recalculan salvo que uses `--forzar-reanalisis`. Si solo quieres reabrir las sospechas locales antiguas, usa `--reanalizar-sospecha-fraude`.

## Ejemplos de salida final

Caso sólido:

```json
{
  "puntuacion_recomendacion": 8.6,
  "resumen": "El patrón de reseñas es consistente y clínicamente útil: predominan menciones verificadas de explicación clara, control del dolor y trato profesional. Publica precios en varios servicios de endodoncia, lo que mejora la transparencia para comparar costos.",
  "puntos_fuertes": [
    "Alta proporción de opiniones verificadas y recientes.",
    "Menciones concretas de claridad del procedimiento y control del dolor.",
    "Servicios principales con precios publicados."
  ],
  "puntos_debiles": [
    "Parte de los servicios no muestra precio, dejando huecos de comparación.",
    "La mayoría de reseñas son positivas, con poca evidencia de manejo de inconformidades."
  ],
  "confiabilidad_opiniones": "alta",
  "justificacion_puntuacion": "La evidencia es reciente, verificada y específica, con penalización menor por huecos de precio."
}
```

Caso incompleto:

```json
{
  "puntuacion_recomendacion": 0.0,
  "resumen": "El perfil no tiene suficientes opiniones para sostener una evaluación útil. Requiere más evidencia verificable antes de asignar recomendación.",
  "puntos_fuertes": [],
  "puntos_debiles": [
    "Información insuficiente para evaluar calidad, consistencia y representatividad de la atención"
  ],
  "confiabilidad_opiniones": "baja",
  "justificacion_puntuacion": "No se asigna puntuación por sin opiniones suficientes."
}
```

Caso con sospecha de fraude:

```json
{
  "puntuacion_recomendacion": 3.0,
  "resumen": "El patrón de reseñas no es confiable para recomendar sin cautela: 30 opiniones activan señales locales de manipulación. La evaluación queda penalizada por 100% de ratings 5.0 y longitudes excesivamente similares.",
  "puntos_fuertes": [
    "100.0% de opiniones declaran algún tipo de verificación."
  ],
  "puntos_debiles": [
    "Sospecha de manipulación: 100% de ratings son 5.0 en 30 opiniones",
    "Sospecha de manipulación: 26/30 opiniones tienen longitud similar",
    "Más de la mitad de las opiniones son muy cortas, lo que reduce profundidad útil."
  ],
  "confiabilidad_opiniones": "sospechosa",
  "justificacion_puntuacion": "La detección local de fraude pesa más que los ratings positivos o la verificación declarada."
}
```

## Pruebas

Suite agregada:

```bash
cd backend
python -m unittest discover -s tests -p 'test_*.py'
```

Cobertura mínima:

- 12 opiniones -> envía 12.
- 80 opiniones -> envía 50 con bloques 30/15/5.
- 160 opiniones -> envía 50 e integra antiguas dentro del máximo.
- Deduplicación por hash estable si falta `opinion_id`.
- Fraude local y sin opiniones no descuentan límite.
- Request LLM exitoso sí descuenta límite.
- Error fatal por cuota registra request remoto.
- Tres flags de pacientes `false` se expresan como falta de detalle.
- Precios concretos se reflejan como transparencia.
- Sin precios y servicios duplicados quedan en puntos débiles.

## Archivos clave para modificar comportamiento

| Necesidad | Archivo | Qué cambiar |
|---|---|---|
| Cambiar máximo de opiniones enviadas | `backend/app/nlp/preprocesador.py` | `MAX_OPINIONES_MODELO` y cuotas en `_muestreo_inteligente` |
| Cambiar ventana de recencia | `backend/app/nlp/preprocesador.py` | `VENTANA_RECIENTE_DIAS` |
| Cambiar criterios de fraude local | `backend/app/nlp/preprocesador.py` | `detectar_sospecha_fraude` |
| Cambiar tono o estructura JSON | `backend/app/nlp/prompt_builder.py` | `construir_prompt_sistema` y JSON esperado |
| Cambiar refuerzo de precios/pacientes | `backend/app/nlp/prompt_builder.py` | `reforzar_resultado_analisis` |
| Cambiar límite operativo | CLI | `--limite N` |
| Forzar reanálisis | CLI | `--forzar-reanalisis` |
| Cambiar detección de cuota fatal | `backend/app/nlp/modelos/base_modelo.py` | `_PATRONES_FATAL_PROVEEDOR` |
| Revisar estado reanudable | `backend/app/scraper/utils/estado_pipeline.py` | bloque `nlp` |
| Revisar idempotencia Mongo | `backend/app/nlp/repositorios/analisis_repo.py` | `analisis_finalizado_reciente` |
