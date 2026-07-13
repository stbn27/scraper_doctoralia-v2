# pyrefly: ignore [missing-import]
from fastapi import FastAPI

from pathlib import Path
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env local
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongo import get_mongo_db, get_doctoralia_db
from app.db.mysql import get_mysql_conn
from app.api.especialistas import router as especialistas_router
from app.api.usuarios import router as usuarios_router
from app.api.catalogos import router as catalogos_router
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from app.api.llm_tokens import router as llm_tokens_router
from app.api.avanzada import router as avanzada_router

app = FastAPI(
    title="API Recomendación Médica v2",
    description="Plataforma de búsqueda y recomendación de especialistas médicos con IA",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(especialistas_router)
app.include_router(usuarios_router)
app.include_router(catalogos_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(llm_tokens_router)
app.include_router(avanzada_router)


@app.get("/")
def root():
    return {"status": "ok", "message": "API Recomendación Médica v2 corriendo"}


@app.get("/health")
def health():
    """Verifica el estado de conexión a MySQL, MongoDB legacy y BD Doctoralia."""
    resultados = {
        "api": "ok",
        "mysql": "error",
        "mongodb_legacy": "error",
        "mongodb_doctoralia": "error",
    }
    try:
        conn = get_mysql_conn()
        conn.close()
        resultados["mysql"] = "ok"
    except Exception as e:
        resultados["mysql"] = str(e)
    try:
        db = get_mongo_db()
        db.command("ping")
        resultados["mongodb_legacy"] = "ok"
    except Exception as e:
        resultados["mongodb_legacy"] = str(e)
    try:
        db2 = get_doctoralia_db()
        db2.command("ping")
        resultados["mongodb_doctoralia"] = "ok"
    except Exception as e:
        resultados["mongodb_doctoralia"] = str(e)
    return resultados


# pyrefly: ignore [missing-import]
from fastapi.exceptions import RequestValidationError

# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse

# pyrefly: ignore [missing-import]
from fastapi import Request


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler global para traducir mensajes de error de validación de Pydantic al español.
    """
    errores_traducidos = []
    for err in exc.errors():
        tipo = err.get("type")
        msg = err.get("msg")
        loc = err.get("loc")
        ctx = err.get("ctx", {})
        val_input = err.get("input")

        # Traducciones comunes de tipos de error de Pydantic v2
        if tipo == "less_than_equal":
            le = ctx.get("le")
            msg = f"El valor debe ser menor o igual a {le}"
        elif tipo == "greater_than_equal":
            ge = ctx.get("ge")
            msg = f"El valor debe ser mayor o igual a {ge}"
        elif tipo == "less_than":
            lt = ctx.get("lt")
            msg = f"El valor debe ser menor a {lt}"
        elif tipo == "greater_than":
            gt = ctx.get("gt")
            msg = f"El valor debe ser mayor a {gt}"
        elif tipo in ("missing", "value_error.missing"):
            msg = "Este campo es obligatorio"
        elif tipo == "string_too_short":
            min_len = ctx.get("min_length")
            msg = f"El texto debe tener al menos {min_len} caracteres"
        elif tipo == "string_too_long":
            max_len = ctx.get("max_length")
            msg = f"El texto debe tener como máximo {max_len} caracteres"
        elif tipo in ("integer_parsing", "int_parsing"):
            msg = "El valor debe ser un número entero válido"
        elif tipo in ("float_parsing", "decimal_parsing"):
            msg = "El valor debe ser un número decimal válido"
        elif tipo in ("bool_parsing", "boolean_parsing"):
            msg = "El valor debe ser un valor booleano válido"
        elif tipo == "json_invalid":
            msg = "JSON no válido"
        # Fallback genérico de substrings en inglés
        elif msg and "should be less than or equal to" in msg:
            val = msg.split("to")[-1].strip()
            msg = f"El valor debe ser menor o igual a {val}"
        elif msg and "should be greater than or equal to" in msg:
            val = msg.split("to")[-1].strip()
            msg = f"El valor debe ser mayor o igual a {val}"

        errores_traducidos.append(
            {"type": tipo, "loc": loc, "msg": msg, "input": val_input, "ctx": ctx}
        )

    return JSONResponse(status_code=422, content={"detail": errores_traducidos})
