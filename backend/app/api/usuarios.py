"""
Router de usuarios, autenticación, favoritos, historial y direcciones.

Endpoints:
- POST /auth/register
- POST /auth/login
- GET  /usuarios/me
- PATCH /usuarios/me
- GET  /usuarios/favoritos
- POST /usuarios/favoritos
- DELETE /usuarios/favoritos/{medico_id}
- GET  /usuarios/historial
- POST /usuarios/historial
- DELETE /usuarios/historial
- GET  /usuarios/direcciones
- POST /usuarios/direcciones
- PATCH /usuarios/direcciones/{id}
- DELETE /usuarios/direcciones/{id}
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.mongo import get_doctoralia_async_db, get_mongo_async_db
from app.db.mysql import get_mysql_conn
from app.db.repositorios import analisis_repo

from app.models.schemas import (
    DireccionCreate,
    DireccionUpdate,
    FavoritoCreate,
    HistorialCreate,
    UsuarioUpdateRequest,
)
from app.models.usuario import TokenResponse, UsuarioCreate, UsuarioLogin
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(tags=["Auth y Usuarios"])


# =============================================================================
# AUTENTICACIÓN
# =============================================================================


@router.post("/auth/register", status_code=201)
def register(data: UsuarioCreate):
    """
    Registra un nuevo usuario en MySQL con rol USER por defecto.

    Al crear el usuario se asigna automáticamente ``rol_id = 1`` (USER).
    Si la tabla ``roles`` aún no existe, el campo se omite para mantener
    compatibilidad con la BD sin la tabla de roles.

    Parámetros
    ----------
    data : UsuarioCreate
        Email y contraseña del nuevo usuario.

    Retorna
    -------
    dict
        Datos básicos del usuario creado: id, email, rol, created_at.

    Excepciones
    -----------
    HTTPException 409
        Si el email ya está registrado.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (data.email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=409, detail="El email ya está registrado")

    hashed = hash_password(data.password)
    # Intentar insertar con rol_id (requiere tabla roles preexistente)
    try:
        cursor.execute(
            """
            INSERT INTO usuarios (email, password_hash, rol_id, nombre, apellido, telefono, avatar_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (data.email, hashed, 1, data.nombre, data.apellido, data.telefono, data.avatar_url),
        )
    except Exception:
        # Fallback: insertar sin rol_id si la columna no existe aún
        cursor.execute(
            """
            INSERT INTO usuarios (email, password_hash, nombre, apellido, telefono, avatar_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (data.email, hashed, data.nombre, data.apellido, data.telefono, data.avatar_url),
        )
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return {
        "id": nuevo_id,
        "email": data.email,
        "nombre": data.nombre,
        "apellido": data.apellido,
        "telefono": data.telefono,
        "avatar_url": data.avatar_url,
        "rol": "USER",
        "created_at": datetime.utcnow(),
    }


@router.post("/auth/login", response_model=TokenResponse)
def login(data: UsuarioLogin):
    """
    Autentica al usuario y retorna un token JWT con el rol incluido.

    El payload del JWT contiene ``sub`` (id) y ``rol`` (nombre del rol del usuario).
    Si la tabla ``roles`` no existe, el rol se omite del token.

    Parámetros
    ----------
    data : UsuarioLogin
        Email y contraseña del usuario.

    Retorna
    -------
    TokenResponse
        Token JWT de acceso y tipo de token.

    Excepciones
    -----------
    HTTPException 401
        Si las credenciales son incorrectas.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)
    # Intentar JOIN con roles para obtener el nombre del rol
    try:
        cursor.execute(
            """
            SELECT u.*, r.nombre AS rol_nombre
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE u.email = %s
            """,
            (data.email,),
        )
        user = cursor.fetchone()
    except Exception:
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (data.email,))
        user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    rol = user.get("rol_nombre") or "USER"
    token = create_access_token({"sub": str(user["id"]), "rol": rol})
    return {"access_token": token, "token_type": "bearer"}


# =============================================================================
# PERFIL
# =============================================================================


@router.get("/usuarios/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """
    Retorna el perfil completo del usuario autenticado incluyendo su rol.

    Realiza JOIN con la tabla ``roles`` para incluir el nombre del rol.
    Si la tabla de roles no existe, devuelve rol ``USER`` por defecto.

    Parámetros
    ----------
    current_user : dict
        Usuario autenticado extraído del JWT.

    Retorna
    -------
    dict
        Perfil completo con dirección principal, preferencias y rol.

    Excepciones
    -----------
    HTTPException 404
        Si el usuario no se encuentra en la base de datos.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT u.id, u.email, u.nombre, u.apellido, u.telefono, u.avatar_url,
                   u.created_at, r.nombre AS rol
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE u.id = %s
            """,
            (current_user["id"],),
        )
    except Exception:
        cursor.execute(
            """
            SELECT id, email, nombre, apellido, telefono, avatar_url, created_at
            FROM usuarios WHERE id = %s
            """,
            (current_user["id"],),
        )

    user = cursor.fetchone()
    if not user:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Asegurar que el campo rol siempre esté presente
    if "rol" not in user or user["rol"] is None:
        user["rol"] = current_user.get("rol") or "USER"

    # Dirección principal
    cursor.execute(
        """
        SELECT id, alias, calle, colonia, municipio_alcaldia, ciudad, ciudad_slug,
               estado, pais, codigo_postal, lat, lng, es_principal
        FROM usuarios_direcciones
        WHERE usuario_id = %s AND es_principal = TRUE
        LIMIT 1
        """,
        (current_user["id"],),
    )
    direccion = cursor.fetchone()
    cursor.close()
    conn.close()

    user["direccion_principal"] = direccion
    user["preferencias"] = {"especialidades": [], "ciudades": []}

    return user


@router.patch("/usuarios/me")
def actualizar_perfil(
    data: UsuarioUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Actualiza datos básicos del perfil del usuario autenticado.

    Parámetros
    ----------
    data : UsuarioUpdateRequest
        Campos a actualizar: nombre, apellido, telefono, avatar_url.
    current_user : dict
        Usuario autenticado.

    Retorna
    -------
    dict
        Mensaje de confirmación y datos actualizados del usuario.
    """
    campos = data.model_dump(exclude_none=True)
    if not campos:
        raise HTTPException(
            status_code=400, detail="No se proporcionaron campos para actualizar"
        )

    set_clause = ", ".join(f"{k} = %s" for k in campos)
    valores = list(campos.values()) + [current_user["id"]]

    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"UPDATE usuarios SET {set_clause} WHERE id = %s", valores)
    conn.commit()

    cursor.execute(
        "SELECT id, email, nombre, apellido, telefono, avatar_url FROM usuarios WHERE id = %s",
        (current_user["id"],),
    )
    usuario_actualizado = cursor.fetchone()
    cursor.close()
    conn.close()

    return {"mensaje": "Perfil actualizado", "usuario": usuario_actualizado}


# =============================================================================
# DIRECCIONES
# =============================================================================


@router.get("/usuarios/direcciones")
def listar_direcciones(current_user: dict = Depends(get_current_user)):
    """
    Lista todas las direcciones del usuario autenticado.

    Parámetros
    ----------
    current_user : dict
        Usuario autenticado.

    Retorna
    -------
    dict
        Total y lista de direcciones del usuario.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, alias, calle, colonia, municipio_alcaldia, ciudad, ciudad_slug,
               estado, pais, codigo_postal, lat, lng, es_principal
        FROM usuarios_direcciones
        WHERE usuario_id = %s
        ORDER BY es_principal DESC, created_at DESC
        """,
        (current_user["id"],),
    )
    direcciones = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"total": len(direcciones), "direcciones": direcciones}


@router.post("/usuarios/direcciones", status_code=201)
def crear_direccion(
    data: DireccionCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Crea una nueva dirección para el usuario autenticado.

    Si `es_principal` es True, desmarca las demás direcciones como no principales.

    Parámetros
    ----------
    data : DireccionCreate
        Datos de la nueva dirección.
    current_user : dict
        Usuario autenticado.

    Retorna
    -------
    dict
        Dirección creada con su ID asignado.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    if data.es_principal:
        cursor.execute(
            "UPDATE usuarios_direcciones SET es_principal = FALSE WHERE usuario_id = %s",
            (current_user["id"],),
        )

    cursor.execute(
        """
        INSERT INTO usuarios_direcciones
        (usuario_id, alias, calle, colonia, municipio_alcaldia, ciudad, ciudad_slug,
         estado, pais, codigo_postal, lat, lng, es_principal)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            current_user["id"],
            data.alias,
            data.calle,
            data.colonia,
            data.municipio_alcaldia,
            data.ciudad,
            data.ciudad_slug,
            data.estado,
            data.pais,
            data.codigo_postal,
            data.lat,
            data.lng,
            data.es_principal,
        ),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid

    cursor.execute("SELECT * FROM usuarios_direcciones WHERE id = %s", (nuevo_id,))
    nueva = cursor.fetchone()
    cursor.close()
    conn.close()
    return nueva


@router.patch("/usuarios/direcciones/{direccion_id}")
def actualizar_direccion(
    direccion_id: int,
    data: DireccionUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    Actualiza parcialmente una dirección del usuario.

    Parámetros
    ----------
    direccion_id : int
        ID de la dirección a actualizar.
    data : DireccionUpdate
        Campos a actualizar.
    current_user : dict
        Usuario autenticado.

    Retorna
    -------
    dict
        Dirección actualizada.

    Excepciones
    -----------
    HTTPException 404
        Si la dirección no existe o no pertenece al usuario.
    """
    campos = data.model_dump(exclude_none=True)
    if not campos:
        raise HTTPException(
            status_code=400, detail="No se proporcionaron campos para actualizar"
        )

    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    # Verificar propiedad
    cursor.execute(
        "SELECT id FROM usuarios_direcciones WHERE id = %s AND usuario_id = %s",
        (direccion_id, current_user["id"]),
    )
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Dirección no encontrada")

    if campos.get("es_principal"):
        cursor.execute(
            "UPDATE usuarios_direcciones SET es_principal = FALSE WHERE usuario_id = %s",
            (current_user["id"],),
        )

    set_clause = ", ".join(f"{k} = %s" for k in campos)
    valores = list(campos.values()) + [direccion_id, current_user["id"]]
    cursor.execute(
        f"UPDATE usuarios_direcciones SET {set_clause} WHERE id = %s AND usuario_id = %s",
        valores,
    )
    conn.commit()

    cursor.execute("SELECT * FROM usuarios_direcciones WHERE id = %s", (direccion_id,))
    actualizada = cursor.fetchone()
    cursor.close()
    conn.close()
    return actualizada


@router.delete("/usuarios/direcciones/{direccion_id}", status_code=204)
def eliminar_direccion(
    direccion_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    Elimina una dirección del usuario.

    Parámetros
    ----------
    direccion_id : int
        ID de la dirección a eliminar.
    current_user : dict
        Usuario autenticado.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM usuarios_direcciones WHERE id = %s AND usuario_id = %s",
        (direccion_id, current_user["id"]),
    )
    conn.commit()
    cursor.close()
    conn.close()


# =============================================================================
# FAVORITOS
# =============================================================================


@router.post("/usuarios/favoritos", status_code=201)
async def agregar_favorito(
    data: FavoritoCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Agrega un especialista a favoritos del usuario autenticado.

    Acepta ObjectId de MongoDB (`medico_id`) o ID de Doctoralia (`doctoralia_id`).
    Si solo se recibe `doctoralia_id`, busca el ObjectId en MongoDB.
    Evita duplicados por usuario + medico_id.

    Parámetros
    ----------
    data : FavoritoCreate
        medico_id (ObjectId) y/o doctoralia_id del especialista.
    current_user : dict
        Usuario autenticado.

    Retorna
    -------
    dict
        Datos del favorito creado.

    Excepciones
    -----------
    HTTPException 400
        Si no se proporciona ningún identificador.
    HTTPException 404
        Si no se encuentra el especialista en MongoDB.
    HTTPException 409
        Si ya está en favoritos.
    """
    medico_id = data.medico_id
    doctoralia_id = data.doctoralia_id

    if not medico_id and not doctoralia_id:
        raise HTTPException(
            status_code=400, detail="Debes proporcionar medico_id o doctoralia_id"
        )

    # Resolver medico_id desde MongoDB si solo viene doctoralia_id
    if not medico_id and doctoralia_id:
        db = get_doctoralia_async_db()
        col = db["doctor_profiles"]
        esp = await col.find_one({"doctor.id_doctoralia": doctoralia_id}, {"_id": 1})
        if not esp:
            raise HTTPException(
                status_code=404, detail="Especialista no encontrado en MongoDB"
            )
        medico_id = str(esp["_id"])

    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    # Verificar duplicado
    cursor.execute(
        "SELECT id FROM favoritos WHERE usuario_id = %s AND medico_id = %s",
        (current_user["id"], medico_id),
    )
    existente = cursor.fetchone()
    if existente:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=409, detail="El especialista ya está en favoritos"
        )

    cursor.execute(
        "INSERT INTO favoritos (usuario_id, medico_id, doctoralia_id) VALUES (%s, %s, %s)",
        (current_user["id"], medico_id, doctoralia_id),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid

    cursor.execute(
        "SELECT id, medico_id, doctoralia_id, guardado_en FROM favoritos WHERE id = %s",
        (nuevo_id,),
    )
    fav = cursor.fetchone()
    cursor.close()
    conn.close()

    return {
        "mensaje": "Especialista agregado a favoritos",
        "favorito": {
            "id": fav["id"],
            "medico_id": fav["medico_id"],
            "doctoralia_id": fav["doctoralia_id"],
            "guardado_en": fav["guardado_en"],
        },
    }


@router.get("/usuarios/favoritos")
async def listar_favoritos(current_user: dict = Depends(get_current_user)):
    """
    Lista los favoritos del usuario con datos completos de cada especialista.

    Obtiene los registros de favoritos de MySQL y enriquece cada uno con datos
    del especialista desde MongoDB y su análisis IA.

    Parámetros
    ----------
    current_user : dict
        Usuario autenticado.

    Retorna
    -------
    dict
        Total y lista de favoritos con datos completos del especialista.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, medico_id, doctoralia_id, guardado_en
        FROM favoritos
        WHERE usuario_id = %s
        ORDER BY guardado_en DESC
        """,
        (current_user["id"],),
    )
    favoritos_mysql = cursor.fetchall()
    cursor.close()
    conn.close()

    if not favoritos_mysql:
        return {"total": 0, "favoritos": []}

    # Batch fetch de especialistas desde MongoDB
    # pyrefly: ignore [missing-import]
    from bson import ObjectId

    db = get_doctoralia_async_db()
    col_esp = db["doctor_profiles"]

    ids_mongo = []
    for fav in favoritos_mysql:
        mid = fav["medico_id"]
        try:
            ids_mongo.append(ObjectId(mid))
        except Exception:
            pass
        ids_mongo.append(mid)

    mapa_especialistas: dict = {}
    if ids_mongo:
        cursor_mongo = col_esp.find({"_id": {"$in": ids_mongo}})
        async for doc in cursor_mongo:
            mapa_especialistas[str(doc["_id"])] = doc

    # Obtener análisis en batch
    doctoralia_ids = [
        fav["doctoralia_id"] for fav in favoritos_mysql if fav.get("doctoralia_id")
    ]
    mapa_analisis = (
        await analisis_repo.obtener_por_doctoralia_ids(doctoralia_ids)
        if doctoralia_ids
        else {}
    )

    # Construir respuesta
    favoritos_response = []
    for fav in favoritos_mysql:
        esp_doc = mapa_especialistas.get(fav["medico_id"])
        if not esp_doc:
            favoritos_response.append(
                {
                    "favorito_id": fav["id"],
                    "guardado_en": fav["guardado_en"],
                    "especialista": None,
                }
            )
            continue

        esp_id = str(esp_doc["_id"])
        doctor_info = esp_doc.get("doctor") or {}
        did = doctor_info.get("id_doctoralia") or esp_doc.get("doctoralia_id")
        analisis_doc = mapa_analisis.get(did) if did else None

        # Importar aquí para evitar circular
        from app.services.busqueda_service import _construir_card, _serializar_id

        card = _construir_card(_serializar_id(dict(esp_doc)), analisis_doc)

        favoritos_response.append(
            {
                "favorito_id": fav["id"],
                "guardado_en": fav["guardado_en"],
                "especialista": card,
            }
        )

    return {"total": len(favoritos_response), "favoritos": favoritos_response}


@router.delete("/usuarios/favoritos/{medico_id}", status_code=200)
def eliminar_favorito(medico_id: str, current_user: dict = Depends(get_current_user)):
    """
    Elimina un favorito por ObjectId del especialista.

    Parámetros
    ----------
    medico_id : str
        ObjectId de MongoDB del especialista a eliminar de favoritos.
    current_user : dict
        Usuario autenticado.

    Retorna
    -------
    dict
        Mensaje de confirmación.

    Excepciones
    -----------
    HTTPException 404
        Si el favorito no existe.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM favoritos WHERE usuario_id = %s AND medico_id = %s",
        (current_user["id"], medico_id),
    )
    conn.commit()
    eliminados = cursor.rowcount
    cursor.close()
    conn.close()

    if eliminados == 0:
        raise HTTPException(status_code=404, detail="Favorito no encontrado")

    return {"mensaje": "Especialista eliminado de favoritos"}


# =============================================================================
# HISTORIAL
# =============================================================================


@router.get("/usuarios/historial")
def listar_historial(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Lista el historial de búsquedas del usuario autenticado con paginación.

    Parámetros
    ----------
    current_user : dict
        Usuario autenticado.
    page : int
        Página actual. Por defecto 1.
    limit : int
        Registros por página. Por defecto 20.

    Retorna
    -------
    dict
        Total, paginación y lista de búsquedas del historial.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT COUNT(*) as total FROM historial_busquedas WHERE usuario_id = %s",
        (current_user["id"],),
    )
    total = cursor.fetchone()["total"]

    offset = (page - 1) * limit
    cursor.execute(
        """
        SELECT id, especialidad, ubicacion, consulta_texto, filtros_json,
               origen, total_resultados, fecha
        FROM historial_busquedas
        WHERE usuario_id = %s
        ORDER BY fecha DESC
        LIMIT %s OFFSET %s
        """,
        (current_user["id"], limit, offset),
    )
    historial = cursor.fetchall()
    cursor.close()
    conn.close()

    # Parsear filtros_json si es string
    for item in historial:
        if isinstance(item.get("filtros_json"), str):
            try:
                item["filtros"] = json.loads(item["filtros_json"])
            except Exception:
                item["filtros"] = None
        else:
            item["filtros"] = item.get("filtros_json")
        item.pop("filtros_json", None)

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "historial": historial,
    }


@router.post("/usuarios/historial", status_code=201)
def guardar_historial(
    data: HistorialCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Guarda una búsqueda en el historial del usuario.

    Parámetros
    ----------
    data : HistorialCreate
        Datos de la búsqueda: especialidad, ubicación, texto, filtros, origen.
    current_user : dict
        Usuario autenticado.

    Retorna
    -------
    dict
        Mensaje de confirmación e ID del registro creado.
    """
    filtros_json = json.dumps(data.filtros) if data.filtros else None

    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO historial_busquedas
        (usuario_id, especialidad, ubicacion, consulta_texto, filtros_json, origen, total_resultados)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            current_user["id"],
            data.especialidad,
            data.ubicacion,
            data.consulta_texto,
            filtros_json,
            data.origen,
            data.total_resultados,
        ),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return {"mensaje": "Búsqueda guardada en el historial", "id": nuevo_id}


@router.delete("/usuarios/historial", status_code=200)
def limpiar_historial(current_user: dict = Depends(get_current_user)):
    """
    Elimina todo el historial de búsquedas del usuario autenticado.

    Parámetros
    ----------
    current_user : dict
        Usuario autenticado.

    Retorna
    -------
    dict
        Mensaje de confirmación con cantidad de registros eliminados.
    """
    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM historial_busquedas WHERE usuario_id = %s",
        (current_user["id"],),
    )
    conn.commit()
    eliminados = cursor.rowcount
    cursor.close()
    conn.close()
    return {"mensaje": f"Historial eliminado ({eliminados} registros)"}
