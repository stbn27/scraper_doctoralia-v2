# Pipeline NLP — Análisis de opiniones médicas

## Descripción general

El pipeline NLP es un sistema CLI de procesamiento masivo que analiza las opiniones de ~52,000 especialistas médicos usando múltiples modelos de IA. El flujo completo es:

1. **Consulta MongoDB** — obtiene especialistas y sus opiniones desde las colecciones `especialistas` y `opiniones`.
2. **Preprocesamiento local** — limpia textos, detecta sospechas de fraude, calcula métricas y filtra opiniones irrelevantes.
3. **Análisis con IA** — envía los datos preprocesados al modelo de IA configurado y obtiene un análisis estructurado en JSON.
4. **Persistencia** — guarda el resultado en la colección `analisis_especialistas` de MongoDB.

Cada ejecución genera un archivo de log detallado en `backend/logs/nlp/` con las respuestas crudas del modelo para auditoría.

---

## Requisitos previos

### Variables de entorno (`.env`)

El archivo `.env` debe estar en la **raíz del proyecto** (donde está `docker-compose.yml`). Variables necesarias:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `MONGO_URL` | URL de conexión a MongoDB | `mongodb://localhost:27017` |
| `MONGO_DB` | Nombre de la base de datos | `medicos_db` |
| `MODELO_ACTIVO` | Modelo por defecto | `groq` |
| `GROQ_API_KEY` | API key de Groq | `gsk_xxx...` |
| `GROQ_MODEL` | Modelo de Groq | `llama-3.3-70b-versatile` |
| `DEEPSEEK_API_KEY` | API key de DeepSeek | `sk-xxx...` |
| `DEEPSEEK_MODEL_NLP` | Modelo DeepSeek para NLP | `deepseek-chat` |
| `DEEPSEEK_BASE_URL_NLP` | URL base de DeepSeek | `https://api.deepseek.com` |
| `GEMINI_API_KEY` | API key de Gemini | `AIza...` |
| `GEMINI_MODEL` | Modelo de Gemini | `gemini-1.5-flash` |
| `MINIMAX_API_KEY` | API key de MiniMax | `xxx` |
| `MINIMAX_GROUP_ID` | Group ID de MiniMax | `xxx` |
| `MINIMAX_MODEL` | Modelo de MiniMax | `abab6.5s-chat` |
| `OLLAMA_BASE_URL` | URL de Ollama local | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modelo de Ollama | `llama3.1:8b` |

### Dependencias (`requirements.txt`)

```bash
cd backend
pip install -r requirements.txt
```

Las dependencias específicas para el pipeline NLP son:

```
groq>=0.9.0
openai>=1.30.0
google-generativeai>=0.5.0
```

### MongoDB activo

El contenedor de MongoDB debe estar corriendo:

```bash
docker compose up -d mongodb
```

---

## Comandos de uso

> **IMPORTANTE**: Todos los comandos se ejecutan desde el directorio `backend/`.

### Modo prueba (siempre ejecutar primero)

Procesa un número reducido de médicos para verificar que todo funciona correctamente antes de ejecutar el procesamiento masivo.

```bash
cd backend

# Prueba con 5 médicos (modelo por defecto del .env)
python -m app.nlp.analizador_pipeline --prueba --limite 5

# Prueba con modelo específico
python -m app.nlp.analizador_pipeline --prueba --limite 5 --modelo deepseek
```

### Por especialidad

Filtra y procesa solo los especialistas de una especialidad concreta.

```bash
cd backend

# Solo endodoncistas
python -m app.nlp.analizador_pipeline --especialidad Endodoncia

# Solo ortodoncistas, máximo 50
python -m app.nlp.analizador_pipeline --especialidad Ortodoncia --limite 50
```

### Procesamiento masivo

Procesa **todos** los especialistas en la base de datos.

```bash
cd backend

# Todos los especialistas con el modelo por defecto
python -m app.nlp.analizador_pipeline --todos

# Todos con DeepSeek y concurrencia de 8
python -m app.nlp.analizador_pipeline --todos --modelo deepseek --concurrencia 8
```

### Reintentar errores

Reprocesa exclusivamente los médicos que quedaron en estado `error` en ejecuciones anteriores.

```bash
cd backend

python -m app.nlp.analizador_pipeline --reintentar-errores

# Con límite
python -m app.nlp.analizador_pipeline --reintentar-errores --limite 100
```

### Particionamiento para múltiples terminales

Para procesamiento masivo con ~52,000 médicos, se recomienda dividir la carga en 4 terminales usando `--skip` y `--limite` combinados con MongoDB queries manuales o dividiendo por especialidades:

```bash
# Terminal 1 — Groq (primeros 13,000)
cd backend
python -m app.nlp.analizador_pipeline --todos --modelo groq --limite 13000

# Terminal 2 — DeepSeek (siguiente bloque por especialidad)
cd backend
python -m app.nlp.analizador_pipeline --especialidad Ortodoncia --modelo deepseek

# Terminal 3 — Gemini (otra especialidad)
cd backend
python -m app.nlp.analizador_pipeline --especialidad Endodoncia --modelo gemini

# Terminal 4 — Reintentar errores acumulados
cd backend
python -m app.nlp.analizador_pipeline --reintentar-errores --modelo groq
```

---

## Modelos disponibles

| Modelo               | Argumento `--modelo` | Velocidad             | Costo           | Límite              |
| -------------------- | -------------------- | --------------------- | --------------- | ------------------- |
| Groq (Llama 3.3 70B) | `groq`               | ⚡ Muy rápida (~0.5s) | Gratuito        | ~14,400 req/día     |
| DeepSeek             | `deepseek`           | 🔵 Rápida (~1.5s)     | ~$0.14/M tokens | Sin límite práctico |
| Gemini 1.5 Flash     | `gemini`             | 🔵 Rápida (~1s)       | Gratuito        | 1,500 req/día       |
| MiniMax              | `minimax`            | 🟡 Media (~2s)        | Gratuito        | 1,500 req/5 horas   |
| Ollama (local)       | `ollama`             | 🟠 Lenta (variable)   | Gratuito        | Sin límite          |


**Recomendación para procesamiento masivo**: Iniciar con **Groq** (gratuito y rápido) para el grueso del trabajo. Cambiar a **DeepSeek** para volúmenes grandes donde Groq alcance el rate limit. Usar **Gemini** como respaldo para reintentos.

---

## Parámetros de línea de comandos

| Argumento              | Tipo    | Default              | Descripción                                           |
| ---------------------- | ------- | -------------------- | ----------------------------------------------------- |
| `--prueba`             | flag    | `False`              | Activa modo prueba (limita automáticamente)           |
| `--limite`             | `int`   | `10`                 | Máximo de médicos a procesar                          |
| `--especialidad`       | `str`   | `None`               | Filtra por nombre de especialidad (case-insensitive)  |
| `--todos`              | flag    | `False`              | Procesa todos los especialistas sin límite            |
| `--reintentar-errores` | flag    | `False`              | Solo reprocesa los que tienen estado=error            |
| `--modelo`             | `str`   | `.env MODELO_ACTIVO` | Sobreescribe el modelo activo del `.env`              |
| `--concurrencia`       | `int`   | `5`                  | Máximo de llamadas paralelas simultáneas a la IA      |
| `--pausa-entre-lotes`  | `float` | `2.0`                | Segundos de espera entre lotes (respetar rate limits) |


---

## Archivos de log

### Ubicación

Los archivos de log se generan automáticamente en:

```
backend/logs/nlp/
```

El directorio se crea automáticamente si no existe.

### Formato del nombre de archivo

```
nlp_{ddMMyy}_{HHMMSS}_{modelo}_{modo}_{particion}.log
```

**Ejemplos:**
- `nlp_010626_100100_groq_prueba_completo.log` — Prueba con Groq
- `nlp_010626_143022_deepseek_masivo_completo.log` — Ejecución masiva con DeepSeek
- `nlp_020626_080000_gemini_especialidad_completo.log` — Ejecución por especialidad con Gemini

### Formato de cada línea

```
[2026-06-01 10:01:00] [INFO   ] Pipeline iniciado correctamente
[2026-06-01 10:01:01] [WARNING] Dr. Pérez | id=123 | sospecha_fraude detectada
[2026-06-01 10:01:02] [ERROR  ] Dr. López | id=456 | Error en modelo: rate limit
[2026-06-01 10:01:03] [SUCCESS] Dr. García | id=789 | score=8.5
```

### Ejemplo de respuesta cruda en el log

El log registra la respuesta completa del modelo para cada médico procesado:

```
══════════════════════════════════════════════════════
RESPUESTA MODELO — Dr. Alejandro Pérez Islas | id=355439
Estado: ÉXITO | Longitud: 847 chars
──────────────────────────────────────────────────────
{
  "puntuacion_recomendacion": 8.5,
  "confiabilidad_opiniones": "media",
  "resumen_general": "Especialista con buena reputación...",
  "fortalezas": ["Trato amable", "Puntualidad"],
  "areas_mejora": ["Tiempos de espera"],
  "alertas": [],
  "analisis_fraude": "Sin indicios de manipulación"
}
══════════════════════════════════════════════════════
```

### Ejemplo de resumen final

Al terminar cada ejecución, el log incluye un resumen consolidado:

```
════════════════════════════════════════════════════════════
  RESUMEN DE EJECUCIÓN — Pipeline NLP
────────────────────────────────────────────────────────────
  Modelo:          groq (llama-3.3-70b-versatile)
  Modo:            prueba | Límite: 10 médicos
  Total médicos:   10
────────────────────────────────────────────────────────────
  Completados:     7
  Sin opiniones:   2
  Errores:         0
  Skips:           1
────────────────────────────────────────────────────────────
  Tasa de éxito:   70.0%
  Tiempo total:    0m 04s
  Promedio:        0.4s/médico
════════════════════════════════════════════════════════════
```

---

## Colección MongoDB: `analisis_especialistas`

### Estructura del documento

```json
{
  "_id": "ObjectId(...)",
  "doctor_id": 355439,
  "doctoralia_id": 355439,
  "nombre_especialista": "Dr. Alejandro Pérez Islas",
  "especialidad": "Endodoncia",
  "estado": "completado",
  "fecha_analisis": "2026-06-01T10:00:00Z",
  "modelo_usado": "groq",
  "version_prompt": "v1",
  "metricas_locales": {
    "total_opiniones": 45,
    "opiniones_validas": 38,
    "sospecha_fraude": false,
    "puntuacion_promedio": 4.7
  },
  "alertas_preprocesamiento": [],
  "resultado_ia": {
    "puntuacion_recomendacion": 8.5,
    "confiabilidad_opiniones": "media",
    "resumen_general": "...",
    "fortalezas": ["..."],
    "areas_mejora": ["..."],
    "alertas": [],
    "analisis_fraude": "..."
  },
  "error_detalle": null
}
```

### Estados posibles

| Estado | Significado |
|---|---|
| `completado` | Análisis exitoso con resultado de IA |
| `sospecha_fraude` | Análisis completado pero con indicios de manipulación de opiniones |
| `sin_opiniones` | El médico no tiene suficientes opiniones; se generó un análisis mínimo local |
| `error` | Fallo en el procesamiento (modelo no respondió, JSON inválido tras reintento, etc.) |

### Consultas útiles en MongoDB

```javascript
// Total de análisis por estado
db.analisis_especialistas.aggregate([
  { $group: { _id: "$estado", total: { $sum: 1 } } }
])

// Médicos con score mayor a 8
db.analisis_especialistas.find({
  "estado": "completado",
  "resultado_ia.puntuacion_recomendacion": { $gte: 8 }
}).count()

// Últimos 10 análisis con errores
db.analisis_especialistas.find({
  "estado": "error"
}).sort({ "fecha_analisis": -1 }).limit(10)

// Médicos con sospecha de fraude
db.analisis_especialistas.find({
  "estado": "sospecha_fraude"
}).sort({ "fecha_analisis": -1 })
```

---

## Guía de escalado masivo (52,000 médicos)

### Estrategia de particionamiento por 4 terminales

Para procesar ~52,000 médicos de forma eficiente, se recomienda distribuir la carga en 4 terminales simultáneas:

| Terminal | Modelo   | Estrategia                  | Comando                                       |
| -------- | -------- | --------------------------- | --------------------------------------------- |
| T1       | Groq     | Primeros 13,000             | `--todos --modelo groq --limite 13000`        |
| T2       | DeepSeek | Por especialidad (bloque 1) | `--especialidad Ortodoncia --modelo deepseek` |
| T3       | Gemini   | Por especialidad (bloque 2) | `--especialidad Endodoncia --modelo gemini`   |
| T4       | Groq     | Reintentar errores          | `--reintentar-errores --modelo groq`          |


### Modelo recomendado por terminal

- **Groq** — Para el grueso del trabajo. Muy rápido (~0.5s/médico) y gratuito. Limitado a ~14,400 req/día.
- **DeepSeek** — Para volumen alto sin preocuparse por rate limits. Costo muy bajo (~$0.14 por millón de tokens).
- **Gemini** — Para respaldo y reintentos. 1,500 req/día gratuitas.
- **MiniMax** — Reserva para situaciones donde los otros modelos estén saturados.

### Tiempo estimado

| Escenario                     | Modelo   | Concurrencia | Tiempo estimado |
| ----------------------------- | -------- | ------------ | --------------- |
| 13,000 médicos                | Groq     | 5            | ~1.8 horas      |
| 13,000 médicos                | DeepSeek | 8            | ~2.7 horas      |
| 13,000 médicos                | Gemini   | 5            | ~3.6 horas      |
| 52,000 médicos (4 terminales) | Mixto    | 5 cada una   | ~4-5 horas      |


> **Nota**: El pipeline detecta automáticamente análisis recientes (< 30 días) y los omite (estado `skip`), por lo que re-ejecutar es seguro e idempotente.

---

## Solución de problemas frecuentes

### JSON inválido

**Síntoma**: El log muestra `JSON inválido, reintentando...` seguido de `Fallo en reintento`.

**Causa**: El modelo retorna una respuesta que no contiene JSON válido o el JSON está truncado.

**Solución**:
1. Revisar el archivo de log en `backend/logs/nlp/` para ver la respuesta cruda completa.
2. Si el JSON está truncado, verificar que `max_tokens` sea suficiente (actualmente 1500).
3. Si el problema persiste con un modelo específico, cambiar a otro modelo con `--modelo`.

### Rate limit

**Síntoma**: El log muestra `Rate limit alcanzado — esperando 60 segundos...`.

**Causa**: Se excedió el límite de peticiones del modelo.

**Solución**:
1. Reducir la concurrencia: `--concurrencia 3`
2. Aumentar la pausa entre lotes: `--pausa-entre-lotes 5.0`
3. Cambiar a un modelo sin rate limit estricto: `--modelo deepseek`
4. Esperar y reintentar con `--reintentar-errores`

### Modelo no disponible

**Síntoma**: Error `model_decommissioned` o `model not found`.

**Causa**: El modelo configurado en el `.env` fue dado de baja por el proveedor.

**Solución**:
1. Consultar la documentación del proveedor para ver los modelos disponibles.
2. Actualizar la variable correspondiente en el `.env` (ejemplo: `GROQ_MODEL=llama-3.3-70b-versatile`).
3. Alternativamente, usar `--modelo` para sobreescribir temporalmente.

### Error de conexión a MongoDB

**Síntoma**: `ServerSelectionTimeoutError: localhost:27017: Connection refused`.

**Causa**: El contenedor de MongoDB no está corriendo.

**Solución**:
```bash
# Levantar solo MongoDB
docker compose up -d mongodb

# Verificar que está activo
docker ps | grep mongo
```

### El `.env` no se carga

**Síntoma**: Se usan valores por defecto en lugar de los configurados en el `.env`.

**Causa**: El archivo `.env` no está en el directorio esperado.

**Solución**:
1. Asegurarse de que el `.env` está en la raíz del proyecto (junto a `docker-compose.yml`).
2. Ejecutar siempre desde el directorio `backend/`:
   ```bash
   cd backend
   python -m app.nlp.analizador_pipeline --prueba --limite 5
   ```
