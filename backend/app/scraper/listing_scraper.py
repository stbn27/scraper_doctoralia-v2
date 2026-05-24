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
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def clean_url(url: str, base_url: str = BASE_DOMAIN) -> str:
    if url.startswith("//"):
        url = f"https:{url}"
    if url.startswith("/"):
        url = urljoin(base_url, url)
    parsed = urlparse(url)
    return parsed._replace(query="", fragment="").geturl()


def parse_int(value: str | int | float | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def parse_float(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def empty_doctor() -> dict:
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def fetch_listing_html(specialty_slug: str, city_slug: str, page: int) -> str:
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
    html_text = html_path.read_text(encoding="utf-8")
    return build_listing_result(html_text, html_path, specialty_slug, city_slug, page)


def scrape_listing(
    specialty_slug: str,
    city_slug: str,
    page: int,
) -> tuple[dict, int | None]:
    html_text = fetch_listing_html(specialty_slug, city_slug, page)
    source_path = Path(f"{BASE_DOMAIN}/{specialty_slug}/{city_slug}?page={page}")
    result = build_listing_result(html_text, source_path, specialty_slug, city_slug, page)
    total_pages = result["meta"].get("total_paginas")
    return result, total_pages


def main() -> None:
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
