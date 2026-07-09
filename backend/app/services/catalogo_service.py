"""
Servicio de validación de catálogos contra la base de datos MongoDB.

Proporciona funciones de solo lectura para que el chatbot pueda
verificar que especialidades y ciudades existen antes de sugerirlas.

Restricciones de seguridad:
    - Solo operaciones de lectura (find/count).
    - Nunca lista colecciones completas sin filtro de búsqueda.
    - No puede crear, actualizar ni eliminar registros.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

from app.db.mongo import get_doctoralia_async_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapeo de códigos postales mexicanos a ciudades (muestra representativa).
# Cubre los rangos de CP más comunes por estado/zona metropolitana.
# ---------------------------------------------------------------------------

_TABLA_CP_CIUDAD: dict[str, str] = {
    # CDMX — rangos 01000–16999
    **{str(cp): "Ciudad de México" for cp in range(1000, 17000)},
    # Ecatepec, Estado de México
    **{str(cp): "Ecatepec de Morelos" for cp in range(55000, 55599)},
    # Nezahualcóyotl, Estado de México
    **{str(cp): "Nezahualcóyotl" for cp in range(57000, 57999)},
    # Tlalnepantla, Estado de México
    **{str(cp): "Tlalnepantla de Baz" for cp in range(54000, 54999)},
    # Naucalpan, Estado de México
    **{str(cp): "Naucalpan de Juárez" for cp in range(53000, 53999)},
    # Guadalajara, Jalisco
    **{str(cp): "Guadalajara" for cp in range(44100, 44999)},
    # Zapopan, Jalisco
    **{str(cp): "Zapopan" for cp in range(45000, 45999)},
    # Monterrey, Nuevo León
    **{str(cp): "Monterrey" for cp in range(64000, 64999)},
    # San Nicolás de los Garza, NL
    **{str(cp): "San Nicolás de los Garza" for cp in range(66400, 66599)},
    # Puebla, Puebla
    **{str(cp): "Puebla" for cp in range(72000, 72999)},
    # Tijuana, Baja California
    **{str(cp): "Tijuana" for cp in range(22000, 22999)},
    # León, Guanajuato
    **{str(cp): "León" for cp in range(37000, 37999)},
    # Juárez, Chihuahua
    **{str(cp): "Ciudad Juárez" for cp in range(32000, 32999)},
    # Mérida, Yucatán
    **{str(cp): "Mérida" for cp in range(97000, 97999)},
    # Cancún, Quintana Roo
    **{str(cp): "Cancún" for cp in range(77500, 77999)},
    # Querétaro, Querétaro
    **{str(cp): "Querétaro" for cp in range(76000, 76999)},
    # San Luis Potosí, SLP
    **{str(cp): "San Luis Potosí" for cp in range(78000, 78999)},
    # Aguascalientes, Ags
    **{str(cp): "Aguascalientes" for cp in range(20000, 20999)},
    # Hermosillo, Sonora
    **{str(cp): "Hermosillo" for cp in range(83000, 83999)},
    # Culiacán, Sinaloa
    **{str(cp): "Culiacán" for cp in range(80000, 80999)},
    # Chihuahua, Chihuahua
    **{str(cp): "Chihuahua" for cp in range(31000, 31999)},
    # Morelia, Michoacán
    **{str(cp): "Morelia" for cp in range(58000, 58999)},
    # Veracruz, Ver.
    **{str(cp): "Veracruz" for cp in range(91700, 91999)},
    # Xalapa, Veracruz
    **{str(cp): "Xalapa" for cp in range(91000, 91499)},
    # Acapulco, Guerrero
    **{str(cp): "Acapulco de Juárez" for cp in range(39300, 39999)},
    # Oaxaca, Oaxaca
    **{str(cp): "Oaxaca de Juárez" for cp in range(68000, 68499)},
    # Saltillo, Coahuila
    **{str(cp): "Saltillo" for cp in range(25000, 25999)},
    # Mexicali, Baja California
    **{str(cp): "Mexicali" for cp in range(21000, 21999)},
    # Torreón, Coahuila
    **{str(cp): "Torreón" for cp in range(27000, 27999)},
    # Durango, Dgo.
    **{str(cp): "Durango" for cp in range(34000, 34999)},
    # Tepic, Nayarit
    **{str(cp): "Tepic" for cp in range(63000, 63999)},
}


def resolver_codigo_postal(cp: str) -> Optional[str]:
    """
    Traduce un código postal mexicano a un nombre de ciudad reconocible.

    Parámetros
    ----------
    cp : str
        Código postal de 5 dígitos.

    Retorna
    -------
    str o None
        Nombre de la ciudad o None si el CP no está en la tabla.

    Ejemplo
    -------
    >>> resolver_codigo_postal("55120")
    "Ecatepec de Morelos"
    """
    cp_limpio = cp.strip().zfill(5)
    return _TABLA_CP_CIUDAD.get(cp_limpio)


def es_codigo_postal(texto: str) -> bool:
    """
    Detecta si el texto es un código postal mexicano (5 dígitos).

    Parámetros
    ----------
    texto : str
        Texto a evaluar.

    Retorna
    -------
    bool
        True si es un código postal numérico de 4-5 dígitos.
    """
    return bool(re.match(r"^\d{4,5}$", texto.strip()))


def _normalizar_slug(texto: str) -> str:
    """
    Convierte texto a slug normalizado para búsqueda (sin acentos, sin espacios).

    Parámetros
    ----------
    texto : str
        Texto a normalizar.

    Retorna
    -------
    str
        Texto en minúsculas, sin tildes y con espacios reemplazados por guiones.
    """
    nfkd = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")


async def validar_especialidad(slug_candidato: str) -> Optional[str]:
    """
    Verifica si una especialidad existe en MongoDB usando búsqueda por prefijo.

    Primero busca coincidencia exacta de slug, luego usa el candidato como
    prefijo de tipo "cardio%" para tolerar variantes de género o escritura.

    Parámetros
    ----------
    slug_candidato : str
        Slug sugerido por el LLM (ej. "cardiologo", "cardiologa", "cardio").

    Retorna
    -------
    str o None
        El slug oficial de la especialidad si existe, None si no se encontró.

    Ejemplo
    -------
    >>> await validar_especialidad("cardiologa")
    "cardiologo"
    """
    if not slug_candidato or not slug_candidato.strip():
        return None

    slug = _normalizar_slug(slug_candidato)

    try:
        db = get_doctoralia_async_db()
        col = db["specializations"]

        # 1. Coincidencia exacta de urlname
        doc = await col.find_one({"urlname": slug}, {"urlname": 1})
        if doc:
            return doc["urlname"]

        # 2. Búsqueda por prefijo — "cardio%" captura cardiologo, cardiologia, etc.
        prefijo = slug[:6] if len(slug) >= 6 else slug
        filtro_prefijo = {
            "$or": [
                {"urlname": {"$regex": f"^{re.escape(prefijo)}", "$options": "i"}},
                {
                    "name": {
                        "$regex": re.escape(slug_candidato.strip()),
                        "$options": "i",
                    }
                },
            ]
        }
        doc = await col.find_one(filtro_prefijo, {"urlname": 1})
        if doc:
            logger.info(
                "[CatalogoService] Especialidad '%s' mapeada a '%s' por prefijo",
                slug_candidato,
                doc["urlname"],
            )
            return doc["urlname"]

        logger.warning(
            "[CatalogoService] Especialidad '%s' no encontrada en la colección",
            slug_candidato,
        )
        return None

    except Exception as exc:
        logger.error(
            "[CatalogoService] Error validando especialidad '%s': %s",
            slug_candidato,
            exc,
        )
        return None


async def validar_ciudad(nombre_candidato: str) -> Optional[str]:
    """
    Verifica si una ciudad existe en MongoDB usando búsqueda parcial.

    Parámetros
    ----------
    nombre_candidato : str
        Nombre o slug de ciudad sugerido por el LLM.

    Retorna
    -------
    str o None
        El displayName oficial de la ciudad si existe, None si no.

    Ejemplo
    -------
    >>> await validar_ciudad("cdmx")
    "Ciudad de México"
    """
    if not nombre_candidato or not nombre_candidato.strip():
        return None

    candidato = nombre_candidato.strip()

    # Si es un código postal, resolverlo primero
    if es_codigo_postal(candidato):
        ciudad_resuelta = resolver_codigo_postal(candidato)
        if ciudad_resuelta:
            logger.info(
                "[CatalogoService] CP '%s' resuelto a ciudad '%s'",
                candidato,
                ciudad_resuelta,
            )
            candidato = ciudad_resuelta
        else:
            logger.warning(
                "[CatalogoService] CP '%s' no encontrado en tabla", candidato
            )
            return None

    try:
        db = get_doctoralia_async_db()
        col = db["cities"]

        # Búsqueda case-insensitive sobre displayName o slug
        filtro = {
            "$or": [
                {"displayName": {"$regex": re.escape(candidato), "$options": "i"}},
                {
                    "slug": {
                        "$regex": re.escape(_normalizar_slug(candidato)),
                        "$options": "i",
                    }
                },
            ]
        }
        doc = await col.find_one(filtro, {"displayName": 1, "slug": 1})
        if doc:
            return doc.get("displayName") or doc.get("slug")

        logger.warning(
            "[CatalogoService] Ciudad '%s' no encontrada en la colección", candidato
        )
        return None

    except Exception as exc:
        logger.error(
            "[CatalogoService] Error validando ciudad '%s': %s", candidato, exc
        )
        return None
