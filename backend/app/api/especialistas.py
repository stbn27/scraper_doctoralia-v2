from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from bson import ObjectId
from app.db.mongo import get_mongo_db
from app.models.especialista import EspecialistaCreate, EspecialistaResponse
from datetime import datetime

router = APIRouter(prefix="/especialistas", tags=["Especialistas"])


def serializar(doc: dict) -> dict:
    """Convierte ObjectId de Mongo a string para JSON."""
    doc["id"] = str(doc.pop("_id"))
    return doc


# CREATE (lo que llega del scraper)
@router.post("/", response_model=EspecialistaResponse, status_code=201)
def crear_especialista(data: EspecialistaCreate):
    """ "
    Crea un nuevo especialista en la base de datos a partir de los datos obtenidos del scraper. Se verifica que no exista
    un especialista con la misma URL de perfil para evitar duplicados. Se agregan campos adicionales como la métrica de recomendación,
    el resumen de PLN, y la fecha de última actualización.
    - data: un objeto EspecialistaCreate que contiene la información básica del especialista obtenida del scraper.
    - Retorna: un objeto EspecialistaResponse con la información completa del especialista, incluyendo los campos adicionales calculados.
    - Errores: devuelve un error 409 si ya existe un especialista con la misma URL de perfil, y un error 400 si los datos proporcionados son inválidos.
    """

    db = get_mongo_db()

    # Evitar duplicados por url_perfil
    existe = db.especialistas.find_one({"url_perfil": data.url_perfil})
    if existe:
        raise HTTPException(status_code=409, detail="El especialista ya existe")

    doc = data.model_dump()
    doc["metrica_recomendacion"] = 0.0
    doc["resumen_pln"] = ""
    doc["datos_suficientes"] = False
    doc["ultima_actualizacion"] = datetime.utcnow()

    resultado = db.especialistas.insert_one(doc)
    doc["id"] = str(resultado.inserted_id)

    return doc


# READ ALL (con filtros)
@router.get("/", response_model=list[EspecialistaResponse])
def listar_especialistas(
    especialidad: Optional[str] = Query(None, description="Ej: Cardiología"),
    ciudad: Optional[str] = Query(None, description="Ej: CDMX"),
    fuente: Optional[str] = Query(None, description="doctoralia o topdoctors"),
    limite: int = Query(20, ge=1, le=100),
    pagina: int = Query(1, ge=1),
):
    """
    Lista los especialistas disponibles en la base de datos, con la posibilidad de aplicar filtros por especialidad, ciudad y fuente.
    Se pueden paginar los resultados utilizando los parámetros de límite y página.
    - especialidad: filtro opcional para buscar especialistas por su especialidad médica (ej: Cardiología).
    - ciudad: filtro opcional para buscar especialistas por la ciudad donde se encuentran (ej: CDMX).
    - fuente: filtro opcional para buscar especialistas por la fuente de donde se obtuvo su información (ej: doctoralia o topdoctors).
    - limite: número máximo de especialistas a devolver por página (por defecto 20, mínimo 1, máximo 100).
    - pagina: número de la página a devolver (por defecto 1, mínimo 1).
    - Retorna: una lista de objetos EspecialistaResponse que cumplen con los filtros aplicados, ordenados por la métrica de recomendación de forma descendente.
    - Errores: devuelve un error 400 si los parámetros de consulta son inválidos.
    """
    db = get_mongo_db()

    filtro = {}
    if especialidad:
        filtro["especialidad"] = {"$regex": especialidad, "$options": "i"}
    if ciudad:
        filtro["ubicacion.ciudad"] = {"$regex": ciudad, "$options": "i"}
    if fuente:
        filtro["fuente"] = fuente

    skip = (pagina - 1) * limite

    docs = (
        db.especialistas.find(filtro)
        .sort("metrica_recomendacion", -1)
        .skip(skip)
        .limit(limite)
    )

    return [serializar(doc) for doc in docs]


# READ ONE
@router.get("/{especialista_id}", response_model=EspecialistaResponse)
def obtener_especialista(especialista_id: str):
    """ "
    Obtiene la información completa de un especialista a partir de su identificador único. Se devuelve un error 404
    si el especialista no se encuentra.
    - especialista_id: el identificador único del especialista a obtener.
    - Retorna: un objeto EspecialistaResponse con la información completa del especialista, incluyendo los campos adicionales calculados.
    - Errores: devuelve un error 400 si el ID proporcionado es inválido, y un error 404 si no se encuentra un especialista con ese ID.
    """
    db = get_mongo_db()

    try:
        oid = ObjectId(especialista_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    doc = db.especialistas.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    return serializar(doc)


# UPDATE
@router.put("/{especialista_id}", response_model=EspecialistaResponse)
def actualizar_especialista(especialista_id: str, data: EspecialistaCreate):
    """ "
    Actualiza la información de un especialista existente a partir de su identificador único. Se pueden actualizar los campos básicos del especialista,
    y se actualiza la fecha de última actualización. Se devuelve un error 404 si el especialista no se encuentra.
    - especialista_id: el identificador único del especialista a actualizar.
    - data: los datos a actualizar del especialista.
    - Retorna: un objeto EspecialistaResponse con la información actualizada del especialista.
    - Errores: devuelve un error 400 si el ID proporcionado es inválido, y un error 404 si no se encuentra un especialista con ese ID.
    """

    db = get_mongo_db()

    try:
        oid = ObjectId(especialista_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    cambios = data.model_dump(exclude_unset=True)
    cambios["ultima_actualizacion"] = datetime.utcnow()

    resultado = db.especialistas.find_one_and_update(
        {"_id": oid}, {"$set": cambios}, return_document=True
    )

    if not resultado:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")

    return serializar(resultado)


# DELETE
@router.delete("/{especialista_id}", status_code=204)
def eliminar_especialista(especialista_id: str):
    """ "
    Elimina un especialista de la base de datos a partir de su identificador único. Se devuelve un error 404 si el especialista no se encuentra.
    - especialista_id: el identificador único del especialista a eliminar.
    """

    db = get_mongo_db()

    try:
        oid = ObjectId(especialista_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    resultado = db.especialistas.delete_one({"_id": oid})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Especialista no encontrado")
