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
