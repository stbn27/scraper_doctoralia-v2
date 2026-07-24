# Documentación — Catálogos

Todos los endpoints son públicos. Los datos provienen de `catalogos` en MongoDB.

---

## GET `/catalogos/especialidades`

| Param | Tipo | Descripción |
|-------|------|-------------|
| `q` | string | Búsqueda parcial en el slug |
| `limit` | int | Máximo resultados (default 20) |

Retorna especialidades agrupadas únicas con total de pares ciudad disponibles.
Si `especialidad_nombre` es null en la BD, se genera desde el slug.

```
GET /catalogos/especialidades?q=endo → [{ "nombre": "Endodoncia", "slug": "endodoncia", "total_pares": 12 }]
```

---

## GET `/catalogos/ciudades`

| Param | Tipo | Descripción |
|-------|------|-------------|
| `q` | string | Búsqueda parcial en el slug de ciudad |
| `especialidad` | string | Filtrar por especialidad disponible |
| `limit` | int | Máximo resultados (default 20) |

El nombre de ciudad se limpia del sufijo de especialidad que adjunta Doctoralia.

```
GET /catalogos/ciudades?especialidad=endodoncia
GET /catalogos/ciudades?q=ciu
GET /catalogos/ciudades?especialidad=endodoncia&q=mex
```

---

## GET `/catalogos/pares`

| Param | Tipo | Descripción |
|-------|------|-------------|
| `especialidad` | string | Slug de especialidad |
| `ciudad` | string | Slug de ciudad |
| `modalidad` | string | `presencial` o `online` |
| `page` | int | Página actual (default 1) |
| `limit` | int | Por página (default 50) |

Retorna paginado completo de pares especialidad-ciudad disponibles en Doctoralia.
