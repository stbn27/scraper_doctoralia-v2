from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongo import get_mongo_db
from app.db.mysql import get_mysql_conn
from app.api.especialistas import router as especialistas_router
from app.api.usuarios import router as usuarios_router
from app.api.catalogos import router as catalogos_router
from app.api.chat import router as chat_router

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


@app.get("/")
def root():
    return {"status": "ok", "message": "API Recomendación Médica v2 corriendo"}


@app.get("/health")
def health():
    """Verifica el estado de conexión a MySQL y MongoDB."""
    resultados = {"api": "ok", "mysql": "error", "mongodb": "error"}
    try:
        conn = get_mysql_conn()
        conn.close()
        resultados["mysql"] = "ok"
    except Exception as e:
        resultados["mysql"] = str(e)
    try:
        db = get_mongo_db()
        db.command("ping")
        resultados["mongodb"] = "ok"
    except Exception as e:
        resultados["mongodb"] = str(e)
    return resultados