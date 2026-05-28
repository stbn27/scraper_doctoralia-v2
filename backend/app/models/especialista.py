from pydantic import BaseModel, ConfigDict, Field


class ConsultorioModel(BaseModel):
    """Representa un consultorio con su direccion y clinica."""

    direccion: str | None
    clinica: str | None


class ServicioModel(BaseModel):
    """Representa un servicio del especialista con su precio."""

    nombre: str
    precio_desde: int | None
    precio_texto: str | None


class PacientesModel(BaseModel):
    """Indica los tipos de pacientes que atiende el especialista."""

    atiende_ninos: bool = False
    atiende_adultos: bool = True
    atiende_adolescentes: bool = False


class ScrapingMetaModel(BaseModel):
    """Metadatos del scraping del perfil."""

    url_origen: str | None
    fecha_consulta: str | None
    total_servicios: int = 0
    total_consultorios: int = 0


class EspecialistaModel(BaseModel):
    """Modelo principal de un especialista en MongoDB."""

    doctoralia_id: int | None = None
    nombre: str
    foto_perfil_url: str | None = None
    especialidad: str | None
    ciudad: str | None
    rating_global: float | None
    total_opiniones: int | None
    cedula: str | None
    cedulas: list[str] = []
    experiencia: list[str] = []
    servicios: list[ServicioModel] = []
    consultorios: list[ConsultorioModel] = []
    pacientes: PacientesModel | None = None
    scraping_meta: ScrapingMetaModel | None = None


class EspecialistaResponse(EspecialistaModel):
    """Modelo de respuesta para incluir el id de Mongo."""

    id: str = Field(alias="_id")
    model_config = ConfigDict(populate_by_name=True)
