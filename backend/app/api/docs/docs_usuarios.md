# Documentación — Usuarios, Favoritos, Historial y Direcciones

## Autenticación

### POST `/auth/register`
Registra un nuevo usuario.
```json
{ "email": "user@email.com", "password": "123456" }
```

### POST `/auth/login`
Retorna token JWT.
```json
{ "email": "user@email.com", "password": "123456" }
// → { "access_token": "...", "token_type": "bearer" }
```

---

## Perfil

### GET `/usuarios/me`
**Auth: ✅**

Retorna perfil completo con dirección principal y preferencias:
```json
{
  "id": 2, "email": "...", "nombre": "Jose", "apellido": "Esteban",
  "telefono": null, "avatar_url": null, "created_at": "...",
  "direccion_principal": { "id": 1, "alias": "Casa", "ciudad": "Ciudad de México", ... },
  "preferencias": { "especialidades": [], "ciudades": [] }
}
```

### PATCH `/usuarios/me`
**Auth: ✅** — Actualiza `nombre`, `apellido`, `telefono`, `avatar_url`.

---

## Direcciones

### GET `/usuarios/direcciones` — Listar
### POST `/usuarios/direcciones` — Crear

Si `es_principal: true`, desmarca las demás como no principales.

```json
{
  "alias": "Casa", "calle": "Av. Universidad 3000",
  "municipio_alcaldia": "Coyoacán",
  "ciudad": "Ciudad de México", "ciudad_slug": "ciudad-de-mexico",
  "estado": "Ciudad de México", "pais": "México",
  "codigo_postal": "04360", "es_principal": true
}
```

### PATCH `/usuarios/direcciones/{id}` — Actualizar parcialmente
### DELETE `/usuarios/direcciones/{id}` — Eliminar

---

## Favoritos

### POST `/usuarios/favoritos`
**Auth: ✅**

Acepta ObjectId o doctoralia_id:
```json
{ "medico_id": "{id_mongo}" }
{ "doctoralia_id": 479140 }
```

Retorna 409 si ya está en favoritos.

### GET `/usuarios/favoritos`
**Auth: ✅** — Devuelve datos completos de cada especialista (card + análisis IA).

### DELETE `/usuarios/favoritos/{medico_id}`
**Auth: ✅** — Elimina por ObjectId del especialista.

---

## Historial

### GET `/usuarios/historial?page=1&limit=20`
**Auth: ✅** — Paginado.

### POST `/usuarios/historial`
**Auth: ✅**
```json
{
  "especialidad": "psicologo",
  "ubicacion": "ciudad-de-mexico",
  "consulta_texto": "Tengo ansiedad",
  "filtros": { "especialidad": "psicologo", "solo_analizados": true },
  "origen": "chat",
  "total_resultados": 8
}
```
`origen`: `tradicional` | `chat` | `home`

### DELETE `/usuarios/historial`
**Auth: ✅** — Elimina todo el historial del usuario.
