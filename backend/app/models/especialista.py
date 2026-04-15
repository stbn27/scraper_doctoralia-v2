from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Resena(BaseModel):
    texto_original: str
    texto_normalizado: Optional[str] = ""
    sentimiento: Optional[str] = "pendiente"  # favorable, desfavorable, neutro
    fecha: Optional[datetime] = None

class Ubicacion(BaseModel):
    ciudad: str
    estado: str
    coordenadas: Optional[dict] = None

# Lo que llega del scraper al crear un especialista
class EspecialistaCreate(BaseModel):
    nombre: str
    especialidad: str
    ubicacion: Ubicacion
    calificacion_global: float = 0.0
    total_resenas: int = 0
    fuente: str                    # "doctoralia" o "topdoctors"
    url_perfil: str
    horarios: Optional[str] = ""
    idiomas: Optional[list[str]] = ["Español"]
    resenas: Optional[list[Resena]] = []

# Lo que devuelve la API (incluye campos calculados)
class EspecialistaResponse(EspecialistaCreate):
    id: Optional[str] = None
    metrica_recomendacion: float = 0.0
    resumen_pln: Optional[str] = ""
    datos_suficientes: bool = False
    ultima_actualizacion: Optional[datetime] = None

    class Config:
        from_attributes = True