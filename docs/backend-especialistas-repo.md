# `backend/app/db/repositorios/especialistas_repo.py`

Este archivo concentra el acceso async a la colección MongoDB `especialistas`. No contiene reglas de negocio de scraping ni lógica HTTP; su responsabilidad es construir filtros, asegurar índices y ejecutar operaciones CRUD sobre Mongo usando Motor.

## Dependencias

| Import                   | Uso                                                           |
| ------------------------ | ------------------------------------------------------------- |
| `re`                     | Escapa texto antes de convertirlo en regex Mongo.             |
| `ObjectId` de `bson`     | Convierte IDs recibidos como `str` a ObjectId real de Mongo.  |
| `ASCENDING` de `pymongo` | Define direcci�n de �ndices.                                  |
| `get_mongo_async_db`     | Obtiene la base Mongo async configurada en `app/db/mongo.py`. |


## Estado interno

```python
_indices_creados = False
```

Variable global usada como bandera para no intentar crear índices en cada llamada. La primera operación de repositorio ejecuta `_asegurar_indices()`, crea los índices y deja `_indices_creados = True`.

Punto de cuidado: esta bandera vive solo en el proceso actual. Si hay varios workers de Uvicorn/Gunicorn, cada worker intentará asegurar índices una vez. Mongo lo tolera, pero conviene saberlo.

## Índices creados

```python
await coleccion.create_index(
    [("doctoralia_id", ASCENDING)], unique=True, sparse=True
)
await coleccion.create_index([("especialidad", ASCENDING), ("ciudad", ASCENDING)])
```

El índice `doctoralia_id` es único y `sparse=True`, así que evita duplicados cuando el campo existe, pero permite documentos sin `doctoralia_id`.

El índice compuesto `especialidad, ciudad` ayuda a las búsquedas por ambos campos. Aun así, las búsquedas actuales usan regex case-insensitive, por lo que el aprovechamiento del índice puede ser limitado dependiendo del patrón y de MongoDB.

## Flujo común

Todas las funciones públicas siguen este patrón:

1. Llaman `await _asegurar_indices()`.
2. Obtienen la colección con `await _obtener_coleccion()`.
3. Ejecutan una operación Mongo.
4. Devuelven datos Python simples: `dict`, `list[dict]`, `str`, `bool` o `None`.

## `_normalizar_regex(valor: str) -> dict`

Construye un filtro regex de MongoDB que busca texto de forma literal y sin distinguir mayúsculas/minúsculas.

```python
def _normalizar_regex(valor: str) -> dict:
    return {"$regex": re.escape(valor), "$options": "i"}
```

Entrada:

```python
"Ciudad de México"
```

Salida:

```python
{"$regex": "Ciudad\\ de\\ México", "$options": "i"}
```

Se usa en `obtener_por_especialidad_y_ciudad()` para construir filtros seguros. `re.escape()` evita que una entrada como `.*` se convierta en una búsqueda regex abierta.

## `_obtener_coleccion()`

Devuelve la colección async `especialistas`.

```python
async def _obtener_coleccion():
    db = get_mongo_async_db()
    return db["especialistas"]
```

Entrada: no recibe parámetros.

Salida: un objeto colección de Motor equivalente a `db["especialistas"]`.

Ejemplo:

```python
coleccion = await _obtener_coleccion()
doc = await coleccion.find_one({"doctoralia_id": 123})
```

## `_asegurar_indices()`

Crea los índices necesarios en MongoDB una sola vez por proceso.

Entrada: no recibe parámetros.

Salida: no retorna valor explícito; devuelve `None`.

Efecto:

- Crea índice único sparse en `doctoralia_id`.
- Crea índice compuesto en `especialidad` y `ciudad`.

Ejemplo:

```python
await _asegurar_indices()
```

Después de la primera llamada, las siguientes retornan inmediatamente por la bandera `_indices_creados`.

## `obtener_por_especialidad_y_ciudad(especialidad: str, ciudad: str) -> list[dict]`

Busca especialistas cuyo campo `especialidad` y `ciudad` coincidan con los textos recibidos, ignorando mayúsculas/minúsculas.

Entrada:

```python
especialidad = "Endodoncia"
ciudad = "Ciudad de México"
```

Filtro generado:

```python
{
    "especialidad": {"$regex": "Endodoncia", "$options": "i"},
    "ciudad": {"$regex": "Ciudad\\ de\\ México", "$options": "i"},
}
```

Salida encontrada:

```python
[
    {
        "_id": ObjectId("665000000000000000000001"),
        "doctoralia_id": 12345,
        "nombre": "Dra. Ana Pérez",
        "especialidad": "Endodoncia",
        "ciudad": "Ciudad de México",
    }
]
```

Si no hay resultados, devuelve `[]`.

## `insertar_especialista(doc: dict) -> str`

Inserta o actualiza un especialista. Si el documento trae `doctoralia_id`, usa upsert por ese campo. Si no trae `doctoralia_id`, inserta un documento nuevo.

Caso A, documento sin `doctoralia_id`:

```python
doc = {
    "nombre": "Dra. Ana Pérez",
    "especialidad": "Endodoncia",
    "ciudad": "Ciudad de México",
}
```

Operación: `insert_one(doc)`.

Salida:

```python
"665000000000000000000001"
```

Caso B, documento con `doctoralia_id` nuevo:

```python
doc = {
    "doctoralia_id": 12345,
    "nombre": "Dra. Ana Pérez",
    "especialidad": "Endodoncia",
    "ciudad": "Ciudad de México",
}
```

Operación:

```python
update_one(
    {"doctoralia_id": 12345},
    {"$set": doc},
    upsert=True,
)
```

Salida: ID Mongo como texto.

Caso C, documento con `doctoralia_id` existente: actualiza con `$set`; como `update_one()` no devuelve `upserted_id` cuando solo actualiza, el código hace un `find_one()` para recuperar el `_id` existente.

Punto de cuidado: si el documento existe, el método devuelve el `_id` aunque no se haya modificado nada. Eso es útil para operaciones tipo "guardar y dame el ID".

## `actualizar_especialista(doctoralia_id: int, doc: dict) -> bool`

Actualiza un especialista existente por `doctoralia_id`.

Entrada:

```python
doctoralia_id = 12345
doc = {
    "nombre": "Dra. Ana Pérez",
    "rating_global": 4.9,
}
```

Salida:

```python
True
```

si Mongo modificó al menos un campo.

Devuelve `False` si no encontró el documento o si el documento encontrado ya tenía exactamente esos valores.

Punto de cuidado: `modified_count > 0` no distingue entre "no existe" y "existe pero no cambió". Si se necesita saber si el documento fue encontrado, sería mejor revisar `resultado.matched_count > 0`.

## `buscar_por_doctoralia_id(doctoralia_id: int) -> dict | None`

Busca un especialista por su identificador de Doctoralia.

Entrada:

```python
12345
```

Salida encontrada:

```python
{
    "_id": ObjectId("665000000000000000000001"),
    "doctoralia_id": 12345,
    "nombre": "Dra. Ana Pérez",
}
```

Salida no encontrada:

```python
None
```

Uso típico: evitar volver a scrapear perfiles ya guardados.

## `buscar_por_id(id: str) -> dict | None`

Busca un especialista por `_id` de Mongo recibido como string.

Entrada válida:

```python
"665000000000000000000001"
```

Salida encontrada:

```python
{
    "_id": ObjectId("665000000000000000000001"),
    "doctoralia_id": 12345,
    "nombre": "Dra. Ana Pérez",
}
```

Entrada inválida:

```python
"no-es-object-id"
```

Salida con entrada inválida:

```python
None
```

La función no lanza error si el ID no tiene formato ObjectId; devuelve `None`. Esto permite que la capa API responda `404` sin exponer errores internos.

## `eliminar_especialista(id: str) -> bool`

Elimina un documento por `_id` de Mongo recibido como string.

Entrada válida:

```python
"665000000000000000000001"
```

Salida si eliminó:

```python
True
```

Salida si no existe o el ID no es válido:

```python
False
```

Punto importante: la función solo elimina el especialista. No elimina opiniones relacionadas en la colección `opiniones`. Si el sistema requiere borrado en cascada, debería coordinarse desde una capa de servicio.

## `listar_especialistas(filtros: dict, limite: int = 50) -> list[dict]`

Lista documentos usando filtros Mongo arbitrarios y aplica límite.

Entrada sin filtros:

```python
filtros = {}
limite = 20
```

Salida:

```python
[
    {"_id": ObjectId("665000000000000000000001"), "nombre": "Dra. Ana Pérez"},
    {"_id": ObjectId("665000000000000000000002"), "nombre": "Dr. Luis Gómez"},
]
```

Entrada con filtros:

```python
filtros = {
    "ciudad": {"$regex": "México", "$options": "i"}
}
limite = 10
```

Salida:

```python
[
    {
        "_id": ObjectId("665000000000000000000001"),
        "nombre": "Dra. Ana Pérez",
        "ciudad": "Ciudad de México",
    }
]
```

Punto de cuidado: esta función confía en que quien la llama construya filtros seguros y razonables. Actualmente `api/especialistas.py` construye filtros simples con regex.

## Ejemplo de uso desde una ruta FastAPI

```python
from app.db.repositorios import especialistas_repo


@router.get("/{especialista_id}")
async def obtener_especialista(especialista_id: str):
    doc = await especialistas_repo.buscar_por_id(especialista_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")
    doc["_id"] = str(doc["_id"])
    return doc
```

## Ejemplo de uso desde un servicio

```python
existente = await especialistas_repo.buscar_por_doctoralia_id(12345)

if existente:
    await especialistas_repo.actualizar_especialista(
        12345,
        {"rating_global": 4.9},
    )
else:
    nuevo_id = await especialistas_repo.insertar_especialista(
        {
            "doctoralia_id": 12345,
            "nombre": "Dra. Ana Pérez",
            "especialidad": "Endodoncia",
            "ciudad": "Ciudad de México",
        }
    )
```

## Relación con otros módulos

| Módulo | Cómo lo usa |
| --- | --- |
| `app/api/especialistas.py` | Lista, obtiene y elimina especialistas desde endpoints HTTP. |
| `app/services/especialistas_service.py` | Busca especialistas existentes, inserta perfiles scrapeados y refresca perfiles por `doctoralia_id`. |
| `app/services/opiniones_service.py` | No usa directamente este repositorio, pero recibe especialistas que normalmente salen de aquí. |

## Comportamiento esperado por función

| Función | Si todo sale bien | Si no encuentra datos | Si recibe ID inválido |
| --- | --- | --- | --- |
| `obtener_por_especialidad_y_ciudad()` | Lista de documentos. | `[]` | No aplica. |
| `insertar_especialista()` | ID Mongo como `str`. | Inserta si no existe. | No valida ObjectId. |
| `actualizar_especialista()` | `True` si modificó. | `False` | No aplica. |
| `buscar_por_doctoralia_id()` | Documento. | `None` | No aplica. |
| `buscar_por_id()` | Documento. | `None` | `None` |
| `eliminar_especialista()` | `True` | `False` | `False` |
| `listar_especialistas()` | Lista limitada. | `[]` | Depende del filtro recibido. |

## Mejoras sugeridas

1. Cambiar `actualizar_especialista()` para distinguir documento encontrado de documento modificado si la capa de servicio necesita esa diferencia.

```python
return resultado.matched_count > 0
```

2. Agregar tipos de retorno internos para `_obtener_coleccion()` si se quiere mejorar autocompletado y análisis estático.

3. Considerar normalizar `especialidad` y `ciudad` en campos adicionales como `especialidad_slug` y `ciudad_slug`. Las búsquedas exactas por slug serían más predecibles e indexables que regex.

4. Agregar paginación a `listar_especialistas()`, por ejemplo `skip` y `limit`, si la colección crece.

5. Agregar tests unitarios con una base Mongo de prueba o mocks de Motor para cubrir ID inválido, upsert nuevo, update existente, eliminación por ObjectId y filtros regex.
