# API MedRec v2 — Documentación

Plataforma de búsqueda y recomendación de especialistas médicos con análisis IA.

**Base URL:** `http://localhost:8000`

---

## Índice de Módulos

| Módulo | Ruta base | Auth | Archivo de docs |
|--------|-----------|------|-----------------|
| Autenticación | `/auth` | ❌ | [docs_usuarios.md](docs_usuarios.md) |
| Usuarios | `/usuarios` | ✅ JWT | [docs_usuarios.md](docs_usuarios.md) |
| Especialistas | `/especialistas` | ❌ | [docs_especialistas.md](docs_especialistas.md) |
| Catálogos | `/catalogos` | ❌ | [docs_catalogos.md](docs_catalogos.md) |
| Chatbot | `/chat` | ❌ / ✅ | [docs_chat.md](docs_chat.md) |
| Recomendador | `/recomendar` | ❌ | [docs_chat.md](docs_chat.md) |

---

## Stack Tecnológico

- **FastAPI** — Framework async para Python
- **MongoDB** (Motor) — `especialistas`, `opiniones`, `analisis_especialistas`, `catalogos`
- **MySQL** — `usuarios`, `favoritos`, `historial_busquedas`, `usuarios_direcciones`
- **JWT** — Autenticación stateless con `python-jose`
- **Groq / Gemini** — LLMs para chatbot de interpretación médica

---

## Convenciones

### Autenticación
Todos los endpoints protegidos requieren header:
```
Authorization: Bearer <token>
```

### Paginación
Los endpoints paginados devuelven:
```json
{
  "total": 150,
  "page": 1,
  "limit": 12,
  "pages": 13,
  "has_next": true,
  "has_prev": false
}
```

### Errores estándar
```json
{ "detail": "Mensaje descriptivo del error" }
```

| Código | Significado |
|--------|-------------|
| 400 | Parámetros inválidos |
| 401 | Token ausente o expirado |
| 404 | Recurso no encontrado |
| 409 | Conflicto (duplicado) |
| 422 | Error de validación Pydantic |
| 503 | Servicio LLM no disponible |

---

## Health Check
```
GET /health
```
Respuesta:
```json
{ "api": "ok", "mysql": "ok", "mongodb": "ok" }
```
