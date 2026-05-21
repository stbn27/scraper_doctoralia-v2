import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


ROOT_DIR = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT_DIR / "fixtures"
DEFAULT_HTML_PATH = FIXTURES_DIR / "views" / "inicio_doctoralia.html"
DEFAULT_OUTPUT_PATH = FIXTURES_DIR / "catalogo_doctoralia.json"


# Slugs de especialidad que NO son especialidades médicas reales
BLOCKED_SPECIALTIES = {
    "gdpr",
    "social-connect",
    "login",
    "registro",
    "privacidad",
    "faq",
    "blog",
    "pro",
    "app-pacientes",
}


def clean_text(text: str | None) -> str | None:
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def slugify_name(name: str) -> str:
    text = unicodedata.normalize("NFD", name)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-]", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def extract_specialties(soup: BeautifulSoup) -> list[dict]:
    selectors = [
        "[data-test-id='dropdown-item'] .text-truncate",
        "[data-test-id='dropdown-item'] .capitalize",
        ".multiselect__option span.capitalize",
    ]

    names: list[str] = []
    for selector in selectors:
        for node in soup.select(selector):
            text = clean_text(node.get_text(" ", strip=True))
            if text:
                names.append(text)

    blacklist = {
        "especialidad",
        "especialidades",
        "buscar especialidad",
        "especialidad o tratamiento",
    }

    specialties: dict[str, dict] = {}
    for name in names:
        if name.lower() in blacklist:
            continue
        slug = slugify_name(name)
        if not slug:
            continue
        if slug not in specialties:
            specialties[slug] = {"nombre": name, "slug": slug}

    return list(specialties.values())


def canonical_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(query="", fragment="").geturl()


#def extract_pairs(soup: BeautifulSoup) -> tuple[list[dict], list[dict]]:
def extract_pairs(soup, known_slugs: set[str] | None = None):
    base_url = "https://www.doctoralia.com.mx"
    pairs: list[dict] = []
    online: list[dict] = []
    seen_pairs: set[str] = set()
    seen_online: set[str] = set()

    for node in soup.find_all("a", href=True):
        href = node.get("href")
        if not href:
            continue
        href = href.strip()
        if not href or href.startswith("#"):
            continue

        url = urljoin(base_url, href)
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not parsed.netloc.endswith("doctoralia.com.mx"):
            continue

        path = parsed.path.strip("/")
        if not path:
            continue

        segments = [seg for seg in path.split("/") if seg]
        if len(segments) != 2:
            continue

        specialty_slug, city_slug = segments
        clean_url = canonical_url(url)
        
        if specialty_slug in BLOCKED_SPECIALTIES:
            continue

        if known_slugs and specialty_slug not in known_slugs:
            continue

        if city_slug == "online":
            if clean_url in seen_online:
                continue
            online.append(
                {
                    "especialidad_slug": specialty_slug,
                    "modalidad": "online",
                    "url": clean_url,
                }
            )
            seen_online.add(clean_url)
            continue

        if clean_url in seen_pairs:
            continue

        texto = clean_text(node.get_text(" ", strip=True)) or city_slug
        pairs.append(
            {
                "especialidad_slug": specialty_slug,
                "ciudad_slug": city_slug,
                "url": clean_url,
                "texto_enlace": texto,
            }
        )
        seen_pairs.add(clean_url)

    return pairs, online


def build_catalog(html_text: str, source_path: Path) -> dict:
    soup = BeautifulSoup(html_text, "html.parser")
    specialties = extract_specialties(soup)
    pairs_presencial, pairs_online = extract_pairs(soup)

    if len(specialties) < 10:
        print("Advertencia: menos de 10 especialidades encontradas.")
    if len(pairs_presencial) < 20:
        print("Advertencia: menos de 20 pares presenciales encontrados.")

    try:
        fuente = source_path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        fuente = source_path.as_posix()

    meta = {
        "fuente": fuente,
        "fecha_extraccion": datetime.now().isoformat(timespec="seconds"),
        "total_especialidades": len(specialties),
        "total_pares_presencial": len(pairs_presencial),
        "total_pares_online": len(pairs_online),
    }

    return {
        "meta": meta,
        "especialidades": specialties,
        "pares_presencial": pairs_presencial,
        "pares_online": pairs_online,
    }


def save_catalog(catalog: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(catalog, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def extract_from_file(
    html_path: Path = DEFAULT_HTML_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> dict:
    html_text = html_path.read_text(encoding="utf-8")
    catalog = build_catalog(html_text, html_path)
    save_catalog(catalog, output_path)
    return catalog


if __name__ == "__main__":
    extract_from_file()
