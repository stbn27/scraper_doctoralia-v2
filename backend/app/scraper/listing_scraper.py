import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.scraper.utils.base import get_user_agent


ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT_DIR / "fixtures"
DEFAULT_HTML_PATH = FIXTURES_DIR / "views" / "listado.html"
BASE_DOMAIN = "https://www.doctoralia.com.mx"


def clean_text(text: str | None) -> str | None:
    """Limpia texto eliminando espacios repetidos.

    Args:
        text: Texto original o ``None``.

    Returns:
        Texto sin espacios sobrantes, o ``None`` si no queda contenido util.
    """
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def clean_url(url: str, base_url: str = BASE_DOMAIN) -> str:
    """Normaliza una URL de Doctoralia.

    Convierte URLs relativas o que empiezan con ``//`` en URLs absolutas y
    elimina parametros de consulta y fragmentos. Esto permite comparar enlaces
    aunque vengan escritos de formas ligeramente distintas.

    Args:
        url: URL original encontrada en el HTML.
        base_url: Dominio base usado para resolver URLs relativas.

    Returns:
        URL absoluta sin query string ni fragmento.
    """
    if url.startswith("//"):
        url = f"https:{url}"
    if url.startswith("/"):
        url = urljoin(base_url, url)
    parsed = urlparse(url)
    return parsed._replace(query="", fragment="").geturl()


def parse_int(value: str | int | float | None) -> int | None:
    """Convierte un valor a entero cuando es posible.

    Args:
        value: Numero o texto que representa un numero. Puede ser ``None``.

    Returns:
        Entero convertido, o ``None`` si la entrada no se puede interpretar
        como numero.
    """
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def parse_float(value: str | int | float | None) -> float | None:
    """Convierte un valor a decimal cuando es posible.

    Args:
        value: Numero o texto que representa un numero decimal.

    Returns:
        Valor ``float`` convertido, o ``None`` si la conversion falla.
    """
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def empty_doctor() -> dict:
    """Crea la estructura base para representar un doctor del listado.

    El diccionario incluye todas las claves esperadas por el extractor, con
    valores iniciales en ``None``. Usar esta plantilla evita que cada funcion
    tenga que validar si una clave existe antes de escribir datos.

    Returns:
        Diccionario con campos de identificacion, perfil, rating, direccion,
        consultorio y servicio destacado.
    """
    return {
        "doctoralia_id": None,
        "nombre": None,
        "url_perfil": None,
        "foto_url": None,
        "especialidades": None,
        "calificacion": None,
        "num_opiniones": None,
        "tiene_calendario": None,
        "es_online_only": None,
        "direccion": {
            "calle": None,
            "alcaldia": None,
            "estado": None,
            "lat": None,
            "lng": None,
        },
        "consultorio": None,
        "servicio_destacado": {
            "nombre": None,
            "precio": None,
            "moneda": None,
        },
    }


def normalize_specialties(value) -> list[str] | None:
    """Normaliza una o varias especialidades a lista de textos.

    Doctoralia puede entregar especialidades como lista o como texto separado
    por comas. Esta funcion acepta ambas formas, limpia cada elemento y descarta
    valores vacios.

    Args:
        value: Lista, cadena separada por comas o ``None``.

    Returns:
        Lista de especialidades limpias, o ``None`` si no hay datos validos.
    """
    if value is None:
        return None
    if isinstance(value, list):
        items = [clean_text(item) for item in value]
        return [item for item in items if item] or None
    if isinstance(value, str):
        items = [clean_text(item) for item in value.split(",")]
        return [item for item in items if item] or None
    return None


def parse_available_service(value: dict | list | None) -> dict:
    """Extrae el servicio destacado desde datos JSON-LD.

    El campo ``availableService`` puede llegar como diccionario, como lista de
    diccionarios o no existir. Esta funcion toma el primer servicio disponible
    y lee su nombre, precio y moneda.

    Args:
        value: Valor del campo ``availableService`` obtenido desde JSON-LD.

    Returns:
        Diccionario con ``nombre``, ``precio`` y ``moneda``. Si falta
        informacion, esas claves quedan en ``None``.
    """
    service = {"nombre": None, "precio": None, "moneda": None}
    if not value:
        return service
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, dict):
        return service

    service_name = clean_text(value.get("name"))
    offers = value.get("offers") or {}
    service["nombre"] = service_name
    service["precio"] = parse_int(offers.get("price"))
    service["moneda"] = clean_text(offers.get("priceCurrency"))
    return service


def extract_jsonld_items(soup: BeautifulSoup) -> list[dict]:
    """Obtiene items de doctores desde scripts JSON-LD tipo ItemList.

    JSON-LD es un bloque de datos estructurados incrustado en HTML. Doctoralia
    lo usa para publicar informacion que tambien aparece visualmente en la
    pagina. Esta funcion localiza scripts ``application/ld+json`` y conserva
    los elementos dentro de ``itemListElement``.

    Args:
        soup: HTML del listado parseado con BeautifulSoup.

    Returns:
        Lista de diccionarios que representan items encontrados en JSON-LD.
        Los scripts con JSON invalido se ignoran.
    """
    items: list[dict] = []
    for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not node.string:
            continue
        try:
            data = json.loads(node.string)
        except json.JSONDecodeError:
            continue

        if isinstance(data, list):
            candidates = data
        else:
            candidates = [data]

        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            if entry.get("@type") != "ItemList":
                continue
            elements = entry.get("itemListElement") or []
            for element in elements:
                if not isinstance(element, dict):
                    continue
                item = element.get("item") if "item" in element else element
                if not isinstance(item, dict):
                    continue
                items.append(item)
    return items


def extract_doctors_from_jsonld(soup: BeautifulSoup) -> dict[str, dict]:
    """Extrae doctores usando los datos estructurados JSON-LD.

    Esta fuente suele contener nombre, URL de perfil, foto, especialidades,
    rating, numero de opiniones, direccion y servicio destacado.

    Args:
        soup: HTML del listado parseado con BeautifulSoup.

    Returns:
        Diccionario indexado por URL de perfil. Cada valor sigue la estructura
        creada por ``empty_doctor``.
    """
    doctors: dict[str, dict] = {}
    for item in extract_jsonld_items(soup):
        url = item.get("url")
        if not url:
            continue
        url = clean_url(url)

        doctor = empty_doctor()
        doctor["nombre"] = clean_text(item.get("name"))
        doctor["url_perfil"] = url

        image_url = item.get("image")
        if isinstance(image_url, str):
            doctor["foto_url"] = clean_url(image_url)

        doctor["especialidades"] = normalize_specialties(item.get("medicalSpecialty"))

        rating = item.get("aggregateRating") or {}
        if isinstance(rating, dict):
            doctor["calificacion"] = parse_float(rating.get("ratingValue"))
            doctor["num_opiniones"] = parse_int(rating.get("reviewCount"))

        address = item.get("address") or {}
        if isinstance(address, dict):
            doctor["direccion"]["calle"] = clean_text(address.get("streetAddress"))
            doctor["direccion"]["alcaldia"] = clean_text(address.get("addressLocality"))
            doctor["direccion"]["estado"] = clean_text(address.get("addressRegion"))

        doctor["servicio_destacado"] = parse_available_service(
            item.get("availableService")
        )

        doctors[url] = doctor

    return doctors


def extract_doctors_from_html(soup: BeautifulSoup) -> dict[str, dict]:
    """Extrae doctores desde las tarjetas visibles del HTML.

    Esta funcion lee atributos ``data-*`` y metadatos dentro de cada tarjeta del
    listado. Suele aportar datos que JSON-LD no siempre incluye, como id interno,
    disponibilidad de calendario, modalidad online y coordenadas.

    Args:
        soup: HTML del listado parseado con BeautifulSoup.

    Returns:
        Diccionario indexado por URL de perfil. Cada valor sigue la estructura
        creada por ``empty_doctor``.
    """
    doctors: dict[str, dict] = {}
    for card in soup.select("[data-test-id='result-item']"):
        doctor = empty_doctor()

        raw_url = card.get("data-doctor-url")
        if not raw_url:
            continue
        url = clean_url(raw_url)

        doctor["doctoralia_id"] = parse_int(card.get("data-result-id"))
        doctor["nombre"] = clean_text(card.get("data-doctor-name"))
        doctor["url_perfil"] = url

        doctor["tiene_calendario"] = card.has_attr("data-eec-has-calendar-with-slots")
        online_attr = (card.get("data-is-online-only") or "").strip().lower()
        doctor["es_online_only"] = online_attr == "true"

        address_item = card.select_one("[data-id='result-address-item']")
        if address_item:
            doctor["direccion"]["lat"] = parse_float(address_item.get("data-lat"))
            doctor["direccion"]["lng"] = parse_float(address_item.get("data-lng"))

            street_meta = address_item.select_one("meta[data-test-id='street-address']")
            locality_meta = address_item.select_one("meta[data-test-id='city-address']")
            region_meta = address_item.select_one("meta[data-test-id='province-address']")

            doctor["direccion"]["calle"] = clean_text(
                street_meta.get("content") if street_meta else None
            )
            doctor["direccion"]["alcaldia"] = clean_text(
                locality_meta.get("content") if locality_meta else None
            )
            doctor["direccion"]["estado"] = clean_text(
                region_meta.get("content") if region_meta else None
            )

            consultorio = address_item.select_one(
                ".address-details[data-test-id='entity-name'],"
                ".address-details[data-test-id='identity-name']"
            )
            doctor["consultorio"] = clean_text(
                consultorio.get_text(" ", strip=True) if consultorio else None
            )

        doctors[url] = doctor

    return doctors


def merge_doctors(jsonld: dict[str, dict], html: dict[str, dict]) -> list[dict]:
    """Combina doctores extraidos desde JSON-LD y desde HTML.

    Usa la URL de perfil como identificador. Primero toma la informacion de
    JSON-LD y luego completa o reemplaza campos con datos del HTML cuando estos
    no son ``None``. Los doctores encontrados solo en HTML tambien se incluyen.

    Args:
        jsonld: Doctores extraidos desde datos estructurados.
        html: Doctores extraidos desde tarjetas HTML.

    Returns:
        Lista de doctores combinados, sin duplicados por URL.
    """
    merged: list[dict] = []
    seen: set[str] = set()

    for url, jsonld_doctor in jsonld.items():
        combined = empty_doctor()
        combined.update(jsonld_doctor)

        html_doctor = html.get(url)
        if html_doctor:
            for key, value in html_doctor.items():
                if value is None:
                    continue
                if key in {"direccion", "servicio_destacado"}:
                    continue
                combined[key] = value

            if html_doctor.get("direccion"):
                for key, value in html_doctor["direccion"].items():
                    if value is not None:
                        combined["direccion"][key] = value

            if html_doctor.get("servicio_destacado"):
                for key, value in html_doctor["servicio_destacado"].items():
                    if value is not None:
                        combined["servicio_destacado"][key] = value

        merged.append(combined)
        seen.add(url)

    for url, html_doctor in html.items():
        if url in seen:
            continue
        merged.append(html_doctor)

    return merged


def extract_pagination(soup: BeautifulSoup) -> tuple[int | None, int | None]:
    """Lee la pagina actual y el total de paginas del listado.

    Busca contenedores comunes de paginacion y revisa el elemento marcado como
    actual. Para el total, recorre los numeros visibles y conserva el ultimo
    numero valido encontrado.

    Args:
        soup: HTML del listado parseado con BeautifulSoup.

    Returns:
        Tupla ``(pagina_actual, total_paginas)``. Cada valor puede ser ``None``
        si no se encuentra en el HTML.
    """
    pagination = (
        soup.select_one("[data-test-id='pagination']")
        or soup.select_one("[data-test-id='listing-pagination']")
        or soup.select_one("ul.pagination")
    )
    if not pagination:
        return None, None

    current_page = None
    current_node = pagination.select_one("[aria-current='page']")
    if current_node:
        current_page = parse_int(current_node.get_text(strip=True))
    if current_page is None:
        active = pagination.select_one("li.active")
        if active:
            current_page = parse_int(active.get_text(strip=True))

    total_page = None
    for li in pagination.select("li"):
        value = parse_int(li.get_text(strip=True))
        if value:
            total_page = value

    return current_page, total_page


def build_listing_result(
    html_text: str,
    source_path: Path,
    specialty_slug: str,
    city_slug: str,
    page: int,
) -> dict:
    """Construye el resultado final de un listado de doctores.

    Parsear un listado implica juntar varias fuentes: JSON-LD, tarjetas HTML y
    paginacion. Esta funcion coordina esas extracciones y agrega metadatos como
    especialidad, ciudad, pagina, fuente y fecha.

    Args:
        html_text: HTML completo del listado.
        source_path: Ruta local o identificador de la fuente analizada.
        specialty_slug: Slug de especialidad usado en la busqueda.
        city_slug: Slug de ciudad usado en la busqueda.
        page: Numero de pagina solicitado originalmente.

    Returns:
        Diccionario con ``meta`` y ``doctores``.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    jsonld_doctors = extract_doctors_from_jsonld(soup)
    html_doctors = extract_doctors_from_html(soup)
    doctors = merge_doctors(jsonld_doctors, html_doctors)

    current_page, total_page = extract_pagination(soup)
    if current_page is None:
        current_page = page

    base_url = f"{BASE_DOMAIN}/{specialty_slug}/{city_slug}"

    try:
        fuente = source_path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        fuente = source_path.as_posix()

    meta = {
        "especialidad_slug": specialty_slug,
        "ciudad_slug": city_slug,
        "url_base": base_url,
        "pagina_actual": current_page,
        "total_paginas": total_page,
        "total_doctores_pagina": len(doctors),
        "fuente": fuente,
        "fecha_extraccion": datetime.now().isoformat(timespec="seconds"),
    }

    return {
        "meta": meta,
        "doctores": doctors,
    }


def save_listing(result: dict, output_path: Path) -> None:
    """Guarda un resultado de listado como JSON.

    Args:
        result: Diccionario devuelto por ``build_listing_result``.
        output_path: Ruta destino del archivo JSON.

    Returns:
        None.

    Side Effects:
        Crea directorios padres si no existen y sobrescribe el archivo destino.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def fetch_listing_html(specialty_slug: str, city_slug: str, page: int) -> str:
    """Descarga el HTML de una pagina de listado de Doctoralia.

    Args:
        specialty_slug: Slug de la especialidad, por ejemplo ``endodoncia``.
        city_slug: Slug de la ciudad, por ejemplo ``ciudad-de-mexico``.
        page: Numero de pagina que se quiere descargar.

    Returns:
        HTML recibido desde Doctoralia.

    Raises:
        httpx.HTTPStatusError: Si Doctoralia responde con error HTTP.
        httpx.RequestError: Si falla la conexion o vence el timeout.
    """
    headers = {
        "User-Agent": get_user_agent(),
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    url = f"{BASE_DOMAIN}/{specialty_slug}/{city_slug}?page={page}"
    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def extract_from_file(
    html_path: Path,
    specialty_slug: str,
    city_slug: str,
    page: int,
) -> dict:
    """Extrae doctores desde un archivo HTML local.

    Args:
        html_path: Ruta al archivo HTML previamente guardado.
        specialty_slug: Slug de especialidad que se asociara al resultado.
        city_slug: Slug de ciudad que se asociara al resultado.
        page: Numero de pagina que se asociara al resultado.

    Returns:
        Diccionario con metadatos y lista de doctores extraidos.
    """
    html_text = html_path.read_text(encoding="utf-8")
    return build_listing_result(html_text, html_path, specialty_slug, city_slug, page)


def scrape_listing(
    specialty_slug: str,
    city_slug: str,
    page: int,
) -> tuple[dict, int | None]:
    """Descarga y parsea una pagina de listado desde Doctoralia.

    Args:
        specialty_slug: Slug de la especialidad buscada.
        city_slug: Slug de la ciudad buscada.
        page: Numero de pagina a descargar.

    Returns:
        Tupla ``(resultado, total_paginas)``. ``resultado`` contiene ``meta`` y
        ``doctores``. ``total_paginas`` puede ser ``None`` si no se detecto
        paginacion.
    """
    html_text = fetch_listing_html(specialty_slug, city_slug, page)
    source_path = Path(f"{BASE_DOMAIN}/{specialty_slug}/{city_slug}?page={page}")
    result = build_listing_result(html_text, source_path, specialty_slug, city_slug, page)
    total_pages = result["meta"].get("total_paginas")
    return result, total_pages


async def scrape_listing_async(
    specialty_slug: str,
    city_slug: str,
    page: int,
) -> tuple[dict, int | None]:
    """Descarga y parsea una página de listado de Doctoralia de forma asíncrona.

    Versión async de ``scrape_listing`` diseñada para el pipeline masivo.
    Usa ``httpx.AsyncClient`` con rotación de User-Agent. El parsing se delega
    a ``build_listing_result``, que es síncrono y puede llamarse directamente.

    Args:
        specialty_slug: Slug de la especialidad buscada, por ejemplo
            ``"endodoncia"``.
        city_slug: Slug de la ciudad buscada, por ejemplo
            ``"ciudad-de-mexico"``.
        page: Número de página a descargar (empieza en 1).

    Returns:
        Tupla ``(resultado, total_paginas)``. ``resultado`` contiene ``meta`` y
        ``doctores``. ``total_paginas`` puede ser ``None`` si el HTML no
        incluye paginación visible.

    Raises:
        httpx.HTTPStatusError: Si Doctoralia responde con error HTTP.
        httpx.RequestError: Si falla la conexión o vence el timeout.

    Ejemplo::

        resultado, total = await scrape_listing_async("endodoncia", "ciudad-de-mexico", 1)
        print(total)          # 5
        print(len(resultado["doctores"]))   # 17
    """
    headers = {
        "User-Agent": get_user_agent(),
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    url = f"{BASE_DOMAIN}/{specialty_slug}/{city_slug}?page={page}"
    async with httpx.AsyncClient(timeout=30) as cliente:
        respuesta = await cliente.get(url, headers=headers)
        respuesta.raise_for_status()
        html_text = respuesta.text

    source_path = Path(url)
    resultado = build_listing_result(html_text, source_path, specialty_slug, city_slug, page)
    total_paginas = resultado["meta"].get("total_paginas")
    return resultado, total_paginas


def main() -> None:

    """Punto de entrada para ejecutar el extractor de listados por CLI.

    Lee argumentos de consola, decide si usar un archivo local o descargar desde
    internet, y guarda el resultado en ``fixtures``.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--especialidad", default="endodoncia")
    parser.add_argument("--ciudad", default="ciudad-de-mexico")
    parser.add_argument("--pagina", type=int, default=1)
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args()

    output_path = (
        FIXTURES_DIR
        / f"listado_{args.especialidad}_{args.ciudad}_p{args.pagina}.json"
    )

    if args.local:
        result = extract_from_file(DEFAULT_HTML_PATH, args.especialidad, args.ciudad, args.pagina)
    else:
        result, _ = scrape_listing(args.especialidad, args.ciudad, args.pagina)

    save_listing(result, output_path)


if __name__ == "__main__":
    main()
