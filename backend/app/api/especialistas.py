from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.repositorios import especialistas_repo
from app.models.especialista import EspecialistaResponse
from app.services.especialistas_service import (
    buscar_o_scrapear_especialistas,
    cargar_catalogo_desde_fixture,
    actualizar_catalogo_desde_web,
)


router = APIRouter(prefix="/especialistas", tags=["Especialistas"])


class CatalogoCargaRequest(BaseModel):
    """Payload para cargar el catalogo desde fixtures."""

    especialidad: str
    ciudad: str


def _serializar_doc(doc: dict) -> dict:
    """Convierte el _id de Mongo a string en la respuesta."""
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
    """Busca especialistas en Mongo o ejecuta scraping segun sea necesario."""
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
    """Lista especialistas desde Mongo sin disparar scraping."""
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
