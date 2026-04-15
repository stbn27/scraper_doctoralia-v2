from fastapi import FastAPI

app = FastAPI(title="API Recomendación Médica v1")

@app.get("/")
def root():
    return {"status": "ok", "message": "API corriendo"}

@app.get("/health")
def health():
    return {"status": "healthy"}