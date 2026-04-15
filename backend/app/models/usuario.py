from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str

class UsuarioResponse(BaseModel):
    id: int
    email: str
    created_at: Optional[datetime] = None

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class Favorito(BaseModel):
    medico_id: str

class FavoritoResponse(BaseModel):
    id: int
    medico_id: str
    guardado_en: Optional[datetime] = None