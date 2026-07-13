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
# Compatible con el nombre en .env (LMSTUDIO_BASE_URL) y el alternativo (LM_STUDIO_BASE_URL)
LM_STUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL") or os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234")


class AvanzadaRequest(BaseModel):
    url: str
    max_opinions: int = 30
    scrape_only: bool = True
    analyze: bool = False
    model: Optional[str] = None
    ollama_model: Optional[str] = None  # Modelo específico de Ollama si aplica


def _extraer_doctor_id_de_html(html: str, url: Optional[str] = None) -> int | None:
    """
    Intenta extraer el ID numérico de Doctoralia desde el HTML del perfil o URL.
    Prueba múltiples estrategias: JSON-LD, data attributes y patrones JS/URL para médicos y clínicas.

    Args:
        html: HTML crudo del perfil de Doctoralia.
        url: URL opcional del perfil.

    Returns:
        ID numérico del doctor/clínica, o None si no se pudo extraer.
    """
    # Estrategia 1: JSON-LD con @type Doctor o Physician o MedicalBusiness
    ld_blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL)
    for block in ld_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "@graph" in data:
                items = data["@graph"]
            else:
                items = [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") in ("Physician", "Doctor", "Person", "MedicalBusiness", "Hospital", "MedicalOrganization"):
                    url_item = item.get("url", item.get("@id", ""))
                    m = re.search(r'/(\d+)(?:[/?#]|$)', url_item)
                    if m:
                        return int(m.group(1))
        except Exception:
            pass

    # Estrategia 2: variable JS con el ID del doctor o clínica
    patterns_js = [
        r'"doctor_id"\s*:\s*(\d+)',
        r'"userId"\s*:\s*(\d+)',
        r'"docId"\s*:\s*(\d+)',
        r"doctorId[\s:=]+(\d+)",
        r'"facility_id"\s*:\s*(\d+)',
        r'"facilityId"\s*:\s*(\d+)',
        r"facilityId[\s:=]+(\d+)",
    ]
    for pat in patterns_js:
        m = re.search(pat, html)
        if m:
            return int(m.group(1))

    # Estrategia 3: data attributes para médicos o clínicas
    patterns_attr = [
        r'data-doctor-id=["\']?(\d+)["\']?',
        r'data-user-id=["\']?(\d+)["\']?',
        r'data-facility-id=["\']?(\d+)["\']?',
        r'data-clinic-id=["\']?(\d+)["\']?',
    ]
    for pat in patterns_attr:
        m = re.search(pat, html)
        if m:
            return int(m.group(1))

    # Estrategia 4: Si es una URL de clínica específicamente y no se encontró en HTML, usar address-id si está
    if url and any(w in url.lower() for w in ["/clinica", "/centro-", "/facility", "/hospital", "/sanatorio"]):
        m_addr = re.search(r'#address-id=(\d+)', url)
        if m_addr:
            return int(m_addr.group(1))

    return None


def _doctor_id_sintetico_desde_url(url: str) -> int:
    """
    Genera un ID entero estable a partir de la URL. Si es específicamente una URL de clínica
    y tiene #address-id=123, utiliza ese ID. En caso contrario, usa los últimos 8 dígitos del hash MD5.

    Args:
        url: URL del perfil de Doctoralia.

    Returns:
        Entero positivo reproducible para esa URL.
    """
    if any(w in url.lower() for w in ["/clinica", "/centro-", "/facility", "/hospital", "/sanatorio"]):
        m_addr = re.search(r'#address-id=(\d+)', url)
        if m_addr:
            return int(m_addr.group(1))
    digest = hashlib.md5(url.encode()).hexdigest()
    return int(digest[:8], 16)  # máx ~4.29 mil millones, suficiente para colisiones bajas


@router.get("/ollama-status")
async def ollama_status():
    """
    Verifica si Ollama o LM Studio están disponibles localmente y devuelve los modelos instalados.

    Comprueba primero Ollama (puerto 11434) y luego LM Studio (puerto 1234).
    El campo `disponible` es True si al menos uno de los dos está activo.
    Cada entrada en `modelos` incluye el campo `proveedor` para identificar la fuente.

    Returns:
        Objeto con {disponible: bool, ollama: bool, lm_studio: bool,
                    modelos: list[{name, proveedor}], url: str}
    """
    ollama_ok = False
    lm_studio_ok = False
    modelos: list[dict] = []

    # — Verificar Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            for m in data.get("models", []):
                modelos.append({"name": m["name"], "proveedor": "ollama"})
            ollama_ok = True
    except Exception:
        pass

    # — Verificar LM Studio
    # Prueba /v1/models (OpenAI-compat, campo 'id') y /api/v1/models (nativa, campo 'key')
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            for path, id_field in [("/v1/models", "id"), ("/api/v1/models", "key")]:
                try:
                    resp = await client.get(f"{LM_STUDIO_BASE_URL}{path}")
                    resp.raise_for_status()
                    lms_data = resp.json()
                    # /v1/models devuelve {data:[{id,...}]}, /api/v1/models devuelve {models:[{key,...}]}
                    items = lms_data.get("data") or lms_data.get("models") or []
                    found = [m[id_field] for m in items if m.get(id_field)]
                    if found:
                        for name in found:
                            modelos.append({"name": name, "proveedor": "lm_studio"})
                        lm_studio_ok = True
                        break
                except Exception:
                    continue
    except Exception:
        pass

    return {
        "disponible": ollama_ok or lm_studio_ok,
        "ollama": ollama_ok,
        "lm_studio": lm_studio_ok,
        "modelos": modelos,
        "url": OLLAMA_BASE_URL,
        "lm_studio_url": LM_STUDIO_BASE_URL,
    }


@router.post("/scrape-analyze")
async def scrape_analyze(
    data: AvanzadaRequest, current_user: dict = Depends(get_current_user)
):
    if "doctoralia.com" not in data.url:
        raise HTTPException(
            status_code=400, detail="URL inválida. Debe ser un perfil de Doctoralia."
        )

    from urllib.parse import urlparse
    parsed_url = urlparse(data.url.strip())
    data.url = parsed_url._replace(query="", fragment="").geturl().rstrip('/')

    # 1. Validar Token si se requiere análisis
    token_str = None
    # Los modelos locales (ollama / lm_studio) no requieren token de usuario
    es_modelo_local = data.model in ("ollama", "local", "lm_studio")
    if data.analyze:
        if not data.model:
            raise HTTPException(
                status_code=400,
                detail="El modelo es requerido para realizar el análisis.",
            )

        if not es_modelo_local:
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
    # pyrefly: ignore [missing-import]
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
            doctor_id = _extraer_doctor_id_de_html(_html_raw, data.url)

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

    # Verificar si el perfil ya existía para proteger y preservar metadatos valiosos (nombre, opiniones reportadas)
    doc_existente = await col_profiles.find_one({"doctor.id_doctoralia": doctor_id})
    if doc_existente:
        doc_exist_doc = doc_existente.get("doctor", {})
        new_doc = profile.get("doctor", {})
        if not new_doc.get("nombre") and doc_exist_doc.get("nombre"):
            new_doc["nombre"] = doc_exist_doc["nombre"]
        if not new_doc.get("foto_perfil") and doc_exist_doc.get("foto_perfil"):
            new_doc["foto_perfil"] = doc_exist_doc["foto_perfil"]
        if not new_doc.get("especialidades") and doc_exist_doc.get("especialidades"):
            new_doc["especialidades"] = doc_exist_doc["especialidades"]
        if not new_doc.get("cedulas") and doc_exist_doc.get("cedulas"):
            new_doc["cedulas"] = doc_exist_doc["cedulas"]
        
        # Si total_opiniones vino en 0 o nulo y en BD teníamos un número real > 0, conservar el de BD
        if (not profile.get("total_opiniones") or profile.get("total_opiniones") == 0) and doc_existente.get("total_opiniones", 0) > 0:
            profile["total_opiniones"] = doc_existente["total_opiniones"]

    # Registrar la fecha de actualización en metadata (no en un campo aparte)
    ahora_iso = datetime.now(timezone.utc).isoformat()
    if "metadata" not in profile or profile["metadata"] is None:
        profile["metadata"] = {}
    profile["metadata"]["ultima_actualizacion"] = ahora_iso

    # Eliminar scraping_meta si existiera en el doc entrante para no contaminar el esquema
    profile.pop("scraping_meta", None)

    await col_profiles.update_one(
        {"doctor.id_doctoralia": doctor_id},
        {
            "$set": profile,
            "$unset": {"scraping_meta": ""},
        },
        upsert=True,
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

        try:
            # Ejecutar scraper sincrónico de opiniones en un thread
            opiniones_resultado = await asyncio.to_thread(
                construir_resultado_opiniones, doctor_id, total_opiniones, data.max_opinions, data.url
            )
            opiniones_guardadas = opiniones_resultado.get("opiniones", [])
        except Exception:
            # Si el endpoint AJAX no está disponible (ej. 404 o ID sintético), continuamos sin opiniones AJAX
            opiniones_guardadas = []

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

    # 5. Analizar con proveedor local (Ollama / LM Studio) o con modelo externo
    usar_local = data.analyze and es_modelo_local

    # Cuando se pide 'local' pero no hay proveedor disponible, hacer fallback a env vars del sistema
    if usar_local:
        # Verificar si hay algún proveedor local disponible
        _local_disponible = False
        _local_model_id = None
        _local_url = None
        _local_es_lm_studio = False

        try:
            async with httpx.AsyncClient(timeout=3.0) as _c:
                # Intentar LM Studio primero
                for _path, _field in [("/v1/models", "id"), ("/api/v1/models", "key")]:
                    try:
                        _r = await _c.get(f"{LM_STUDIO_BASE_URL}{_path}")
                        _r.raise_for_status()
                        _lms_data = _r.json()
                        _items = _lms_data.get("data") or _lms_data.get("models") or []
                        _found = [m[_field] for m in _items if m.get(_field)]
                        if _found:
                            _local_model_id = data.ollama_model or _found[0]
                            _local_url = LM_STUDIO_BASE_URL
                            _local_es_lm_studio = True
                            _local_disponible = True
                            break
                    except Exception:
                        continue

                # Si LM Studio no está, probar Ollama
                if not _local_disponible:
                    try:
                        _r = await _c.get(f"{OLLAMA_BASE_URL}/api/tags")
                        _r.raise_for_status()
                        _tags = _r.json().get("models", [])
                        if _tags:
                            _local_model_id = data.ollama_model or _tags[0]["name"]
                            _local_url = OLLAMA_BASE_URL
                            _local_disponible = True
                    except Exception:
                        pass
        except Exception:
            pass

        if not _local_disponible:
            # Fallback: buscar token en variables de entorno del sistema (modo admin)
            _ENV_FALLBACK = [
                ("gemini",   "GEMINI_API_KEY"),
                ("groq",     "GROQ_API_KEY"),
                ("deepseek", "DEEPSEEK_API_KEY"),
            ]
            for _mod, _env in _ENV_FALLBACK:
                _key = os.getenv(_env, "").strip()
                if _key:
                    usar_local = False
                    es_modelo_local = False
                    token_str = _key
                    # Actualizar data.model al modelo de fallback para que la instanciación sea correcta
                    data.model = _mod  # type: ignore[assignment]
                    break
            else:
                # Sin proveedor local ni env vars → omitir análisis, solo guardar el perfil
                usar_local = False

    if data.analyze and (token_str or usar_local):
        # Importaciones tardías para evitar dependencias circulares/carga pesada global
        from app.nlp.modelos import obtener_modelo
        from app.nlp.preprocesador import preparar_datos_para_analisis
        from app.nlp.prompt_builder import (
            construir_prompt_sistema,
            construir_prompt_usuario,
            reforzar_resultado_analisis,
        )

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
            # Resolver el proveedor local real
            ollama_model_id = data.ollama_model
            es_lm_studio_model = False

            if usar_local:
                # Usar los datos ya resueltos arriba
                ollama_model_id = _local_model_id
                es_lm_studio_model = _local_es_lm_studio
                modelo = obtener_modelo("ollama")
                if ollama_model_id:
                    modelo._modelo = ollama_model_id
                if es_lm_studio_model and _local_url:
                    if hasattr(modelo, "_es_lm_studio"):
                        modelo._es_lm_studio = True
                    else:
                        setattr(modelo, "_es_lm_studio", True)
                    if hasattr(modelo, "_base_url"):
                        modelo._base_url = f"{_local_url}/v1"
                    else:
                        setattr(modelo, "_base_url", f"{_local_url}/v1")
            else:
                modelo = obtener_modelo(data.model)
                # Inyectar token del sistema o de usuario
                if hasattr(modelo, "api_key"):
                    modelo.api_key = token_str
                else:
                    setattr(modelo, "api_key", token_str)
                    if data.model == "groq":
                        # pyrefly: ignore [missing-import]
                        from groq import Groq
                        modelo.cliente = Groq(api_key=token_str)
                    elif data.model == "gemini":
                        # pyrefly: ignore [missing-import]
                        import google.generativeai as genai
                        genai.configure(api_key=token_str)
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

                especialidad_nom = profile.get("doctor", {}).get("especialidad", "") or profile.get("especialidad", "")
                nombre_prov_local = "lm_studio" if _local_es_lm_studio else "ollama"
                modelo_real_usado = f"{nombre_prov_local} ({_local_model_id})" if (usar_local and _local_model_id) else (f"{data.model} ({ollama_model_id})" if (data.model in ("ollama", "lm_studio") and ollama_model_id) else str(data.model))
                doc_analisis = {
                    "id_doctoralia": doctor_id,
                    "doctor_id": doctor_id,
                    "doctoralia_id": doctor_id,
                    "nombre_especialista": profile.get("doctor", {}).get("nombre", ""),
                    "especialidad": especialidad_nom,
                    "estatus_analisis": "completado",
                    "estado": "completado",
                    "fecha_analisis": datetime.now(timezone.utc),
                    "modelo_usado": modelo_real_usado,
                    "version_prompt": "v2",
                    "analisis": {
                        "puntuacion": resultado_ia.get("puntuacion_recomendacion"),
                        "resumen": resultado_ia.get("resumen"),
                        "puntos_fuertes": resultado_ia.get("puntos_fuertes", []),
                        "puntos_debiles": resultado_ia.get("puntos_debiles", []),
                        "confiabilidad": resultado_ia.get("confiabilidad_opiniones"),
                        "justificacion": resultado_ia.get("justificacion_puntuacion"),
                    },
                    "metadata_analisis": {
                        "fecha": datetime.now(timezone.utc).isoformat(),
                        "opiniones_enviadas": len(datos.get("opiniones_procesadas", [])),
                        "error_detalle": None,
                    },
                    "metadata_opiniones": datos.get("metricas_locales", {}),
                    "metricas_locales": datos.get("metricas_locales", {}),
                    "metadatos_muestreo": datos.get("metadatos_muestreo", {}),
                    "perfil_limpio": datos.get("perfil_limpio", {}),
                    "alertas_preprocesamiento": datos.get("alertas", []),
                    "resultado_ia": resultado_ia,
                    "error_detalle": None,
                    "fatal_proveedor": False,
                }

                await db_async["analisis_especialistas"].update_one(
                    {"id_doctoralia": doctor_id},
                    {"$set": doc_analisis},
                    upsert=True,
                )

            except Exception as e:
                # Guardar el error de análisis si falla
                doc_error = {
                    "id_doctoralia": doctor_id,
                    "doctor_id": doctor_id,
                    "doctoralia_id": doctor_id,
                    "estatus_analisis": "error",
                    "estado": "error",
                    "error_detalle": str(e),
                    "metadata_analisis": {
                        "fecha": datetime.now(timezone.utc).isoformat(),
                        "error_detalle": str(e),
                    },
                    "fecha_analisis": datetime.now(timezone.utc),
                }
                await db_async["analisis_especialistas"].update_one(
                    {"id_doctoralia": doctor_id},
                    {"$set": doc_error},
                    upsert=True,
                )
                raise HTTPException(
                    status_code=500, detail=f"Error en análisis IA: {e}"
                )
        else:
            doc_no_apto = {
                "id_doctoralia": doctor_id,
                "doctor_id": doctor_id,
                "doctoralia_id": doctor_id,
                "estatus_analisis": "sin_opiniones",
                "estado": "sin_opiniones",
                "metadata_analisis": {
                    "fecha": datetime.now(timezone.utc).isoformat(),
                    "error_detalle": datos.get("razon_no_apto"),
                },
                "fecha_analisis": datetime.now(timezone.utc),
                "error_detalle": datos.get("razon_no_apto"),
            }
            await db_async["analisis_especialistas"].update_one(
                {"id_doctoralia": doctor_id},
                {"$set": doc_no_apto},
                upsert=True,
            )

    return {
        "mensaje": "Scraping y análisis completados con éxito.",
        "especialista_id": mongo_id,
        "doctoralia_id": doctor_id,
    }
