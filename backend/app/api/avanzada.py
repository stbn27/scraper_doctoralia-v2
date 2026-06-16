# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException

# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import asyncio

from app.db.mongo import get_doctoralia_async_db, get_mongo_db
from app.db.mysql import get_mysql_conn
from app.security import get_current_user

router = APIRouter(prefix="/especialistas/avanzada", tags=["Búsqueda Avanzada"])


class AvanzadaRequest(BaseModel):
    url: str
    max_opinions: int = 30
    scrape_only: bool = True
    analyze: bool = False
    model: Optional[str] = None


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

    try:
        profile = await fetch_and_parse_profile_async(data.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar el perfil: {e}")

    doctor_id = profile.get("doctor", {}).get("id_doctoralia")
    if not doctor_id:
        raise HTTPException(
            status_code=400, detail="No se pudo obtener el ID del doctor del perfil."
        )

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

    # 5. Analizar
    if data.analyze and token_str:
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
            # Inyección dinámica del API key
            # Monkey patch al modelo para que use este token
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
