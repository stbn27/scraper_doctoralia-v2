from pathlib import Path

import httpx

from app.scraper.catalog_extractor import (
    DEFAULT_OUTPUT_PATH,
    FIXTURES_DIR,
    build_catalog,
    save_catalog,
)
from app.scraper.utils.base import get_user_agent


SEARCH_URL = "https://www.doctoralia.com.mx/buscar"
LATEST_HTML_PATH = FIXTURES_DIR / "views" / "inicio_doctoralia_latest.html"


def download_html(url: str) -> str:
    """Descarga el HTML de una URL usando cabeceras similares a un navegador.

    Esta funcion se usa para obtener la pagina inicial de Doctoralia desde
    internet. Define cabeceras HTTP basicas, como ``User-Agent`` e idioma, para
    que la peticion se parezca a la de un navegador real.

    Args:
        url: Direccion web completa que se quiere descargar.

    Returns:
        El contenido HTML de la pagina como texto.

    Raises:
        httpx.HTTPStatusError: Si el servidor responde con un codigo de error,
            por ejemplo 404, 403 o 500.
        httpx.RequestError: Si ocurre un problema de red, DNS o timeout.
    """
    headers = {
        "User-Agent": get_user_agent(),
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    response = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return response.text


def refresh_catalog() -> dict:
    """Actualiza el catalogo local de especialidades y ciudades.

    El flujo completo es:
    1. Descargar la pagina de busqueda de Doctoralia.
    2. Guardar una copia del HTML descargado en fixtures.
    3. Extraer especialidades, pares presenciales y opciones online.
    4. Guardar el catalogo resultante como JSON.

    Returns:
        Diccionario con la estructura del catalogo generado. Incluye la clave
        ``meta`` con totales y fecha de extraccion, ademas de listas de
        especialidades y rutas encontradas.

    Side Effects:
        Crea o sobrescribe el archivo HTML mas reciente y el JSON del catalogo.
        Tambien imprime un resumen en consola.
    """
    html_text = download_html(SEARCH_URL)
    LATEST_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_HTML_PATH.write_text(html_text, encoding="utf-8")

    catalog = build_catalog(html_text, LATEST_HTML_PATH)
    save_catalog(catalog, DEFAULT_OUTPUT_PATH)

    meta = catalog.get("meta", {})
    print(
        "Catalogo actualizado: "
        f"{meta.get('total_especialidades', 0)} especialidades, "
        f"{meta.get('total_pares_presencial', 0)} presenciales, "
        f"{meta.get('total_pares_online', 0)} online."
    )

    return catalog


if __name__ == "__main__":
    refresh_catalog()
