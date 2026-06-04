from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.repositorios import especialistas_repo
from app.models.especialista import EspecialistaResponse
from app.models.opinion import OpinionesResponse
from app.services.especialistas_service import (
    buscar_o_scrapear_especialistas,
    cargar_catalogo_desde_fixture,
    actualizar_catalogo_desde_web,
)
from app.services.opiniones_service import obtener_o_scrapear_opiniones

router = APIRouter(prefix="/especialistas", tags=["Especialistas"])

class CatalogoCargaRequest(BaseModel):
    """Payload para cargar el catalogo desde fixtures."""

    especialidad: str
    ciudad: str


def _serializar_doc(doc: dict) -> dict:
    """
    Convierte el campo "_id" de un documento a su representación de cadena si existe y no es `None`.

    Esta función es útil para serializar documentos de MongoDB, donde el campo "_id" es un ObjectId que no es directamente serializable a JSON.

    Parametros
    ----------
    doc : dict
        Un diccionario que representa un documento de MongoDB.

    Returns
    -------
    dict
        Un diccionario con el campo "_id" convertido a cadena si estaba presente y no era `None`.
        Si el campo "_id" no existe o es `None`, el diccionario se devuelve sin modificaciones.
    """
    if "_id" in doc and doc["_id"] is not None:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("/buscar", response_model=dict)
async def buscar_especialistas(
    especialidad: str = Query(...),
    ciudad: str = Query(...),
    limite: int = Query(20, ge=1, le=100),
    forzar_scraping: bool = Query(False),
):
    """
    Busca especialistas por especialidad y ciudad.

    La función primero intenta obtener los resultados desde MongoDB y, si no
    encuentra suficientes registros o se solicita explícitamente, puede ejecutar
    scraping para completar la respuesta.

    Parámetros
    ----------
    especialidad : str
        Nombre o texto de la especialidad a buscar.
        Parametro obligatorio
    ciudad : str
        Ciudad donde se desea realizar la búsqueda.
        Parametro obligatorio
    limite : int
        Número máximo de especialistas a devolver.
        Parámetro opcional, por defecto es 20.
    forzar_scraping : bool
        Indica si se debe ignorar la caché en Mongo y ejecutar scraping.
        Parámetro opcional, por defecto es False.

    Retorna
    -------
    dict
        Diccionario con la información de la búsqueda y la lista de especialistas.

    Excepciones
    -----------
    HTTPException
        Se lanza con estado 404 si no hay especialistas disponibles para los
        criterios solicitados.
    """
    try:
        resultado = await buscar_o_scrapear_especialistas(
            especialidad=especialidad,
            ciudad=ciudad,
            limite=limite,
            forzar_scraping=forzar_scraping,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    especialistas = [_serializar_doc(doc) for doc in resultado.get("especialistas", [])]
    resultado["especialistas"] = especialistas
    return resultado


@router.get("/", response_model=list[EspecialistaResponse])
async def listar_especialistas(
    especialidad: str | None = Query(None),
    ciudad: str | None = Query(None),
    limite: int = Query(20, ge=1, le=100),
):
    """
    Listado de especialistas basado en filtros de especialidad, ciudad y límite de resultados.

    Obtiene una lista de especialistas del repositorio según los filtros proporcionados para
    especialidad, ciudad y límite en el número de resultados. Si no se proporcionan filtros,
    devolverá especialistas sin condiciones dentro del límite especificado.

    Parámetros
    ----------
    especialidad : str or None
        Filtrar especialistas por su especialidad. Se admiten coincidencias parciales mediante expresiones regulares propias de MongoDB.
        Parámetro opcional, por defecto es None, lo que significa que no se aplican filtros de especialidad.
    ciudad : str or None
        Filtrar especialistas por su ciudad. Se admiten coincidencias parciales mediante expresiones regulares.
        Filtro opcional, por defecto es None, lo que significa que no se aplican filtros de ciudad.
    limite : int
        Maximo número de especialistas a devolver. Debe ser un valor entre 1 y 100 (inclusive). Por defecto es 20.

    Returns
    -------
    Listado de especialistas
        Una lista de objetos que representan especialistas que cumplen con los criterios de búsqueda.
        Cada objeto contiene información relevante sobre el especialista, como su nombre, especialidad, ciudad, rating global y total de opiniones.
    """

    filtros = {}
    if especialidad:
        filtros["especialidad"] = {"$regex": especialidad, "$options": "i"}
    if ciudad:
        filtros["ciudad"] = {"$regex": ciudad, "$options": "i"}

    docs = await especialistas_repo.listar_especialistas(filtros, limite=limite)
    return [_serializar_doc(doc) for doc in docs]


@router.get("/{especialista_id}", response_model=EspecialistaResponse)
async def obtener_especialista(especialista_id: str):
    """Obtiene un especialista por ObjectId."""
    doc = await especialistas_repo.buscar_por_id(especialista_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")
    return _serializar_doc(doc)


@router.get("/doctoralia/{doctoralia_id}", response_model=EspecialistaResponse)
async def obtener_especialista_por_doctoralia_id(doctoralia_id: int):
    """Obtiene un especialista por su identificador de Doctoralia."""
    doc = await especialistas_repo.buscar_por_doctoralia_id(doctoralia_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")
    return _serializar_doc(doc)


@router.delete("/{especialista_id}")
async def eliminar_especialista(especialista_id: str):
    """Elimina un especialista por ObjectId."""
    eliminado = await especialistas_repo.eliminar_especialista(especialista_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")
    return {"eliminado": True}


@router.post("/catalogo/cargar")
async def cargar_catalogo(payload: CatalogoCargaRequest):
    """Carga el catalogo de especialidad y ciudad desde fixtures."""
    try:
        return await cargar_catalogo_desde_fixture(payload.especialidad, payload.ciudad)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/catalogo/actualizar")
async def actualizar_catalogo():
    """Scrapea el catalogo completo y lo persiste en Mongo."""
    return await actualizar_catalogo_desde_web()


@router.get("/{especialista_id}/opiniones", response_model=OpinionesResponse)
async def obtener_opiniones(
    especialista_id: str,
    limite: int = Query(30, ge=1, le=200),
    actualizar: bool = Query(False),
):
    """
    Obtiene y devuelve las opiniones de un especialista según la identificación proporcionada.
    Permite parámetros opcionales para limitar el número de reseñas obtenidas y forzar una
    Actualización de los datos de revisión mediante scraping.

    Parámetros
    ----------
    - especialista_id: str
        El identificador único del especialista cuyas reseñas se van a buscar.
    - límite: int, predeterminado = 30
        El número máximo de reseñas para recuperar. Debe estar entre 1 y 200 (inclusive).
    - actualizar: bool, default=Falso actualizaralse
        Si se debe forzar una actualización eliminando las últimas revisiones, incluso si son
        ya disponible en la base de datos.

    Salida
    -------
    dict
    Un diccionario que contiene detalles sobre el especialista, metadatos sobre las reseñas,
    y una lista de reseñas serializadas.

    Excepciones
    ------
    HTTPExcepción
    Si no se pudo encontrar al especialista con la identificación proporcionada, aparecerá el error "404 No encontrado".
    """

    # Buscamos al especialista/médico
    especialista = await especialistas_repo.buscar_por_id(especialista_id)
    if not especialista:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    # Obtenemos las opiniones del especialista, ya sea desde la base de datos o mediante scraping si es necesario o solicitado
    resultado = await obtener_o_scrapear_opiniones(
        especialista=especialista,
        limite=limite,
        forzar_actualizacion=actualizar,
    )

    # Información basica del especialista/médico
    especialista_info = {
        "nombre": especialista.get("nombre"),
        "especialidad": especialista.get("especialidad"),
        "ciudad": especialista.get("ciudad"),
        "rating_global": especialista.get("rating_global"),
        "total_opiniones": especialista.get("total_opiniones"),
    }

    # Metadatos de las opiniones
    opiniones_info = {
        "fuente": resultado.get("fuente"),
        "total_en_bd": resultado.get("total_en_bd"),
        "total_extraidas": resultado.get("total_extraidas"),
    }

    opiniones = [_serializar_doc(op) for op in resultado.get("opiniones", [])]

    return {
        "especialista": especialista_info,
        "opiniones_info": opiniones_info,
        "opiniones": opiniones,
    }
