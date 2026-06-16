# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException

# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from typing import List, Optional
from app.db.mysql import get_mysql_conn
from app.security import get_current_user

router = APIRouter(prefix="/usuarios/me/tokens", tags=["Tokens LLM"])


class TokenLLMBase(BaseModel):
    modelo: str
    token: str


class TokenLLMResponse(BaseModel):
    id: int
    modelo: str
    token: str


@router.get("", response_model=List[TokenLLMResponse])
def listar_tokens(current_user: dict = Depends(get_current_user)):
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, modelo, token FROM tokens_llm WHERE usuario_id = %s",
        (current_user["id"],),
    )
    tokens = cursor.fetchall()
    cursor.close()
    conn.close()
    return tokens


@router.post("", response_model=TokenLLMResponse)
def guardar_token(data: TokenLLMBase, current_user: dict = Depends(get_current_user)):
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    # Check if the token already exists for the user and model
    cursor.execute(
        "SELECT id FROM tokens_llm WHERE usuario_id = %s AND modelo = %s",
        (current_user["id"], data.modelo),
    )
    existente = cursor.fetchone()

    try:
        if existente:
            cursor.execute(
                "UPDATE tokens_llm SET token = %s WHERE id = %s",
                (data.token, existente["id"]),
            )
            token_id = existente["id"]
        else:
            # Note: If `modelo` is globally UNIQUE in the DB schema, this will fail if another user has the same model.
            # Assuming the schema intended UNIQUE(usuario_id, modelo). If it fails due to UNIQUE constraint, catch it.
            cursor.execute(
                "INSERT INTO tokens_llm (usuario_id, modelo, token) VALUES (%s, %s, %s)",
                (current_user["id"], data.modelo, data.token),
            )
            token_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

    cursor.execute(
        "SELECT id, modelo, token FROM tokens_llm WHERE id = %s", (token_id,)
    )
    token_db = cursor.fetchone()
    cursor.close()
    conn.close()
    return token_db


@router.delete("/{modelo}")
def eliminar_token(modelo: str, current_user: dict = Depends(get_current_user)):
    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM tokens_llm WHERE usuario_id = %s AND modelo = %s",
        (current_user["id"], modelo),
    )
    conn.commit()
    eliminados = cursor.rowcount
    cursor.close()
    conn.close()

    if eliminados == 0:
        raise HTTPException(status_code=404, detail="Token no encontrado")

    return {"mensaje": f"Token para {modelo} eliminado"}
