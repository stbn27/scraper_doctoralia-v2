"""
Schemas Pydantic centralizados para la API MedRec v2.

Contiene todos los modelos de request/response necesarios para los endpoints
de especialistas, catálogos, chatbot, usuarios, direcciones, favoritos e historial.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# UTILIDADES
# =============================================================================


class PaginadoBase(BaseModel):
    """Campos comunes de paginación incluidos en respuestas listadas."""

    total: int = Field(
        ..., description="Total de documentos que coinciden con los filtros"
    )
    page: int = Field(..., description="Página actual (1-indexed)")
    limit: int = Field(..., description="Documentos por página")
    pages: int = Field(..., description="Total de páginas")
    has_next: bool = Field(..., description="Indica si existe una página siguiente")
    has_prev: bool = Field(..., description="Indica si existe una página anterior")


# =============================================================================
# ESPECIALISTAS
# =============================================================================


class ConsultorioPrincipalSchema(BaseModel):
    """Consultorio resumido para vistas de tarjeta."""

    direccion: Optional[str] = None
    clinica: Optional[str] = None


class PacientesSchema(BaseModel):
    """Tipos de pacientes que atiende el especialista."""

    atiende_ninos: bool = False
    atiende_adultos: bool = False
    atiende_adolescentes: bool = False


class ServicioSchema(BaseModel):
    """Servicio ofrecido por el especialista con precio."""

    nombre: str
    precio_desde: Optional[int] = None
    precio_texto: Optional[str] = None


class MetricasLocalesSchema(BaseModel):
    """Métricas estadísticas calculadas localmente sobre las opiniones."""

    total_opiniones_bd: Optional[int] = None
    opiniones_enviadas_al_modelo: Optional[int] = None
    porcentaje_verificadas: Optional[float] = None
    recencia_promedio_dias: Optional[float] = None
    longitud_promedio_palabras: Optional[float] = None
    porcentaje_texto_corto: Optional[float] = None
    porcentaje_ultimos_6_meses: Optional[float] = None
    rating_promedio: Optional[float] = None
    sospecha_fraude: Optional[bool] = None
    razones_fraude: list[str] = []


class AnalisisResumenSchema(BaseModel):
    """Resumen del análisis IA incluido en la tarjeta de especialista."""

    estado: Optional[str] = None
    modelo_usado: Optional[str] = None
    fecha_analisis: Optional[str] = None
    puntuacion_recomendacion: Optional[float] = None
    resumen: Optional[str] = None
    confiabilidad_opiniones: Optional[str] = None
    sospecha_fraude: Optional[bool] = None
    razones_fraude: list[str] = []
    metricas_locales: Optional[MetricasLocalesSchema] = None


class AnalisisDetalleSchema(AnalisisResumenSchema):
    """Análisis IA completo incluido en la vista de detalle de especialista."""

    tiene_analisis: bool = False
    version_prompt: Optional[str] = None
    puntos_fuertes: list[str] = []
    puntos_debiles: list[str] = []
    justificacion_puntuacion: Optional[str] = None


class EspecialistaCardResponse(BaseModel):
    """
    Respuesta de un especialista en formato de tarjeta (card) para listados y favoritos.

    Incluye los datos mínimos necesarios para renderizar una card en el frontend,
    así como el resumen del análisis IA si existe.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(
        ..., alias="_id", description="ObjectId de MongoDB serializado como string"
    )
    doctoralia_id: Optional[int] = None
    nombre: str
    especialidad: Optional[str] = None
    ciudad: Optional[str] = None
    rating_global: Optional[float] = None
    total_opiniones: Optional[int] = None
    foto_perfil_url: Optional[str] = None
    cedula: Optional[str] = None
    consultorio_principal: Optional[ConsultorioPrincipalSchema] = None
    pacientes: Optional[PacientesSchema] = None
    precio_minimo: Optional[int] = None
    servicios_destacados: list[ServicioSchema] = []
    tiene_analisis: bool = False
    analisis: Optional[AnalisisResumenSchema] = None


class ScrapingMetaSchema(BaseModel):
    """Metadatos del proceso de scraping del perfil."""

    url_origen: Optional[str] = None
    fecha_consulta: Optional[str] = None
    total_servicios: int = 0
    total_consultorios: int = 0


class EspecialistaDetailResponse(BaseModel):
    """
    Respuesta completa de un especialista para la vista de detalle.

    Incluye todos los campos disponibles, servicios completos, consultorios,
    experiencia, cédulas y el análisis IA completo si existe.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    doctoralia_id: Optional[int] = None
    nombre: str
    foto_perfil_url: Optional[str] = None
    especialidad: Optional[str] = None
    ciudad: Optional[str] = None
    rating_global: Optional[float] = None
    total_opiniones: Optional[int] = None
    cedula: Optional[str] = None
    cedulas: list[str] = []
    experiencia: list[str] = []
    servicios: list[ServicioSchema] = []
    consultorios: list[ConsultorioPrincipalSchema] = []
    pacientes: Optional[PacientesSchema] = None
    scraping_meta: Optional[ScrapingMetaSchema] = None
    analisis: Optional[AnalisisDetalleSchema] = None


class EspecialistasListResponse(PaginadoBase):
    """Respuesta paginada de la búsqueda de especialistas con filtros aplicados."""

    filters_applied: dict[str, Any] = {}
    results: list[EspecialistaCardResponse] = []
    message: Optional[str] = None


# =============================================================================
# OPINIONES
# =============================================================================


class OpinionResponse(BaseModel):
    """
    Respuesta de una opinión individual de paciente.

    El campo `es_verificada` se calcula a partir de `tipo_verificacion`.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(None, alias="_id")
    opinion_id: Optional[int] = None
    doctor_id: Optional[int] = None
    autor: Optional[str] = None
    rating: Optional[float] = None
    texto: Optional[str] = None
    fecha_publicacion: Optional[str] = None
    servicio_consultado: Optional[str] = None
    consultorio: Optional[str] = None
    tipo_verificacion: Optional[str] = None
    es_verificada: bool = False


class EspecialistaResumenParaOpiniones(BaseModel):
    """Información resumida del especialista incluida en la respuesta de opiniones."""

    id: str = Field(..., alias="_id")
    doctoralia_id: Optional[int] = None
    nombre: str
    especialidad: Optional[str] = None
    ciudad: Optional[str] = None
    rating_global: Optional[float] = None
    total_opiniones: Optional[int] = None

    model_config = ConfigDict(populate_by_name=True)


class OpinionesPaginadasResponse(BaseModel):
    """Respuesta paginada de opiniones para un especialista."""

    especialista: EspecialistaResumenParaOpiniones
    total: int
    page: int
    limit: int
    pages: int
    orden: str
    results: list[OpinionResponse] = []


# =============================================================================
# CATÁLOGOS
# =============================================================================


class EspecialidadCatalogoResponse(BaseModel):
    """Especialidad disponible en el catálogo para autocompletado."""

    nombre: str = Field(..., description="Nombre legible de la especialidad")
    slug: str = Field(..., description="Slug normalizado")
    total_pares: int = Field(
        0, description="Número de combinaciones especialidad-ciudad"
    )


class CiudadCatalogoResponse(BaseModel):
    """Ciudad disponible en el catálogo para autocompletado."""

    nombre: str
    slug: str
    estado: Optional[str] = None
    total_pares: int = 0


class ParCatalogoResponse(BaseModel):
    """Par especialidad-ciudad del catálogo de Doctoralia."""

    especialidad_nombre: Optional[str] = None
    especialidad_slug: str
    ciudad_nombre: Optional[str] = None
    ciudad_slug: str
    modalidad: Optional[str] = None
    url: Optional[str] = None


class EspecialidadesListResponse(BaseModel):
    """Listado de especialidades disponibles."""

    total: int
    especialidades: list[EspecialidadCatalogoResponse]


class CiudadesListResponse(BaseModel):
    """Listado de ciudades disponibles."""

    total: int
    ciudades: list[CiudadCatalogoResponse]


class ParesListResponse(PaginadoBase):
    """Listado paginado de pares especialidad-ciudad."""

    pares: list[ParCatalogoResponse]


# =============================================================================
# CHATBOT
# =============================================================================


class MensajeChat(BaseModel):
    """Mensaje individual en el historial de conversación."""

    role: str = Field(..., description="'user' o 'assistant'")
    content: str


class FiltrosActualesChat(BaseModel):
    """Filtros de búsqueda ya confirmados antes de esta interacción."""

    especialidad: Optional[str] = None
    ciudad: Optional[str] = None
    atiende_ninos: bool = False
    atiende_adultos: bool = True
    atiende_adolescentes: bool = False


class ChatInterpretRequest(BaseModel):
    """
    Request del endpoint de interpretación médica por chatbot.

    Parámetros
    ----------
    messages : list[MensajeChat]
        Historial completo de la conversación (sistema + usuario).
    consulta : str
        Último mensaje del usuario.
    filtros_actuales : FiltrosActualesChat, opcional
        Filtros ya conocidos de turnos previos.
    provider : str
        Proveedor LLM a usar: 'groq', 'gemini' o 'auto'.
    auto_search : bool
        Si True, el endpoint también ejecuta la búsqueda cuando `ready=True`.
    """

    messages: list[MensajeChat] = []
    consulta: str
    filtros_actuales: Optional[FiltrosActualesChat] = None
    provider: str = "groq"
    auto_search: bool = False


class SugerenciaChat(BaseModel):
    """Sugerencia rápida para el usuario en el chat."""

    type: str = Field(
        ..., description="'city' | 'specialty' | 'patient_type' | 'action'"
    )
    label: str
    value: str


class DetectadoChat(BaseModel):
    """Entidades detectadas por el LLM en el mensaje del usuario."""

    especialidad: Optional[str] = None
    especialidad_slug: Optional[str] = None
    ciudad: Optional[str] = None
    ciudad_slug: Optional[str] = None
    tipo_paciente: Optional[str] = None
    atiende_ninos: bool = False
    atiende_adultos: bool = True
    atiende_adolescentes: bool = False
    servicio: Optional[str] = None
    orden: Optional[str] = "puntuacion_desc"
    solo_analizados: bool = True
    solo_con_opiniones: bool = True
    confiabilidad: Optional[str] = None
    sospecha_fraude: Optional[bool] = None
    precio_min: Optional[float] = None
    precio_max: Optional[float] = None


class SafetyChat(BaseModel):
    """Información de seguridad médica detectada por el chatbot."""

    is_emergency: bool = False
    message: Optional[str] = None


class ModeloInfoChat(BaseModel):
    """Información del modelo LLM utilizado en la respuesta."""

    provider: str
    name: str


class ChatInterpretResponse(BaseModel):
    """
    Respuesta del endpoint de interpretación médica.

    Contiene la respuesta en formato de mensajes, filtros SQL/Mongo,
    y sugerencias de próximos pasos.
    """

    mensaje: str
    respuesta: list[str]
    mongo: Optional[Any] = None
    sql: Optional[list[str]] = None
    filtros: Optional[dict[str, Any]] = None
    sugerencias: list[str] = []
    historial_mensajes: Optional[list[Any]] = None
    ready: bool = False
    model: Optional[ModeloInfoChat] = None


class RecomendarRequest(BaseModel):
    """Request del endpoint combinado de interpretación + búsqueda."""

    consulta: str
    provider: str = "auto"
    limit: int = Field(6, ge=1, le=24)


class RecomendarResponse(BaseModel):
    """Respuesta del endpoint `/recomendar` con interpretación y resultados."""

    interpretacion: dict[str, Any]
    results: list[EspecialistaCardResponse] = []


# =============================================================================
# USUARIOS / PERFIL
# =============================================================================


class DireccionResponse(BaseModel):
    """Dirección de usuario registrada en MySQL."""

    id: int
    alias: Optional[str] = None
    calle: Optional[str] = None
    colonia: Optional[str] = None
    municipio_alcaldia: Optional[str] = None
    ciudad: Optional[str] = None
    ciudad_slug: Optional[str] = None
    estado: Optional[str] = None
    pais: Optional[str] = "México"
    codigo_postal: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    es_principal: bool = False


class DireccionCreate(BaseModel):
    """Body para crear una nueva dirección de usuario."""

    alias: Optional[str] = None
    calle: Optional[str] = None
    colonia: Optional[str] = None
    municipio_alcaldia: Optional[str] = None
    ciudad: Optional[str] = None
    ciudad_slug: Optional[str] = None
    estado: Optional[str] = None
    pais: str = "México"
    codigo_postal: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    es_principal: bool = False


class DireccionUpdate(BaseModel):
    """Body para actualizar parcialmente una dirección de usuario."""

    alias: Optional[str] = None
    calle: Optional[str] = None
    colonia: Optional[str] = None
    municipio_alcaldia: Optional[str] = None
    ciudad: Optional[str] = None
    ciudad_slug: Optional[str] = None
    estado: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    es_principal: Optional[bool] = None


class PreferenciasUsuario(BaseModel):
    """Preferencias de búsqueda del usuario (futuro: personalización)."""

    especialidades: list[str] = []
    ciudades: list[str] = []


class UsuarioPerfilResponse(BaseModel):
    """
    Perfil completo del usuario autenticado.

    Incluye datos personales, dirección principal registrada y
    preferencias de búsqueda para personalización futura.
    """

    id: int
    email: str
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    direccion_principal: Optional[DireccionResponse] = None
    preferencias: PreferenciasUsuario = PreferenciasUsuario()


class UsuarioUpdateRequest(BaseModel):
    """Body para actualizar datos básicos del perfil del usuario."""

    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    avatar_url: Optional[str] = None


# =============================================================================
# FAVORITOS
# =============================================================================


class FavoritoCreate(BaseModel):
    """
    Body para agregar un especialista a favoritos.

    Acepta ObjectId de MongoDB o doctoralia_id (o ambos).
    """

    medico_id: Optional[str] = Field(
        None, description="ObjectId de MongoDB del especialista"
    )
    doctoralia_id: Optional[int] = Field(
        None, description="ID de Doctoralia del especialista"
    )


class FavoritoDetalleResponse(BaseModel):
    """
    Favorito con datos completos del especialista para renderizar en el frontend.
    """

    favorito_id: int
    guardado_en: Optional[datetime] = None
    especialista: Optional[EspecialistaCardResponse] = None


class FavoritosListResponse(BaseModel):
    """Listado de favoritos con datos completos de cada especialista."""

    total: int
    favoritos: list[FavoritoDetalleResponse]


# =============================================================================
# HISTORIAL
# =============================================================================


class HistorialCreate(BaseModel):
    """Body para guardar una búsqueda en el historial del usuario."""

    especialidad: Optional[str] = None
    ubicacion: Optional[str] = None
    consulta_texto: Optional[str] = None
    filtros: Optional[dict[str, Any]] = None
    origen: Optional[str] = Field(None, description="'tradicional' | 'chat' | 'home'")
    total_resultados: Optional[int] = None


class HistorialItemResponse(BaseModel):
    """Entrada del historial de búsquedas de un usuario."""

    id: int
    especialidad: Optional[str] = None
    ubicacion: Optional[str] = None
    consulta_texto: Optional[str] = None
    filtros: Optional[dict[str, Any]] = None
    origen: Optional[str] = None
    total_resultados: Optional[int] = None
    fecha: Optional[datetime] = None


class HistorialListResponse(BaseModel):
    """Listado paginado del historial de búsquedas del usuario."""

    total: int
    page: int
    limit: int
    historial: list[HistorialItemResponse]
