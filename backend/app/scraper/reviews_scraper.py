import argparse
import html
import json
import math
import random
import re
import time
from datetime import datetime
from pathlib import Path

# pyrefly: ignore [missing-import]
import httpx

# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup

from app.scraper.utils.base import get_user_agent

ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT_DIR / "fixtures"
BASE_URL = "https://www.doctoralia.com.mx/ajax/mobile/doctor-opinions"
BASE_URL_FACILITY = "https://www.doctoralia.com.mx/ajax/facility/opinions"


def limpiar_texto(text: str | None) -> str | None:
    """Normaliza texto eliminando espacios repetidos y recortando extremos.

    Args:
        text: Texto original o ``None``.

    Returns:
        Texto limpio, o ``None`` si no hay contenido util.
    """
    if not text:
        return None
    text = " ".join(text.split()).strip()
    return text or None


def convertir_entero(value: str | int | float | None) -> int | None:
    """Convierte un valor a entero si es posible.

    Args:
        value: Numero, texto numerico o ``None``.

    Returns:
        Entero convertido, o ``None`` si la entrada esta vacia o no es numerica.
    """
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def convertir_decimal(value: str | int | float | None) -> float | None:
    """Convierte un valor a numero decimal si es posible.

    Args:
        value: Numero, texto numerico o ``None``.

    Returns:
        Valor ``float`` convertido, o ``None`` si la conversion falla.
    """
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def fetch_pagina_opiniones(
    doctor_id: int, page: int, es_clinica: bool | None = None
) -> tuple[str, int, int, bool]:
    """Descarga una pagina de opiniones desde el endpoint AJAX de Doctoralia.

    Soporta tanto perfiles de médicos (/ajax/mobile/doctor-opinions) como
    perfiles de clínicas/centros (/ajax/facility/opinions). Si el endpoint
    inicial responde con 404 Not Found, hace fallback automático al otro.

    Args:
        doctor_id: Identificador interno en Doctoralia.
        page: Numero de pagina de opiniones que se quiere descargar.
        es_clinica: True para intentar ruta de clínica primero, False para doctor.
            Si es None o da 404, prueba automáticamente ambos endpoints.

    Returns:
        Tupla ``(html_text, num_rows, limit, es_clinica_efectivo)``.
    """
    headers = {
        "User-Agent": get_user_agent(),
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept": "application/json, text/plain, */*",
    }

    if es_clinica is True:
        rutas = [(BASE_URL_FACILITY, True), (BASE_URL, False)]
    elif es_clinica is False:
        rutas = [(BASE_URL, False), (BASE_URL_FACILITY, True)]
    else:
        # Por defecto intenta doctor y luego facility
        rutas = [(BASE_URL, False), (BASE_URL_FACILITY, True)]

    ultimo_exc = None
    for url_base, es_fac in rutas:
        url = f"{url_base}/{doctor_id}/{page}"
        try:
            response = httpx.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            payload = response.json()
            raw_html = payload.get("html") if isinstance(payload, dict) else None
            num_rows = int(payload.get("numRows", 0)) if isinstance(payload, dict) else 0
            limit = int(payload.get("limit", 10)) if isinstance(payload, dict) else 10
            return html.unescape(raw_html or ""), num_rows, limit, es_fac
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                ultimo_exc = exc
                continue  # Probar el siguiente endpoint ante un 404
            raise
        except Exception as exc:
            ultimo_exc = exc
            continue

    # Si todos los intentos respondieron 404, el ID o la página no tienen opiniones AJAX en Doctoralia.
    # Devolvemos tupla vacía para que el flujo siga y no tumbar el servidor con un 500.
    if isinstance(ultimo_exc, httpx.HTTPStatusError) and ultimo_exc.response.status_code == 404:
        return "", 0, 10, (es_clinica if es_clinica is not None else False)

    if ultimo_exc:
        raise ultimo_exc
    return "", 0, 10, False


def extract_opinion_id(node) -> int | None:
    """Intenta obtener el id de una opinion desde atributos HTML comunes.

    Args:
        node: Nodo de BeautifulSoup que representa una opinion.

    Returns:
        Identificador numerico de la opinion, o ``None`` si no se encuentra.
    """
    for attr in ["data-opinion-id", "data-review-id", "data-id", "id"]:
        value = node.get(attr)
        value = convertir_entero(value)
        if value:
            return value
    return None


def extract_rating(node) -> float | None:
    """Extrae la calificacion de una opinion.

    La funcion prueba varias fuentes: metadatos ``itemprop``, atributos
    ``data-score``/``data-rating`` y texto visible con formatos como ``5/5`` o
    ``5 estrellas``.

    Args:
        node: Nodo de BeautifulSoup que representa una opinion.

    Returns:
        Calificacion como decimal, o ``None`` si no se detecta.
    """
    rating_meta = node.select_one("[itemprop='ratingValue']")
    if rating_meta and rating_meta.get("content"):
        return convertir_decimal(rating_meta.get("content"))

    rating_node = node.select_one(".rating, [data-score], [data-rating]")
    if rating_node:
        return convertir_decimal(
            rating_node.get("data-score") or rating_node.get("data-rating")
        )

    rating_text = node.get_text(" ", strip=True)
    match = None
    for pattern in [r"([0-5](?:\.\d+)?)\s*/\s*5", r"([0-5](?:\.\d+)?)\s*estrellas?"]:
        match = re.search(pattern, rating_text, re.IGNORECASE)
        if match:
            break
    return convertir_decimal(match.group(1)) if match else None


def extract_review_fields(node) -> dict:
    """Extrae los campos principales de una opinion.

    Lee el autor, rating, texto, fecha, servicio consultado, consultorio y tipo
    de verificacion desde el bloque HTML de una opinion. La funcion esta
    adaptada a la estructura que Doctoralia usa en sus bloques
    ``data-test-id='opinion-block'``.

    Args:
        node: Nodo de BeautifulSoup correspondiente a una opinion.

    Returns:
        Diccionario con las claves ``opinion_id``, ``autor``, ``rating``,
        ``texto``, ``fecha``, ``servicio_consultado``, ``consultorio`` y
        ``tipo_verificacion``.
    """
    # opinion_id
    opinion_id = convertir_entero(node.get("data-id"))

    # autor — itemprop="name" dentro del h4 con itemprop="author"
    autor_node = node.select_one(
        "h4[itemprop='author'] [itemprop='name'], h4[itemprop='author']"
    )
    autor = limpiar_texto(autor_node.get_text(" ", strip=True)) if autor_node else None

    # rating — div con data-score
    rating_node = node.select_one("[data-score]")
    rating = convertir_decimal(rating_node.get("data-score")) if rating_node else None

    # texto — p con itemprop="reviewBody"
    texto_node = node.select_one("[itemprop='reviewBody']")
    texto = limpiar_texto(texto_node.get_text(" ", strip=True)) if texto_node else None

    # fecha — time con itemprop="datePublished"
    fecha_node = node.select_one("time[itemprop='datePublished']")
    fecha = fecha_node.get("datetime") if fecha_node else None

    # servicio — meta itemprop="name" dentro del bloque itemReviewed
    servicio_node = node.select_one("[itemprop='itemReviewed'] meta[itemprop='name']")
    servicio_raw = servicio_node.get("content") if servicio_node else None
    # El content viene como "RM Dental Center Endodoncia" — separar consultorio y servicio
    consultorio, servicio_consultado = None, None
    if servicio_raw:
        partes = servicio_raw.rsplit(" ", 1)
        if len(partes) == 2:
            consultorio, servicio_consultado = partes
        else:
            consultorio = servicio_raw

    # tipo_verificacion — badge con texto específico
    tipo_verificacion = None
    for badge in node.select("span.badge, button span"):
        texto_badge = badge.get_text(strip=True)
        if texto_badge in (
            "Cita verificada",
            "Pago y cita verificados",
            "Número de teléfono verificado",
        ):
            tipo_verificacion = texto_badge
            break

    return {
        "opinion_id": opinion_id,
        "autor": autor,
        "rating": rating,
        "texto": texto,
        "fecha_publicacion": fecha,
        "servicio_consultado": servicio_consultado,
        "consultorio": consultorio,
        "tipo_verificacion": tipo_verificacion,
    }


def parse_opinions(html_text: str) -> list[dict]:
    """Parsea HTML de opiniones y lo convierte en una lista de diccionarios.

    Args:
        html_text: HTML que contiene uno o varios bloques de opinion.

    Returns:
        Lista de opiniones extraidas. Cada elemento es el diccionario devuelto
        por ``extract_review_fields``.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    # Nodo raíz real de cada opinión
    candidates = soup.select("[data-test-id='opinion-block']")
    return [
        extract_review_fields(node) for node in candidates if node.get_text(strip=True)
    ]


def construir_resultado_opiniones(
    doctor_id: int,
    total_opiniones: int,
    max_opiniones: int | None = None,
    url_perfil: str | None = None,
    es_clinica: bool | None = None,
) -> dict:
    """Descarga varias paginas de opiniones y arma el resultado final.

    Cada opinion incluye un campo ``scraping_meta`` con la URL de origen, el
    numero de pagina, el total de paginas y la fecha de extraccion, siguiendo
    el esquema del ``index.ts``.

    Args:
        doctor_id: Identificador interno del doctor en Doctoralia.
        total_opiniones: Total de opiniones conocido para ese doctor.
        max_opiniones: Limite opcional de opiniones a extraer. Si es ``None``,
            intenta extraer todas las disponibles segun ``total_opiniones``.
        url_perfil: URL del perfil del doctor para incluir en ``scraping_meta``.
        es_clinica: True si el perfil pertenece a una clínica/centro.

    Returns:
        Diccionario con ``meta`` y ``opiniones``. ``meta`` incluye totales,
        limite aplicado y fecha de extraccion. Cada opinion en ``opiniones``
        tiene ``scraping_meta`` con ``url``, ``page``, ``total_pages`` y
        ``fecha_extraccion``.
    """
    if es_clinica is None and url_perfil:
        url_lower = url_perfil.lower()
        if any(w in url_lower for w in ["/clinica", "/centro-", "/facility", "/hospital", "/sanatorio"]):
            es_clinica = True

    # Primera pagina para determinar total real de paginas y si el endpoint efectivo es de clínica
    first_html, num_rows_real, limit_por_pagina, es_fac_real = fetch_pagina_opiniones(
        doctor_id, 1, es_clinica=es_clinica
    )
    if num_rows_real > 0:
        total_opiniones = num_rows_real
    if limit_por_pagina <= 0:
        limit_por_pagina = 10

    total_paginas = (
        math.ceil(total_opiniones / limit_por_pagina) if total_opiniones else 0
    )

    # Si hay limite, calcular cuantas paginas necesitamos realmente
    if max_opiniones is not None:
        paginas_necesarias = math.ceil(max_opiniones / limit_por_pagina)
        total_paginas = min(total_paginas, paginas_necesarias)

    fecha_extraccion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    base_url_activa = BASE_URL_FACILITY if es_fac_real else BASE_URL
    base_url_opinion = f"{base_url_activa}/{doctor_id}"
    all_opinions: list[dict] = []

    def _enriquecer(opinion: dict, page: int, t_pages: int) -> dict:
        """Agrega ``doctor_id`` y ``scraping_meta`` a una opinion."""
        url_pagina = f"{base_url_opinion}/{page}"
        return {
            **opinion,
            "doctor_id": doctor_id,
            "scraping_meta": {
                "url": url_pagina,
                "page": page,
                "total_pages": t_pages,
                "fecha_extraccion": fecha_extraccion,
            },
        }

    # Procesar primera pagina ya descargada
    for op in parse_opinions(first_html):
        all_opinions.append(_enriquecer(op, 1, total_paginas))

    if max_opiniones is not None and len(all_opinions) >= max_opiniones:
        all_opinions = all_opinions[:max_opiniones]
    else:
        for page in range(2, total_paginas + 1):
            time.sleep(random.uniform(1, 2))
            html_text, _, _, _ = fetch_pagina_opiniones(
                doctor_id, page, es_clinica=es_fac_real
            )
            for op in parse_opinions(html_text):
                all_opinions.append(_enriquecer(op, page, total_paginas))

            if max_opiniones is not None and len(all_opinions) >= max_opiniones:
                all_opinions = all_opinions[:max_opiniones]
                break

    meta = {
        "doctor_id": doctor_id,
        "total_opiniones": total_opiniones,
        "total_paginas": total_paginas,
        "opiniones_extraidas": len(all_opinions),
        "limite_aplicado": max_opiniones is not None,
        "fecha_extraccion": fecha_extraccion,
    }

    return {
        "meta": meta,
        "opiniones": all_opinions,
    }


def save_reviews(result: dict, output_path: Path) -> None:
    """Guarda el resultado de opiniones como JSON.

    Args:
        result: Diccionario con metadatos y opiniones.
        output_path: Ruta donde se escribira el archivo JSON.

    Returns:
        None.

    Side Effects:
        Crea directorios padres si no existen y sobrescribe el archivo destino.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    """Punto de entrada para ejecutar el scraper de opiniones por CLI.

    Lee el id del doctor, el total de opiniones y un limite opcional desde la
    consola. Luego descarga las opiniones y guarda el JSON dentro de fixtures.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("doctor_id", type=int)
    parser.add_argument("total_opiniones", type=int)
    parser.add_argument(
        "max_opiniones",
        type=int,
        nargs="?",
        default=None,
        help="Límite de opiniones a extraer (posicional opcional).",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        dest="max_opiniones_flag",
        help="Límite de opiniones a extraer. Sin este flag se extraen todas.",
    )
    args = parser.parse_args()

    output_path = FIXTURES_DIR / f"opiniones2_{args.doctor_id}.json"
    max_opiniones = (
        args.max_opiniones
        if args.max_opiniones is not None
        else args.max_opiniones_flag
    )
    result = construir_resultado_opiniones(
        args.doctor_id,
        args.total_opiniones,
        max_opiniones,
    )
    save_reviews(result, output_path)


if __name__ == "__main__":
    main()
