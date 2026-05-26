"""Este archivo concentra el acceso async a la colección MongoDB `especialistas`. No contiene
reglas de negocio de scraping ni lógica HTTP; su responsabilidad es construir filtros, asegurar
índices y ejecutar operaciones CRUD sobre Mongo usando Motor.

## Dependencias

| Import                   | Uso                                                           |
| ------------------------ | ------------------------------------------------------------- |
| `re`                     | Escapa texto antes de convertirlo en regex Mongo.             |
| `ObjectId` de `bson`     | Convierte IDs recibidos como `str` a ObjectId real de Mongo.  |
| `ASCENDING` de `pymongo` | Define dirección de índices.                                  |
| `get_mongo_async_db`     | Obtiene la base Mongo async configurada en `app/db/mongo.py`. |
"""

import re

from bson import ObjectId
from pymongo import ASCENDING

from app.db.mongo import get_mongo_async_db

"""
Variable global usada como bandera para no intentar crear índices en cada llamada.
La primera operación del repositorio ejecuta `_asegurar_indices()`, crea los índices y deja
`_indices_creados = True`.
"""
_indices_creados = False


def _normalizar_regex(valor: str) -> dict:
    """
    Construye un diccionario con un patrón de expresión regular que no distingue entre
    mayúsculas y minúsculas a partir de la cadena de entrada.
    El patrón escapa los caracteres especiales de la cadena para garantizar una coincidencia
    literal y agrega una opción para no distinguir entre mayúsculas y minúsculas.

    Parámetros
    ----------
    valor : str
        La cadena de entrada que se convertirá en un patrón de expresión regular.

    Returns
    -------
    dict
        Un diccionario con las claves "$regex" y "$options" que representa el patrón.
    """
    return {"$regex": re.escape(valor), "$options": "i"}


async def _obtener_coleccion():
    """
    Recupera de forma asíncrona la colección 'especialistas' de la base de datos MongoDB.

    Esta función obtiene una colección específica de la base de datos MongoDB asíncrona ya
    conectada. La colección obtenida puede utilizarse posteriormente para realizar operaciones
    de base de datos.

    Returns
    -------
    Collection
        La colección 'especialistas' de la base de datos MongoDB.
    """
    db = get_mongo_async_db()
    return db["especialistas"]


async def _asegurar_indices():
    """
    Asegura que los índices necesarios se creen en la colección de la base de datos. Esta
    función está diseñada para ser idempotente, lo que significa que solo creará los índices
    una vez. Las llamadas posteriores no tendrán efecto si los índices ya existen.

    Esta función interactúa con una colección MongoDB para crear dos tipos de índices:
    1. Un índice único y disperso sobre el campo `doctoralia_id`.
    2. Un índice compuesto sobre los campos `especialidad` y `ciudad`.

    La función usa una bandera global para llevar el control de si los índices ya fueron
    creados y así evitar llamadas redundantes a la base de datos.

    Notes
    -----
    Esta función es asíncrona y debe llamarse con `await`.

    Raises
    ------
    Cualquier excepción generada durante la obtención de la colección o la creación de índices
    no se documenta aquí. Consulta la documentación de la biblioteca cliente de MongoDB para
    conocer errores específicos.

    See Also
    --------
    _obtener_coleccion : Recupera la colección de MongoDB.

    """
    global _indices_creados
    if _indices_creados:
        return

    coleccion = await _obtener_coleccion()
    await coleccion.create_index(
        [("doctoralia_id", ASCENDING)], unique=True, sparse=True
    )
    await coleccion.create_index([("especialidad", ASCENDING), ("ciudad", ASCENDING)])
    _indices_creados = True


async def obtener_por_especialidad_y_ciudad(
    especialidad: str, ciudad: str
) -> list[dict]:
    """
    Obtiene una lista de documentos de la base de datos basados en la especialidad
    y ciudad especificadas.

    Esta función asíncrona consulta una colección de MongoDB, utilizando filtros
    basados en expresiones regulares normalizadas para la especialidad y ciudad dadas.
    Asegura que existan los índices necesarios en la base de datos antes de realizar
    la consulta y recupera documentos que coinciden con los criterios.

    Parámetros
    ----------
    especialidad : str
        La especialidad para filtrar los documentos.
    ciudad : str
        La ciudad para filtrar los documentos.

    Devuelve
    -------
    list[dict]
        Una lista de diccionarios donde cada diccionario representa un documento
        de la colección que coincide con los criterios especificados.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    filtro = {
        "especialidad": _normalizar_regex(especialidad),
        "ciudad": _normalizar_regex(ciudad),
    }
    cursor = coleccion.find(filtro)
    return [doc async for doc in cursor]


async def insertar_especialista(doc: dict) -> str:
    """
    Inserta o actualiza un documento de especialista en la base de datos. Si el documento
    contiene un "doctoralia_id", se realiza una operación upsert para actualizar el registro
    existente o insertar uno nuevo. Si no se proporciona "doctoralia_id", el documento
    se inserta como nuevo. Devuelve el ID del documento insertado o actualizado.

    Parámetros
    ----------
    doc : dict
        El diccionario que contiene los datos del especialista a insertar o actualizar.
        Puede incluir un campo "doctoralia_id" para identificar el registro.

    Devuelve
    -------
    str
        El ID del documento insertado o actualizado como una cadena.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()

    doctoralia_id = doc.get("doctoralia_id")
    if doctoralia_id is None:
        resultado = await coleccion.insert_one(doc)
        return str(resultado.inserted_id)

    resultado = await coleccion.update_one(
        {"doctoralia_id": doctoralia_id}, {"$set": doc}, upsert=True
    )
    if resultado.upserted_id:
        return str(resultado.upserted_id)

    existente = await coleccion.find_one({"doctoralia_id": doctoralia_id})
    return str(existente.get("_id")) if existente else ""


async def actualizar_especialista(doctoralia_id: int, doc: dict) -> bool:
    """
    Actualiza la información de un especialista en la base de datos según su ID de Doctoralia.

    Esta función asíncrona actualiza los datos del especialista en la colección
    correspondiente. La actualización se realiza utilizando el ID de Doctoralia proporcionado
    y el diccionario de datos. Devuelve un booleano indicando si la operación de actualización
    ha modificado algún documento.

    Parámetros
    ----------
    doctoralia_id : int
        El identificador único del especialista en el sistema Doctoralia.
    doc : dict
        Un diccionario que contiene los campos y sus valores respectivos a actualizar
        en el registro del especialista.

    Devuelve
    -------
    bool
        True si el documento del especialista fue actualizado exitosamente (es decir,
        al menos un campo fue modificado); False en caso contrario.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    resultado = await coleccion.update_one(
        {"doctoralia_id": doctoralia_id}, {"$set": doc}
    )
    return resultado.modified_count > 0


async def buscar_por_doctoralia_id(doctoralia_id: int) -> dict | None:
    """
    Busca un documento en la colección por su ID de Doctoralia.

    Esta función asegura que los índices necesarios se creen antes de consultar
    la colección. Recupera un único documento que coincide con el ID de Doctoralia
    proporcionado.

    Parámetros
    ----------
    doctoralia_id : int
        El ID único asociado con Doctoralia a buscar en la colección.

    Devuelve
    -------
    dict o None
        Un diccionario que representa el documento si se encuentra una coincidencia,
        o None si ningún documento coincide con el ID de Doctoralia proporcionado.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    return await coleccion.find_one({"doctoralia_id": doctoralia_id})


async def buscar_por_id(id: str) -> dict | None:
    """
    Obtiene un documento por su identificador único (ID) de la base de datos.

    Esta función asíncrona asegura que los índices necesarios de la base de datos
    estén configurados antes de intentar recuperar datos. Luego valida y convierte
    el ID proporcionado al formato apropiado y obtiene el documento correspondiente
    de la colección. Si el ID no es válido, la función devuelve None.

    Parámetros
    ----------
    id : str
        El identificador único (ID) del documento a recuperar.

    Devuelve
    -------
    dict o None
        Devuelve el documento como un diccionario si se encuentra; en caso contrario,
        devuelve None.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    try:
        oid = ObjectId(id)
    except Exception:
        return None
    return await coleccion.find_one({"_id": oid})


async def eliminar_especialista(id: str) -> bool:
    """
    Elimina un registro de especialista de la base de datos según su identificador.
    Esta operación asegura que los índices apropiados estén configurados antes de
    intentar eliminar el registro. El identificador se valida y se convierte a su
    formato ObjectId antes de realizar la eliminación.

    Parámetros
    ----------
    id : str
        El identificador único del registro del especialista a eliminar.

    Devuelve
    -------
    bool
        True si el registro del especialista fue eliminado exitosamente;
        False en caso contrario.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    try:
        oid = ObjectId(id)
    except Exception:
        return False
    resultado = await coleccion.delete_one({"_id": oid})
    return resultado.deleted_count > 0


async def listar_especialistas(filtros: dict, limite: int = 50) -> list[dict]:
    """
    Listar especialistas según los filtros proporcionados.

    Esta función consulta una base de datos asíncrona para listar especialistas
    que coincidan con los filtros especificados. El cliente puede establecer
    un límite en el número de resultados devueltos. Los resultados se presentan
    en forma de lista de diccionarios.

    Parámetros
    ----------
    filtros : dict
        Filtros utilizados para realizar la búsqueda en la colección de especialistas.
        Las claves del diccionario deben coincidir con los campos disponibles en
        la colección.
    limite : int, optional
        Número máximo de especialistas a retornar. El valor predeterminado es 50.

    Returns
    -------
    list of dict
        Lista de especialistas, cada uno representado como un diccionario con
        sus respectivos campos y valores.
    """
    await _asegurar_indices()
    coleccion = await _obtener_coleccion()
    cursor = coleccion.find(filtros).limit(limite)
    return [doc async for doc in cursor]
