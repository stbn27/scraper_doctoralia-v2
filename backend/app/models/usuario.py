from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UsuarioCreate(BaseModel):
    """ "
    Representa los datos necesarios para crear un nuevo usuario. Esta información se recibe a través de
    la API cuando un nuevo usuario se registra.
    - email: la dirección de correo electrónico del usuario, que se utilizará para iniciar sesión y para la comunicación.
    - password: la contraseña del usuario, que se almacenará de forma segura (hashing) en la base de datos.
    """

    email: EmailStr
    password: str


class UsuarioResponse(BaseModel):
    """ "
    Representa la información de un usuario que se devuelve a través de la API, por ejemplo, después de iniciar
    sesión o al consultar su perfil.
    - id: un identificador único para el usuario (puede ser generado por la base de datos).
    - email: la dirección de correo electrónico del usuario.
    - created_at: la fecha y hora en que se creó el usuario, para referencia.
    """

    id: int
    email: str
    created_at: Optional[datetime] = None


class UsuarioLogin(BaseModel):
    """ "
    Representa los datos necesarios para que un usuario inicie sesión. Esta información se recibe a través de
    la API cuando un usuario intenta autenticarse.
    - email: la dirección de correo electrónico del usuario, que se utilizará para identificarlo en el sistema.
    - password: la contraseña del usuario, que se verificará contra la información almacenada en la base de datos para permitir el acceso.
    """

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """ "
    Representa la respuesta que se devuelve a través de la API después de que un usuario inicia sesión correctamente.
    - access_token: el token de acceso generado para el usuario, que se utilizará para autenticar futuras solicitudes a la API.
    - token_type: el tipo de token, que generalmente es "bearer" para indicar que es un token de portador.
    """

    access_token: str
    token_type: str = "bearer"


class Favorito(BaseModel):
    """ "
    Representa la información necesaria para que un usuario pueda marcar a un especialista como favorito. Esta
    información se recibe a través de la API cuando un usuario agrega un especialista a su lista de favoritos.
    - medico_id: el identificador único del especialista que se desea marcar como favorito.
    """

    medico_id: str


class FavoritoResponse(BaseModel):
    """ "
    Representa la información de un especialista marcado como favorito por un usuario, que se devuelve a través de la API.
    - id: un identificador único para el favorito (puede ser generado por la base de datos).
    - medico_id: el identificador único del especialista que ha sido marcado como favorito.
    - guardado_en: la fecha y hora en que el especialista fue marcado como favorito, para referencia.
    """

    id: int
    medico_id: str
    guardado_en: Optional[datetime] = None
