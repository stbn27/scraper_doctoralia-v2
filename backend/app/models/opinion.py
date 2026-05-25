from pydantic import BaseModel


class OpinionModel(BaseModel):
    """Modelo de una opinion de paciente."""

    opinion_id: int | None = None
    doctor_id: int
    autor: str | None = None
    rating: float | None = None
    texto: str | None = None
    fecha_publicacion: str | None = None
    servicio_consultado: str | None = None
    consultorio: str | None = None
    tipo_verificacion: str | None = None


class OpinionesResponse(BaseModel):
    """Respuesta del endpoint de opiniones por especialista."""

    especialista: dict
    opiniones_info: dict
    opiniones: list[OpinionModel]
