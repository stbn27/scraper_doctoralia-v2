from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Resena(BaseModel):
    """ "
    Representa una reseña de un especialista. Esta se obtiene despues de procesar el texto original con PLN, y se
    almacena junto con el texto original para referencia.
    - texto_original: el texto tal como se obtuvo del scraper.
    - texto_normalizado: el texto después de ser procesado con PLN (limpieza, lematización, etc.)
    - sentimiento: el resultado del análisis de sentimiento (favorable, desfavorable, neutro).
    - fecha: la fecha en que se publicó la reseña (si está disponible).
    """

    texto_original: str
    texto_normalizado: Optional[str] = ""
    sentimiento: Optional[str] = "pendiente"  # favorable, desfavorable, neutro
    fecha: Optional[datetime] = None


class Ubicacion(BaseModel):
    """
    Representa la ubicación de un especialista. Se obtiene a partir de la dirección proporcionada por el scraper,
    y se puede complementar con geocodificación para obtener coordenadas.
    - ciudad: la ciudad extraída de la dirección.
    - estado: el estado o provincia extraída de la dirección.
    - direccion: la dirección completa tal como se obtuvo del scraper.
    - coordenadas: un diccionario con latitud y longitud (opcional, se puede obtener mediante geocodificación).
    """

    ciudad: str
    estado: str
    direccion: Optional[str] = None
    coordenadas: Optional[dict] = None


# Lo que llega del scraper al crear un especialista
class EspecialistaCreate(BaseModel):
    """ "
    Representa los datos básicos de un especialista tal como se obtienen del scraper, antes de cualquier procesamiento adicional.
    - nombre: el nombre completo del especialista.
    - especialidad: la especialidad médica del especialista.
    - ubicacion: un objeto Ubicacion con los detalles de la ubicación del especialista.
    - calificacion_global: la calificación promedio del especialista (si está disponible).
    - total_resenas: el número total de reseñas del especialista (si está disponible).
    - fuente: la fuente de donde se obtuvo la información (por ejemplo, "doctoralia" o "topdoctors").
    - url_perfil: la URL del perfil del especialista en la fuente original.
    - horarios: los horarios de atención del especialista (si están disponibles).
    - idiomas: los idiomas que habla el especialista (si están disponibles).
    - resenas: una lista de objetos Resena con las reseñas del especialista (si están disponibles).
    """

    nombre: str
    especialidad: str
    ubicacion: Ubicacion
    calificacion_global: float = 0.0
    total_resenas: int = 0
    fuente: str  # "doctoralia" o "topdoctors"
    url_perfil: str
    horarios: Optional[str] = ""
    idiomas: Optional[list[str]] = ["Español"]
    resenas: Optional[list[Resena]] = []


# Lo que devuelve la API (incluye campos calculados)
class EspecialistaResponse(EspecialistaCreate):
    """ "
    Representa la información completa de un especialista que se devuelve a través de la API, incluyendo
    campos adicionales calculados o procesados.
    - id: un identificador único para el especialista (puede ser generado por la base de datos).
    - metrica_recomendacion: una métrica calculada que indica la recomendación del especialista basada en sus reseñas y calificaciones.
    - resumen_pln: un resumen generado a partir del análisis de las reseñas utilizando PLN, que destaca los puntos fuertes y débiles del especialista.
    - datos_suficientes: un indicador booleano que señala si se cuenta con suficientes datos para hacer una recomendación confiable del especialista.
    - ultima_actualizacion: la fecha y hora de la última actualización de la información del especialista, para saber cuándo se
      procesaron por última vez sus datos.
    """

    id: Optional[str] = None
    metrica_recomendacion: float = 0.0
    resumen_pln: Optional[str] = ""
    datos_suficientes: bool = False
    ultima_actualizacion: Optional[datetime] = None

    class Config:
        from_attributes = True
