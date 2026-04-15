from fastapi import APIRouter, HTTPException, Depends, status
from app.db.mysql import get_mysql_conn
from app.models.usuario import (
    UsuarioCreate,
    UsuarioResponse,
    UsuarioLogin,
    TokenResponse,
    Favorito,
    FavoritoResponse,
)
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from datetime import datetime

router = APIRouter(tags=["Auth y Usuarios"])


# REGISTER
@router.post("/auth/register", response_model=UsuarioResponse, status_code=201)
def register(data: UsuarioCreate):
    """
    Registra un nuevo usuario en la base de datos MySQL. Se verifica que el email no esté ya registrado para evitar duplicados. La contraseña
    se almacena de forma segura utilizando hashing. Se retorna la información del usuario creado, incluyendo su ID, email y fecha de creación.
    - data: un objeto UsuarioCreate que contiene el email y la contraseña del nuevo usuario.
    - Retorna: un objeto UsuarioResponse con la información del usuario creado, incluyendo su ID, email y fecha de creación.
    - Errores: devuelve un error 409 si el email ya está registrado, y un error 400 si los datos proporcionados son inválidos.
    """

    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (data.email,))
    if cursor.fetchone():
        raise HTTPException(status_code=409, detail="El email ya está registrado")

    hashed = hash_password(data.password)
    cursor.execute(
        "INSERT INTO usuarios (email, password_hash) VALUES (%s, %s)",
        (data.email, hashed),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return {"id": nuevo_id, "email": data.email, "created_at": datetime.utcnow()}


# LOGIN
@router.post("/auth/login", response_model=TokenResponse)
def login(data: UsuarioLogin):
    """
    Autentica a un usuario utilizando su email y contraseña. Se verifica que el email exista en la base de datos y que la contraseña proporcionada
    coincida con el hash almacenado. Si la autenticación es exitosa, se genera un token JWT que el usuario puede usar para acceder a rutas protegidas.
    - data: un objeto UsuarioLogin que contiene el email y la contraseña del usuario que intenta autenticarse.
    - Retorna: un objeto TokenResponse que contiene el token de acceso JWT y el tipo de token.
    - Errores: devuelve un error 401 si las credenciales son incorrectas o si el usuario no existe, y un error 400 si los datos proporcionados son inválidos.
    """

    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (data.email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
        )

    token = create_access_token({"sub": str(user["id"])})
    return {"access_token": token, "token_type": "bearer"}


# PERFIL PROPIO
@router.get("/usuarios/me", response_model=UsuarioResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """
    Obtiene la información del usuario autenticado utilizando el token JWT proporcionado en la solicitud. Se verifica que el token sea válido y no haya expirado.
    Si la autenticación es exitosa, se retorna la información del usuario, incluyendo su ID, email y fecha de creación.
    - current_user: un diccionario que contiene la información del usuario autenticado, obtenido a través de la función get_current_user que decodifica el token JWT.
    - Retorna: un objeto UsuarioResponse con la información del usuario autenticado, incluyendo su ID, email y fecha de creación.
    - Errores: devuelve un error 401 si el token es inválido o ha expirado, y un error 404 si el usuario no se encuentra en la base de datos.
    """

    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT id, email, created_at FROM usuarios WHERE id = %s",
        (current_user["id"],),
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


# FAVORITOS: AGREGAR
@router.post("/usuarios/favoritos", status_code=201)
def agregar_favorito(data: Favorito, current_user: dict = Depends(get_current_user)):
    """
    Agrega un médico a la lista de favoritos del usuario autenticado. Se verifica que el médico no esté ya en la lista de favoritos para evitar duplicados.
    Si la operación es exitosa, se retorna un mensaje de confirmación.
    - data: un objeto Favorito que contiene el ID del médico que se desea agregar a favoritos.
    - current_user: un diccionario que contiene la información del usuario autenticado, obtenido a través de la función get_current_user que decodifica el token JWT.
    - Retorna: un mensaje de confirmación indicando que el médico ha sido agregado a favoritos.
    - Errores: devuelve un error 409 si el médico ya está en favoritos, un error 401 si el token es inválido o ha expirado, y un error 400 si los datos proporcionados son inválidos.
    """

    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "INSERT INTO favoritos (usuario_id, medico_id) VALUES (%s, %s)",
            (current_user["id"], data.medico_id),
        )
        conn.commit()
    except Exception:
        raise HTTPException(status_code=409, detail="Ya está en favoritos")
    finally:
        cursor.close()
        conn.close()

    return {"mensaje": "Agregado a favoritos"}


# FAVORITOS: LISTAR
@router.get("/usuarios/favoritos", response_model=list[FavoritoResponse])
def listar_favoritos(current_user: dict = Depends(get_current_user)):
    """
    Obtiene la lista de médicos favoritos del usuario autenticado. Se verifica que el token JWT sea válido y no haya expirado. Si la autenticación es exitosa,
    se retorna una lista de objetos FavoritoResponse que contienen el ID del médico y la fecha en que fue agregado a favoritos, ordenados por fecha de adición de forma descendente.
    - current_user: un diccionario que contiene la información del usuario autenticado, obtenido a través de la función get_current_user que decodifica el token JWT.
    - Retorna: una lista de objetos FavoritoResponse que contienen el ID del médico y la fecha en que fue agregado a favoritos, ordenados por fecha de adición de forma descendente.
    - Errores: devuelve un error 401 si el token es inválido o ha expirado, y un error 400 si los datos proporcionados son inválidos.
    """

    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT id, medico_id, guardado_en FROM favoritos WHERE usuario_id = %s ORDER BY guardado_en DESC",
        (current_user["id"],),
    )
    favoritos = cursor.fetchall()
    cursor.close()
    conn.close()

    return favoritos


# FAVORITOS: ELIMINAR
@router.delete("/usuarios/favoritos/{medico_id}", status_code=204)
def eliminar_favorito(medico_id: str, current_user: dict = Depends(get_current_user)):
    """
    Elimina un médico de la lista de favoritos del usuario autenticado. Se verifica que el token JWT sea válido y no haya expirado. Si la autenticación
    es exitosa, se elimina el médico de favoritos y se retorna un mensaje de confirmación.
    - medico_id: el ID del médico que se desea eliminar de favoritos.
    - current_user: un diccionario que contiene la información del usuario autenticado, obtenido a través de la función get_current_user que decodifica el token JWT.
    - Retorna: un mensaje de confirmación indicando que el médico ha sido eliminado de favoritos.
    - Errores: devuelve un error 401 si el token es inválido o ha expirado, un error 404 si el médico no se encuentra en favoritos, y un error 400 si los datos proporcionados son inválidos.
    """

    conn = get_mysql_conn()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM favoritos WHERE usuario_id = %s AND medico_id = %s",
        (current_user["id"], medico_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


# HISTORIAL: GUARDAR
@router.post("/usuarios/historial", status_code=201)
def guardar_historial(
    especialidad: str, ubicacion: str, current_user: dict = Depends(get_current_user)
):
    """
    Guarda una búsqueda realizada por el usuario autenticado en su historial de búsquedas. Se verifica que el token JWT sea válido y no haya expirado. Si la autenticación es exitosa, se almacena la búsqueda en la base de datos MySQL con la especialidad, ubicación y fecha de la búsqueda, y se retorna un mensaje de confirmación.
    - especialidad: la especialidad médica que el usuario buscó.
    - ubicacion: la ubicación que el usuario buscó.
    - current_user: un diccionario que contiene la información del usuario autenticado, obtenido a través de la función get_current_user que decodifica el token JWT.
    - Retorna: un mensaje de confirmación indicando que la búsqueda ha sido guardada en el historial.
    - Errores: devuelve un error 401 si el token es inválido o ha expirado, y un error 400 si los datos proporcionados son inválidos.
    """

    conn = get_mysql_conn()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO historial_busquedas (usuario_id, especialidad, ubicacion) VALUES (%s, %s, %s)",
        (current_user["id"], especialidad, ubicacion),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"mensaje": "Búsqueda guardada"}


# HISTORIAL: LISTAR
@router.get("/usuarios/historial")
def listar_historial(current_user: dict = Depends(get_current_user)):
    """
    Obtiene el historial de búsquedas del usuario autenticado. Se verifica que el token JWT sea válido y no haya expirado. Si la autenticación es exitosa,
    se retorna una lista de objetos que contienen la especialidad, ubicación y fecha de cada búsqueda realizada por el usuario, ordenados por fecha de búsqueda de forma descendente.
    - current_user: un diccionario que contiene la información del usuario autenticado, obtenido a través de la función get_current_user que decodifica el token JWT.
    - Retorna: una lista de objetos que contienen la especialidad, ubicación y fecha de cada búsqueda realizada por el usuario, ordenados por fecha de búsqueda de forma descendente.
    - Errores: devuelve un error 401 si el token es inválido o ha expirado, y un error 400 si los datos proporcionados son inválidos.
    """

    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT id, especialidad, ubicacion, fecha FROM historial_busquedas WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 20",
        (current_user["id"],),
    )
    historial = cursor.fetchall()
    cursor.close()
    conn.close()

    return historial
