from fastapi import FastAPI
from app.db.mongo import get_mongo_db
from app.db.mysql import get_mysql_conn

app = FastAPI(title="API Recomendación Médica v1")

@app.get("/")
def root():
    return {"status": "ok", "message": "API corriendo"}

@app.get("/health")
def health():
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