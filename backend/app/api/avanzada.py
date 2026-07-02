# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException

# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import asyncio
import hashlib
import json
import os
import re

# pyrefly: ignore [missing-import]
import httpx

from app.db.mongo import get_doctoralia_async_db, get_mongo_db
from app.db.mysql import get_mysql_conn
from app.security import get_current_user

router = APIRouter(prefix="/especialistas/avanzada", tags=["Búsqueda Avanzada"])

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class AvanzadaRequest(BaseModel):
    url: str
    max_opinions: int = 30
    scrape_only: bool = True
    analyze: bool = False
    model: Optional[str] = None
    ollama_model: Optional[str] = None  # Modelo específico de Ollama si aplica


def _extraer_doctor_id_de_html(html: str) -> int | None:
    """
    Intenta extraer el ID numérico de Doctoralia desde el HTML del perfil.
    Prueba múltiples estrategias: JSON-LD, data attributes y patrones JS.

    Args:
        html: HTML crudo del perfil de Doctoralia.

    Returns:
        ID numérico del doctor, o None si no se pudo extraer.
    """
    # Estrategia 1: JSON-LD con @type Doctor o Physician
    ld_blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    for block in ld_blocks:
        try:
            data = json.loads(block)
            # puede ser una lista
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "@graph" in data:
                items = data["@graph"]
            else:
                items = [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") in ("Physician", "Doctor", "Person", "MedicalBusiness"):
                    url_item = item.get("url", item.get("@id", ""))
                    m = re.search(r'/(\d+)(?:[/?#]|$)', url_item)
                    if m:
                        return int(m.group(1))
        except Exception:
            pass

    # Estrategia 2: data-doctor-id / data-user-id en cualquier tag HTML
    m = re.search(r'data-doctor-id=["\']?(\d+)["\']?', html)
    if m:
        return int(m.group(1))

    m = re.search(r'data-user-id=["\']?(\d+)["\']?', html)
    if m:
        return int(m.group(1))

    # Estrategia 3: variable JS con el ID del doctor
    patterns = [
        r'"doctor_id"\s*:\s*(\d+)',
        r'"userId"\s*:\s*(\d+)',
        r'"docId"\s*:\s*(\d+)',
        r"doctorId[\s:=]+(\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            return int(m.group(1))

    return None


def _doctor_id_sintetico_desde_url(url: str) -> int:
    """
    Genera un ID entero estable a partir de la URL usando los últimos 8 dígitos
    de su hash MD5. Sirve como fallback cuando no se puede extraer el ID real.

    Args:
        url: URL del perfil de Doctoralia.

    Returns:
        Entero positivo reproducible para esa URL.
    """
    digest = hashlib.md5(url.encode()).hexdigest()
    return int(digest[:8], 16)  # máx ~4.29 mil millones, suficiente para colisiones bajas


@router.get("/ollama-status")
async def ollama_status():
    """
    Verifica si Ollama está disponible localmente y devuelve los modelos instalados.

    Returns:
        Objeto con {disponible: bool, modelos: list[str], url: str}
    """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            modelos = [m["name"] for m in data.get("models", [])]
            return {"disponible": True, "modelos": modelos, "url": OLLAMA_BASE_URL}
    except Exception:
        return {"disponible": False, "modelos": [], "url": OLLAMA_BASE_URL}


@router.post("/scrape-analyze")
async def scrape_analyze(
    data: AvanzadaRequest, current_user: dict = Depends(get_current_user)
):
    if "doctoralia.com" not in data.url:
        raise HTTPException(
            status_code=400, detail="URL inválida. Debe ser un perfil de Doctoralia."
        )

    # 1. Validar Token si se requiere análisis
    token_str = None
    if data.analyze:
        if not data.model:
            raise HTTPException(
                status_code=400,
                detail="El modelo es requerido para realizar el análisis.",
            )

        conn = get_mysql_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT token FROM tokens_llm WHERE usuario_id = %s AND modelo = %s",
            (current_user["id"], data.model),
        )
        token_db = cursor.fetchone()
        cursor.close()
        conn.close()

        if not token_db or not token_db["token"]:
            raise HTTPException(
                status_code=400,
                detail=f"No tienes token configurado para el modelo {data.model}.",
            )
        token_str = token_db["token"]

    # 2. Scraping del Perfil
    from app.scraper.doctoralia import fetch_and_parse_profile_async
    import httpx as _httpx_scraper

    try:
        # Descargar HTML antes de parsear para poder extraer el ID
        from app.scraper.utils.base import get_user_agent
        _headers = {
            "User-Agent": get_user_agent(),
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        async with _httpx_scraper.AsyncClient(timeout=30, follow_redirects=True) as _cli:
            _resp = await _cli.get(data.url, headers=_headers)
            _resp.raise_for_status()
            _html_raw = _resp.text

        profile = await fetch_and_parse_profile_async(data.url)

        # Intentar extraer el ID real desde el HTML descargado
        doctor_id = profile.get("doctor", {}).get("id_doctoralia")
        if not doctor_id:
            doctor_id = _extraer_doctor_id_de_html(_html_raw)

        # Si aún no hay ID, generar uno sintético reproducible desde la URL
        if not doctor_id:
            doctor_id = _doctor_id_sintetico_desde_url(data.url)
            profile["doctor"]["id_doctoralia"] = doctor_id
            profile["_id"] = f"doctor:{doctor_id}"
        else:
            profile["doctor"]["id_doctoralia"] = doctor_id
            profile["_id"] = f"doctor:{doctor_id}"

    except _httpx_scraper.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"Error HTTP al obtener el perfil ({e.response.status_code}): {data.url}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar el perfil: {e}")

    # 3. Guardar Perfil en MongoDB
    db_async = get_doctoralia_async_db()
    col_profiles = db_async["doctor_profiles"]

    # Asignar un scraping_meta mínimo si no existe
    if "scraping_meta" not in profile:
        profile["scraping_meta"] = {
            "url_origen": data.url,
            "fecha_consulta": datetime.now(timezone.utc).isoformat(),
        }

    await col_profiles.update_one(
        {"doctor.id_doctoralia": doctor_id}, {"$set": profile}, upsert=True
    )

    # Recuperar el documento para obtener su ObjectId
    doc_esp = await col_profiles.find_one({"doctor.id_doctoralia": doctor_id})
    if not doc_esp:
        raise HTTPException(
            status_code=500, detail="Error al recuperar el perfil guardado."
        )

    mongo_id = str(doc_esp["_id"])

    # 4. Scraping de Opiniones adicionales (si es necesario)
    total_opiniones = profile.get("total_opiniones", 0)
    opiniones_guardadas = []
    if total_opiniones > 0:
        from app.scraper.reviews_scraper import construir_resultado_opiniones

        # Ejecutar scraper sincrónico de opiniones en un thread
        opiniones_resultado = await asyncio.to_thread(
            construir_resultado_opiniones, doctor_id, total_opiniones, data.max_opinions
        )

        opiniones_guardadas = opiniones_resultado.get("opiniones", [])

        if opiniones_guardadas:
            col_opinions = db_async["doctor_opinions"]
            # pyrefly: ignore [missing-import]
            from pymongo import UpdateOne

            operations = []
            for op in opiniones_guardadas:
                op["doctor_id"] = doctor_id
                operations.append(
                    UpdateOne(
                        {"opinion_id": op["opinion_id"], "doctor_id": doctor_id},
                        {"$set": op},
                        upsert=True,
                    )
                )
            if operations:
                await col_opinions.bulk_write(operations)

    # 5. Analizar con Ollama (sin token, local) o con modelo externo (con token)
    usar_ollama = data.analyze and data.model == "ollama"

    if data.analyze and (token_str or usar_ollama):
        # Importaciones tardías para evitar dependencias circulares/carga pesada global
        from app.nlp.modelos import obtener_modelo
        from app.nlp.preprocesador import preparar_datos_para_analisis
        from app.nlp.prompt_builder import (
            construir_prompt_sistema,
            construir_prompt_usuario,
            reforzar_resultado_analisis,
        )
        from app.nlp.repositorios.analisis_repo import guardar_analisis

        # Buscar las opiniones guardadas para enviarlas al modelo
        cursor_opinions = (
            db_async["doctor_opinions"]
            .find({"doctor_id": doctor_id})
            .sort("fecha_publicacion", -1)
            .limit(data.max_opinions)
        )
        opiniones_db = await cursor_opinions.to_list(length=data.max_opinions)

        # Si no se encontraron en Mongo (ej. se acaban de extraer y no dio tiempo), usar las que sacamos
        if not opiniones_db:
            opiniones_db = opiniones_guardadas[: data.max_opinions]

        datos = preparar_datos_para_analisis(profile, opiniones_db, min_opiniones_ia=1)

        if datos["apto_para_ia"]:
            modelo = obtener_modelo(data.model)

            # Configurar modelo Ollama con el modelo específico si se indicó
            if usar_ollama and data.ollama_model:
                modelo._modelo = data.ollama_model

            # Inyección dinámica del API key (solo para modelos externos)
            # Asumimos que los modelos en base_modelo.py leen self.api_key o usarán os.environ.
            # Lo más limpio es setear la variable o pasarla en kwargs.
            # Verificaremos cómo lo usan, por ahora agregamos la propiedad
            if hasattr(modelo, "api_key"):
                modelo.api_key = token_str
            else:
                # Fallback: algunos modelos leen client.api_key (como GroqModelo, GeminiModelo)
                # Como son instanciados, podemos asignarles
                setattr(modelo, "api_key", token_str)
                # Si usan cliente oficial, podríamos tener que recrear el cliente
                if data.model == "groq":
                    # pyrefly: ignore [missing-import]
                    from groq import Groq

                    modelo.cliente = Groq(api_key=token_str)
                elif data.model == "gemini":
                    # pyrefly: ignore [missing-import]
                    import google.generativeai as genai

                    # Gemini model initialization uses configure, which sets a global state.
                    # This is tricky in a multi-user environment.
                    genai.configure(api_key=token_str)
                    # We might need to recreate the model instance:
                    # modelo.model = genai.GenerativeModel(...)
                elif data.model == "deepseek":
                    # pyrefly: ignore [missing-import]
                    import openai

                    modelo.cliente = openai.OpenAI(
                        api_key=token_str, base_url="https://api.deepseek.com"
                    )

            prompt_sistema = construir_prompt_sistema()
            prompt_usuario = construir_prompt_usuario(datos)

            try:
                # LLM request
                respuesta_raw = await asyncio.to_thread(
                    modelo.analizar, prompt_sistema, prompt_usuario
                )
                resultado_ia = modelo.parsear_respuesta(respuesta_raw)
                resultado_ia = reforzar_resultado_analisis(resultado_ia, datos)

                doc_analisis = {
                    "doctor_id": doctor_id,
                    "doctoralia_id": doctor_id,
                    "nombre_especialista": profile.get("doctor", {}).get("nombre", ""),
                    "especialidad": profile.get("especialidad", ""),
                    "estado": "completado",
                    "fecha_analisis": datetime.now(timezone.utc),
                    "modelo_usado": data.model,
                    "version_prompt": "v2",
                    "metricas_locales": datos.get("metricas_locales", {}),
                    "metadatos_muestreo": datos.get("metadatos_muestreo", {}),
                    "perfil_limpio": datos.get("perfil_limpio", {}),
                    "alertas_preprocesamiento": datos.get("alertas", []),
                    "resultado_ia": resultado_ia,
                    "error_detalle": None,
                    "fatal_proveedor": False,
                }

                # guardar_analisis es síncrono
                await asyncio.to_thread(guardar_analisis, doc_analisis)

            except Exception as e:
                # Guardar el error de análisis si falla
                doc_error = {
                    "doctor_id": doctor_id,
                    "doctoralia_id": doctor_id,
                    "estado": "error",
                    "error_detalle": str(e),
                    "fecha_analisis": datetime.now(timezone.utc),
                }
                await asyncio.to_thread(guardar_analisis, doc_error)
                raise HTTPException(
                    status_code=500, detail=f"Error en análisis IA: {e}"
                )
        else:
            doc_no_apto = {
                "doctor_id": doctor_id,
                "estado": "sin_opiniones",
                "fecha_analisis": datetime.now(timezone.utc),
                "error_detalle": datos.get("razon_no_apto"),
            }
            await asyncio.to_thread(guardar_analisis, doc_no_apto)

    return {
        "mensaje": "Scraping y análisis completados con éxito.",
        "especialista_id": mongo_id,
        "doctoralia_id": doctor_id,
    }
