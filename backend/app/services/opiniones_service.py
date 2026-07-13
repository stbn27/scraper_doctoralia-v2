"""Servicio de negocio para opiniones bajo demanda."""

import asyncio
from datetime import datetime, timezone

from app.db.repositorios import opiniones_repo
from app.scraper import reviews_scraper


async def obtener_o_scrapear_opiniones(
    especialista: dict,
    limite: int = 30,
    forzar_actualizacion: bool = False,
) -> dict:
    """Obtiene opiniones desde Mongo o ejecuta scraping si es necesario."""
    doctoralia_id = especialista.get("doctoralia_id")
    total_opiniones = especialista.get("total_opiniones")

    if not doctoralia_id or not total_opiniones:
        return {
            "fuente": "sin_datos_para_scraping",
            "total_en_bd": 0,
            "total_extraidas": 0,
            "opiniones": [],
        }

    total_en_bd = await opiniones_repo.contar_opiniones_por_doctor(doctoralia_id)
    if total_en_bd > 0 and not forzar_actualizacion:
        opiniones = await opiniones_repo.obtener_opiniones_por_doctor(
            doctoralia_id, limite=limite
        )
        return {
            "fuente": "mongo",
            "total_en_bd": total_en_bd,
            "total_extraidas": len(opiniones),
            "opiniones": opiniones,
        }

    url_perfil = especialista.get("doctor", {}).get("url_perfil") or especialista.get("metadata", {}).get("fuente")
    resultado = await asyncio.to_thread(
        reviews_scraper.construir_resultado_opiniones,
        doctoralia_id,
        total_opiniones,
        limite,
        url_perfil,
    )

    meta = resultado.get("meta", {})
    opiniones_raw = resultado.get("opiniones", [])
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    opiniones = []
    for opinion in opiniones_raw:
        opiniones.append(
            {
                "opinion_id": opinion.get("opinion_id"),
                "doctor_id": doctoralia_id,
                "autor": opinion.get("autor"),
                "rating": opinion.get("rating"),
                "texto": opinion.get("texto"),
                "fecha_publicacion": opinion.get("fecha"),
                "servicio_consultado": opinion.get("servicio_consultado"),
                "consultorio": opinion.get("consultorio"),
                "tipo_verificacion": opinion.get("tipo_verificacion"),
                "scraping_meta": {
                    "fecha_extraccion": meta.get("fecha_extraccion", timestamp),
                },
            }
        )

    total_insertado = await opiniones_repo.insertar_opiniones_masivo(opiniones)
    opiniones_final = await opiniones_repo.obtener_opiniones_por_doctor(
        doctoralia_id, limite=limite
    )

    return {
        "fuente": "scraping",
        "total_en_bd": total_insertado,
        "total_extraidas": len(opiniones_final),
        "opiniones": opiniones_final,
    }
