# Documentación — Especialistas

## GET `/especialistas/`
**Auth:** No requerida | **Fuente:** MongoDB (sin scraping)

Búsqueda avanzada con filtros múltiples y paginación. Enriquece cada resultado con análisis IA.

### Query Params

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `especialidad` | string | — | Nombre o slug de especialidad |
| `ciudad` | string | — | Nombre o slug de ciudad |
| `q` | string | — | Búsqueda textual por nombre |
| `page` | int | 1 | Página actual |
| `limit` | int | 12 | Máx. 50 |
| `orden` | string | `opiniones_desc` | Ver opciones abajo |
| `solo_con_opiniones` | bool | false | Solo con `total_opiniones > 0` |
| `solo_analizados` | bool | false | Solo con análisis IA |
| `estado_analisis` | string | — | `completado\|sin_opiniones\|sospecha_fraude\|error` |
| `confiabilidad` | string | — | `alta\|media\|baja\|sospechosa` |
| `sospecha_fraude` | bool | — | Filtrar por sospecha de fraude IA |
| `atiende_ninos` | bool | — | Filtra `pacientes.atiende_ninos = true` |
| `atiende_adultos` | bool | — | Filtra `pacientes.atiende_adultos = true` |
| `atiende_adolescentes` | bool | — | Filtra `pacientes.atiende_adolescentes = true` |
| `rating_min` | float | — | Rating mínimo global |
| `rating_max` | float | — | Rating máximo global |
| `puntuacion_min` | float | — | Puntuación IA mínima |
| `puntuacion_max` | float | — | Puntuación IA máxima |
| `solo_con_foto` | bool | — | Requiere foto de perfil |
| `solo_con_cedula` | bool | — | Requiere cédula profesional |
| `solo_con_consultorio` | bool | — | Requiere al menos un consultorio |
| `solo_con_precio` | bool | — | Requiere al menos un precio |
| `precio_min` | int | — | Precio mínimo de servicios |
| `precio_max` | int | — | Precio máximo de servicios |
| `servicio` | string | — | Búsqueda en `servicios.nombre` |
| `alcaldia_o_municipio` | string | — | Búsqueda en dirección de consultorios |

### Opciones de `orden`

| Valor | Descripción |
|-------|-------------|
| `puntuacion_desc` | Mayor puntuación IA primero |
| `puntuacion_asc` | Menor puntuación IA primero |
| `opiniones_desc` | Más opiniones primero |
| `opiniones_asc` | Menos opiniones primero |
| `rating_desc` | Mayor rating global primero |
| `rating_asc` | Menor rating global primero |
| `nombre_asc` | Alfabético A→Z |
| `nombre_desc` | Alfabético Z→A |
| `recencia_analisis_desc` | Análisis más reciente primero |

> **Nota:** Para `puntuacion_*` y `recencia_analisis_desc`, el ordenamiento se hace en memoria sobre los resultados de la página. Los especialistas sin análisis van al final.

### Comportamiento sin filtros
```json
{
  "total": 0,
  "page": 1,
  "limit": 12,
  "pages": 0,
  "results": [],
  "message": "Agrega al menos un filtro para buscar especialistas."
}
```

---

## GET `/especialistas/{id}`
**Auth:** No requerida

Retorna detalle completo del especialista por ObjectId de MongoDB, incluyendo análisis IA completo.

---

## GET `/especialistas/doctoralia/{doctoralia_id}`
**Auth:** No requerida

Retorna detalle completo por ID numérico de Doctoralia.

---

## GET `/especialistas/{id}/opiniones`

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `page` | int | 1 | Página |
| `limit` | int | 20 | Máx. 100 |
| `orden` | string | `reciente` | `reciente\|antigua\|rating_desc\|rating_asc` |
| `rating_min` | float | — | Rating mínimo |
| `rating_max` | float | — | Rating máximo |
| `solo_verificadas` | bool | — | Solo opiniones verificadas |
| `servicio` | string | — | Filtrar por servicio consultado |

`es_verificada = true` si `tipo_verificacion` contiene "verific" (case-insensitive).

---

## GET `/especialistas/buscar` _(Legacy)_

Búsqueda con posibilidad de scraping. Conservado para compatibilidad. Parámetros obligatorios: `especialidad`, `ciudad`.

---

## Ejemplos

```http
GET /especialistas/?especialidad=endodoncia&ciudad=ciudad-de-mexico&solo_analizados=true&orden=puntuacion_desc
GET /especialistas/?especialidad=endodoncia&atiende_ninos=true&solo_con_opiniones=true
GET /especialistas/{id_mongo}/opiniones?page=1&limit=20&orden=rating_desc&solo_verificadas=true
```
