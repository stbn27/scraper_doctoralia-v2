# Backend: API, modelos, servicios y datos

Esta documentación describe los archivos Python de `backend/app` que exponen la API, definen modelos, conectan bases de datos y coordinan lógica de negocio. Los ejemplos muestran entradas y salidas representativas; los IDs, fechas y tokens son ilustrativos.

## `app/main.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `root()` | No recibe parámetros. | `dict` con estado básico de la API. | Entrada: `GET /` -> salida: `{"status": "ok", "message": "API corriendo"}` |
| `health()` | No recibe parámetros. Internamente prueba MySQL y MongoDB. | `dict` con estado de API, MySQL y MongoDB. | Salida ok: `{"api": "ok", "mysql": "ok", "mongodb": "ok"}`. Si falla una BD, el valor contiene el mensaje de excepción. |

## `app/security.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `hash_password(password)` | `password: str`. | Hash bcrypt como `str`. | Entrada: `"secret123"` -> salida: `"$2b$12$..."` |
| `verify_password(plain, hashed)` | Contraseña plana y hash guardado. | `bool`. | Entrada: `"secret123"`, `"$2b$..."` -> salida: `True` si coincide. |
| `create_access_token(data)` | `dict` con claims JWT. Agrega `exp`. | Token JWT firmado. | Entrada: `{"sub": "7"}` -> salida: `"eyJhbGciOi..."` |
| `get_current_user(token=Depends(...))` | Token bearer desde FastAPI. | `{"id": int}` si el token es válido. | Entrada: JWT con `sub="7"` -> salida: `{"id": 7}`. Si falla, lanza `HTTPException 401`. |

## `app/api/usuarios.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `register(data)` | `UsuarioCreate` con `email` y `password`. | `UsuarioResponse`. | Entrada: `{"email": "ana@test.com", "password": "abc12345"}` -> salida: `{"id": 1, "email": "ana@test.com", "created_at": "..."}`. Si el email existe, `409`. |
| `login(data)` | `UsuarioLogin` con `email` y `password`. | `TokenResponse`. | Entrada: `{"email": "ana@test.com", "password": "abc12345"}` -> salida: `{"access_token": "...", "token_type": "bearer"}`. Si no coincide, `401`. |
| `get_me(current_user)` | Usuario autenticado desde `get_current_user`. | Datos del usuario desde MySQL. | Entrada: token de usuario `1` -> salida: `{"id": 1, "email": "ana@test.com", "created_at": "..."}`. |
| `agregar_favorito(data, current_user)` | `Favorito` y usuario autenticado. | Mensaje de confirmación. | Entrada: `{"medico_id": "665..."}` -> salida: `{"mensaje": "Agregado a favoritos"}`. Si duplica, `409`. |
| `listar_favoritos(current_user)` | Usuario autenticado. | Lista de favoritos ordenada por fecha. | Salida: `[{"id": 3, "medico_id": "665...", "guardado_en": "..."}]` |
| `eliminar_favorito(medico_id, current_user)` | `medico_id: str` y usuario autenticado. | Respuesta vacía con HTTP `204`. | Entrada: `DELETE /usuarios/favoritos/665...` -> salida: sin cuerpo. |
| `guardar_historial(especialidad, ubicacion, current_user)` | Query params `especialidad`, `ubicacion` y usuario autenticado. | Mensaje de confirmación. | Entrada: `especialidad=endodoncia&ubicacion=cdmx` -> salida: `{"mensaje": "Búsqueda guardada"}` |
| `listar_historial(current_user)` | Usuario autenticado. | Últimas 20 búsquedas. | Salida: `[{"id": 1, "especialidad": "endodoncia", "ubicacion": "cdmx", "fecha": "..."}]` |

## `app/api/especialistas.py`

| Función / clase | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `CatalogoCargaRequest` | Modelo con `especialidad: str` y `ciudad: str`. | Payload validado para cargar catálogo. | Entrada: `{"especialidad": "Endodoncia", "ciudad": "Ciudad de México"}` |
| `_serializar_doc(doc)` | Documento Mongo como `dict`. | Mismo dict con `_id` convertido a `str`. | Entrada: `{"_id": ObjectId(...)}` -> salida: `{"_id": "665..."}` |
| `buscar_especialistas(...)` | Query: `especialidad`, `ciudad`, `limite`, `forzar_scraping`. | `dict` con fuente, total y especialistas. | Entrada: `/especialistas/buscar?especialidad=endodoncia&ciudad=ciudad-de-mexico&limite=2` -> salida: `{"fuente": "mongo", "total": 2, "especialistas": [...]}` |
| `listar_especialistas(...)` | Filtros opcionales `especialidad`, `ciudad`, `limite`. | Lista de `EspecialistaResponse`. | Entrada: `/especialistas/?ciudad=méxico` -> salida: `[{"_id": "665...", "nombre": "..."}]` |
| `obtener_especialista(especialista_id)` | ID Mongo como `str`. | Un especialista serializado. | Entrada: `"665..."` -> salida: `{"_id": "665...", "nombre": "Dra. Ana"}`. Si no existe, `404`. |
| `eliminar_especialista(especialista_id)` | ID Mongo como `str`. | `{"eliminado": True}`. | Entrada: `"665..."` -> salida: `{"eliminado": true}`. Si no existe, `404`. |
| `cargar_catalogo(payload)` | `CatalogoCargaRequest`. | Resultado de carga desde fixture. | Entrada: `{"especialidad": "Endodoncia", "ciudad": "CDMX"}` -> salida: `{"insertado": true, "url": "https://..."}` |
| `actualizar_catalogo()` | No recibe parámetros. | Resumen de catálogo scrapeado. | Salida: `{"insertados": 10, "actualizados": 5, "procesados": 15}` |
| `obtener_opiniones(especialista_id, limite, actualizar)` | ID Mongo, límite y flag de actualización. | `OpinionesResponse`. | Entrada: `/665.../opiniones?limite=10` -> salida: `{"especialista": {...}, "opiniones_info": {...}, "opiniones": [...]}` |

## `app/models`

Estos modelos no tienen métodos propios; funcionan como contratos Pydantic de entrada y salida.

| Modelo | Campos principales | Ejemplo |
| --- | --- | --- |
| `UsuarioCreate` | `email`, `password`. | `{"email": "ana@test.com", "password": "abc12345"}` |
| `UsuarioResponse` | `id`, `email`, `created_at`. | `{"id": 1, "email": "ana@test.com", "created_at": "2026-05-25T10:00:00"}` |
| `UsuarioLogin` | `email`, `password`. | `{"email": "ana@test.com", "password": "abc12345"}` |
| `TokenResponse` | `access_token`, `token_type`. | `{"access_token": "...", "token_type": "bearer"}` |
| `Favorito` | `medico_id`. | `{"medico_id": "665..."}` |
| `FavoritoResponse` | `id`, `medico_id`, `guardado_en`. | `{"id": 1, "medico_id": "665...", "guardado_en": "..."}` |
| `ConsultorioModel` | `direccion`, `clinica`. | `{"direccion": "Av. X 123", "clinica": "Clínica Centro"}` |
| `ServicioModel` | `nombre`, `precio_desde`, `precio_texto`. | `{"nombre": "Endodoncia", "precio_desde": 900, "precio_texto": "Desde $900"}` |
| `PacientesModel` | `atiende_ninos`, `atiende_adultos`, `atiende_adolescentes`. | `{"atiende_ninos": false, "atiende_adultos": true, "atiende_adolescentes": true}` |
| `ScrapingMetaModel` | `url_origen`, `fecha_consulta`, totales. | `{"url_origen": "https://...", "fecha_consulta": "...", "total_servicios": 4, "total_consultorios": 1}` |
| `EspecialistaModel` | Datos médicos, servicios, consultorios y metadata. | `{"doctoralia_id": 123, "nombre": "Dra. Ana", "especialidad": "Endodoncia", "ciudad": "CDMX"}` |
| `EspecialistaResponse` | Extiende `EspecialistaModel` con alias `_id`. | `{"_id": "665...", "nombre": "Dra. Ana", ...}` |
| `OpinionModel` | `opinion_id`, `doctor_id`, `autor`, `rating`, `texto`, fechas y metadata básica. | `{"opinion_id": 10, "doctor_id": 123, "rating": 5.0, "texto": "Excelente"}` |
| `OpinionesResponse` | `especialista`, `opiniones_info`, `opiniones`. | `{"especialista": {...}, "opiniones_info": {...}, "opiniones": [...]}` |

## `app/db/mysql.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `get_mysql_pool()` | No recibe parámetros. Lee variables `MYSQL_*`. | Singleton `MySQLConnectionPool`. | Salida: pool con `pool_name="medicos_pool"` y `pool_size=5`. |
| `get_mysql_conn()` | No recibe parámetros. | Conexión MySQL desde el pool. | Uso: `conn = get_mysql_conn(); cursor = conn.cursor(dictionary=True)` |

## `app/db/mongo.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `get_mongo_client()` | No recibe parámetros. Lee `MONGO_URL`. | Singleton `MongoClient` síncrono. | Salida: cliente conectado a `mongodb://mongodb:27017` por defecto. |
| `get_mongo_db()` | No recibe parámetros. Lee `MONGO_DB`. | Base Mongo síncrona. | Salida: `client["medicos_db"]`. |
| `get_mongo_async_client()` | No recibe parámetros. Lee `MONGO_URL`. | Singleton `AsyncIOMotorClient`. | Salida: cliente Motor para repositorios async. |
| `get_mongo_async_db()` | No recibe parámetros. Lee `MONGO_DB`. | Base Mongo async. | Salida: `async_client["medicos_db"]`. |

## `app/db/repositorios/especialistas_repo.py`

Documentación ampliada: [backend-especialistas-repo.md](/home/esteban/Documentos/python/pt/v1/docs/backend-especialistas-repo.md).

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `_normalizar_regex(valor)` | Texto de filtro. | Regex Mongo case-insensitive escapado. | Entrada: `"Endodoncia"` -> salida: `{"$regex": "Endodoncia", "$options": "i"}` |
| `_obtener_coleccion()` | No recibe parámetros. | Colección async `especialistas`. | Salida: `db["especialistas"]`. |
| `_asegurar_indices()` | No recibe parámetros. | `None`; crea índices una vez. | Crea índice único sparse en `doctoralia_id` e índice por `especialidad, ciudad`. |
| `obtener_por_especialidad_y_ciudad(especialidad, ciudad)` | Dos textos. | Lista de documentos. | Entrada: `"Endodoncia"`, `"Ciudad de México"` -> salida: `[{...}, {...}]` |
| `insertar_especialista(doc)` | Documento de especialista. | ID Mongo como `str`. | Entrada: `{"doctoralia_id": 123, "nombre": "Dra. Ana"}` -> salida: `"665..."` |
| `actualizar_especialista(doctoralia_id, doc)` | ID Doctoralia y documento. | `bool` si modificó. | Entrada: `123`, `{"nombre": "Dra. Ana"}` -> salida: `True` |
| `buscar_por_doctoralia_id(doctoralia_id)` | ID Doctoralia. | Documento o `None`. | Entrada: `123` -> salida: `{"doctoralia_id": 123, ...}` |
| `buscar_por_id(id)` | ObjectId en texto. | Documento o `None`. | Entrada: `"665..."` -> salida: `{"_id": ObjectId(...), ...}` |
| `eliminar_especialista(id)` | ObjectId en texto. | `bool`. | Entrada: `"665..."` -> salida: `True` |
| `listar_especialistas(filtros, limite)` | Filtro Mongo y límite. | Lista de documentos. | Entrada: `{"ciudad": {"$regex": "México", "$options": "i"}}`, `20` -> salida: `[{...}]` |

## `app/db/repositorios/opiniones_repo.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `_clave_opinion(opinion_id)` | ID de opinión. | Filtro Mongo. | Entrada: `10` -> salida: `{"opinion_id": 10}` |
| `_obtener_coleccion()` | No recibe parámetros. | Colección async `opiniones`. | Salida: `db["opiniones"]`. |
| `_asegurar_indices()` | No recibe parámetros. | `None`; crea índices una vez. | Crea índice único en `opinion_id`, índice en `doctor_id` y fecha. |
| `obtener_opiniones_por_doctor(doctor_id, limite)` | ID Doctoralia y límite opcional. | Lista de opiniones. | Entrada: `123`, `10` -> salida: `[{ "doctor_id": 123, "texto": "..." }]` |
| `contar_opiniones_por_doctor(doctor_id)` | ID Doctoralia. | `int`. | Entrada: `123` -> salida: `42` |
| `insertar_opiniones_masivo(opiniones)` | Lista de opiniones. | Cantidad insertada o modificada. | Entrada: `[{"opinion_id": 1, "doctor_id": 123}]` -> salida: `1` |
| `eliminar_opiniones_por_doctor(doctor_id)` | ID Doctoralia. | Cantidad eliminada. | Entrada: `123` -> salida: `42` |

## `app/db/repositorios/catalogos_repo.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `_clave_compuesta(especialidad_slug, ciudad_slug)` | Slugs de especialidad y ciudad. | Filtro Mongo. | Entrada: `"endodoncia"`, `"ciudad-de-mexico"` -> salida: `{"especialidad_slug": "...", "ciudad_slug": "..."}` |
| `_obtener_coleccion()` | No recibe parámetros. | Colección async `catalogos`. | Salida: `db["catalogos"]`. |
| `_asegurar_indices()` | No recibe parámetros. | `None`; crea índice único compuesto. | Índice en `especialidad_slug, ciudad_slug`. |
| `obtener_catalogo_por_especialidad_ciudad(especialidad_slug, ciudad_slug)` | Dos slugs. | Documento o `None`. | Entrada: `"endodoncia"`, `"ciudad-de-mexico"` -> salida: `{"url": "https://..."}` |
| `insertar_catalogo(doc)` | Documento catálogo. | ID Mongo como `str`. | Entrada: `{"especialidad_slug": "endodoncia", "ciudad_slug": "cdmx"}` -> salida: `"665..."` |
| `listar_catalogos()` | No recibe parámetros. | Lista de catálogos. | Salida: `[{...}, {...}]` |
| `actualizar_catalogo(especialidad_slug, ciudad_slug, doc)` | Clave compuesta y cambios. | `bool` si modificó. | Entrada: `"endodoncia"`, `"cdmx"`, `{"url": "..."}` -> salida: `True` |
| `upsert_catalogos(documentos)` | Lista de documentos. | Resumen. | Entrada: `[{...}]` -> salida: `{"insertados": 1, "actualizados": 0, "procesados": 1}` |

## `app/services/especialistas_service.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `_normalizar_slug(texto)` | Texto libre. | Slug en minúsculas sin acentos. | Entrada: `"Ciudad de México"` -> salida: `"ciudad-de-mexico"` |
| `_es_reciente(fecha_iso, dias_max=7)` | Fecha ISO y días máximos. | `bool`. | Entrada: `"2026-05-24T10:00:00+00:00"`, `7` -> salida: `True` |
| `_cargar_catalogo_local(especialidad_slug, ciudad_slug)` | Dos slugs. | Catálogo local o `None`. | Entrada: `"endodoncia"`, `"ciudad-de-mexico"` -> salida: `{"url": "https://...", "ultima_actualizacion": "..."}` |
| `cargar_catalogo_desde_fixture(especialidad, ciudad)` | Texto de especialidad y ciudad. | Resultado de inserción. | Entrada: `"Endodoncia"`, `"Ciudad de México"` -> salida: `{"insertado": true, "url": "https://..."}` |
| `actualizar_catalogo_desde_web()` | No recibe parámetros. | Resumen de upsert en Mongo. | Salida: `{"insertados": 10, "actualizados": 20, "procesados": 30}` |
| `_mapear_perfil_a_doc(perfil, doctoralia_id, especialidad, ciudad)` | Perfil parseado, ID y contexto. | Documento Mongo normalizado. | Entrada: `{"nombre": "Dra. Ana", "servicios": []}`, `123`, `"Endodoncia"`, `"CDMX"` -> salida: `{"doctoralia_id": 123, "nombre": "Dra. Ana", ...}` |
| `buscar_o_scrapear_especialistas(especialidad, ciudad, limite=20, forzar_scraping=False)` | Búsqueda del usuario. | Resultado con fuente y especialistas. | Entrada: `"Endodoncia"`, `"CDMX"`, `5`, `False` -> salida: `{"fuente": "mixto", "total": 5, "especialistas": [...]}` |

## `app/services/opiniones_service.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `obtener_o_scrapear_opiniones(especialista, limite=30, forzar_actualizacion=False)` | Documento de especialista con `doctoralia_id` y `total_opiniones`. | Opiniones desde Mongo o scraping. | Entrada: `{"doctoralia_id": 123, "total_opiniones": 40}`, `10`, `False` -> salida: `{"fuente": "mongo", "total_en_bd": 40, "total_extraidas": 10, "opiniones": [...]}` |

