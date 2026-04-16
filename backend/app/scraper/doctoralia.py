import json
import re
from pathlib import Path
from bs4 import BeautifulSoup


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_number(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d[\d,\.]*)", text.replace(",", ""))
    if not match:
        return None
    try:
        return int(float(match.group(1)))
    except ValueError:
        return None


def extract_price(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"\$ ?([\d,]+)", text)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def safe_text(node):
    return clean_text(node.get_text(" ", strip=True)) if node else None


def first_text_by_selectors(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = safe_text(node)
            if text:
                return text
    return None


def extract_profile_header(soup: BeautifulSoup) -> dict:
    full_text = soup.get_text("\n", strip=True)

    nombre = None
    h1 = soup.select_one("h1")
    if h1:
        nombre = safe_text(h1)

    if not nombre:
        title = soup.title.get_text(strip=True) if soup.title else ""
        if title:
            nombre = clean_text(title.split("|")[0].split("- Agenda")[0])

    especialidad = None
    possible_h2 = soup.find(
        lambda tag: tag.name in ["h2", "h3"] and tag.get_text(strip=True)
    )
    if possible_h2:
        txt = safe_text(possible_h2)
        if txt and "Cardiólogo" in txt:
            especialidad = "Cardiólogo"

    if not especialidad:
        m = re.search(r"\b(Cardiólogo|Cardiologo)\b", full_text, re.IGNORECASE)
        if m:
            especialidad = m.group(1)

    ciudad = None
    m = re.search(r"\bCiudad de México\b", full_text, re.IGNORECASE)
    if m:
        ciudad = "Ciudad de México"

    cedula = None
    m = re.search(r"No\.\s*de\s*cédula:\s*([0-9]+)", full_text, re.IGNORECASE)
    if m:
        cedula = m.group(1)

    total_opiniones = None
    review_count_meta = soup.select_one('[itemprop="reviewCount"]')
    if review_count_meta and review_count_meta.get("content"):
        total_opiniones = extract_number(review_count_meta.get("content"))

    if total_opiniones is None:
        m = re.search(r"(\d+)\s+opiniones", full_text, re.IGNORECASE)
        if m:
            total_opiniones = int(m.group(1))

    rating_global = None
    rating_meta = soup.select_one('[itemprop="ratingValue"]')
    if rating_meta and rating_meta.get("content"):
        try:
            rating_global = float(rating_meta.get("content"))
        except ValueError:
            rating_global = None

    return {
        "nombre": nombre,
        "especialidad": especialidad,
        "ciudad": ciudad,
        "cedula": cedula,
        "total_opiniones": total_opiniones,
        "rating_global": rating_global,
    }


def extract_experiencia(soup: BeautifulSoup) -> list[str]:
    text = soup.get_text("\n", strip=True)

    m = re.search(
        r"Experiencia\s+(.*?)\s+Enfocado en:", text, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return []

    block = m.group(1)
    lines = [clean_text(x) for x in block.split("\n")]
    lines = [x for x in lines if x]

    blacklist = {
        "Servicios y precios",
        "Consultorios",
        "Aseguradoras",
        "Opiniones",
        "Experiencia",
        "Formación",
    }

    results = []
    seen = set()
    for line in lines:
        if line in blacklist:
            continue
        if len(line) < 8:
            continue
        if line not in seen:
            seen.add(line)
            results.append(line)

    return results


def extract_services(soup: BeautifulSoup) -> list[dict]:
    text = soup.get_text("\n", strip=True)
    m = re.search(
        r"Servicios y precios\s+(.*?)\s+Consultorios\s*\(\d+\)",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if not m:
        return []

    block = m.group(1)
    lines = [clean_text(x) for x in block.split("\n")]
    lines = [x for x in lines if x]

    services = []
    current_name = None

    for line in lines:
        if line.startswith("Desde $"):
            if current_name:
                services.append(
                    {
                        "nombre": current_name,
                        "precio_desde": extract_price(line),
                        "precio_texto": line,
                    }
                )
                current_name = None
        else:
            if len(line) > 3 and line != "- - - - - - -":
                current_name = line

    unique = []
    seen = set()
    for item in services:
        key = (item["nombre"], item["precio_desde"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def extract_addresses(soup: BeautifulSoup) -> list[dict]:
    consultorios = []

    # 1) Fuente preferida: selector de "Agendar cita"
    options = soup.select(".multiselect__content .multiselect__option .media")
    if not options:
        options = soup.select(".multiselect__single .media")

    for opt in options:
        direccion_node = opt.select_one("h5")
        clinica_node = opt.select_one(".text-muted")

        direccion = safe_text(direccion_node)
        clinica = safe_text(clinica_node)

        if direccion:
            consultorios.append({"direccion": direccion, "clinica": clinica})

    # Deduplicar por dirección + clínica
    unique = []
    seen = set()
    for item in consultorios:
        key = (item["direccion"], item["clinica"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    if unique:
        return unique

    # 2) Fallback: bloque "Consultorios"
    sections = soup.select('section[data-id="doctor-address-item"]')

    for sec in sections:
        clinica_node = sec.select_one("span.h5")
        street_node = sec.select_one('[itemprop="streetAddress"]')
        city_node = sec.select_one('[itemprop="addressLocality"]')
        postal_node = sec.select_one('[itemprop="postalCode"]')

        clinica = safe_text(clinica_node)

        street = safe_text(street_node)
        city = city_node.get("content", "").strip() if city_node else ""
        postal = postal_node.get("content", "").strip() if postal_node else ""

        parts = [p for p in [street, city, postal] if p]
        direccion = ", ".join(parts) if parts else None

        if direccion:
            consultorios.append({"direccion": direccion, "clinica": clinica})

    unique = []
    seen = set()
    for item in consultorios:
        key = (item["direccion"], item["clinica"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def extract_reviews(soup: BeautifulSoup, limit: int | None = None) -> list[dict]:
    review_nodes = soup.select('[data-test-id="opinion-block"]')
    reviews = []

    for node in review_nodes:
        author = None
        author_node = node.select_one('[itemprop="author"] [itemprop="name"]')
        if author_node:
            author = safe_text(author_node)

        date_published = None
        date_node = node.select_one('[itemprop="datePublished"]')
        if date_node:
            date_published = date_node.get("datetime") or safe_text(date_node)

        rating = None
        rating_node = node.select_one(
            '[itemprop="reviewRating"] [itemprop="ratingValue"], [itemprop="ratingValue"]'
        )
        if rating_node:
            rating_raw = (
                rating_node.get("content")
                if rating_node.has_attr("content")
                else safe_text(rating_node)
            )
            try:
                rating = float(rating_raw)
            except (TypeError, ValueError):
                rating = None

        texto = None
        text_node = node.select_one(
            '[data-test-id="opinion-comment"], [itemprop="reviewBody"]'
        )
        if text_node:
            texto = safe_text(text_node)

        contexto = None
        small_texts = [safe_text(x) for x in node.select("span.small.text-muted")]
        small_texts = [x for x in small_texts if x]
        if small_texts:
            contexto = normalize_context(" | ".join(small_texts))

        review = {
            "autor": author,
            "fecha": date_published,
            "rating": rating,
            "texto": texto,
            "contexto": contexto,
        }

        if review["texto"]:
            reviews.append(review)

        if limit and len(reviews) >= limit:
            break

    return reviews


def parse_doctoralia_html(html: str, limit_reviews: int | None = None) -> dict:
    soup = BeautifulSoup(html, "lxml")

    data = extract_profile_header(soup)
    data["experiencia"] = extract_experiencia(soup)
    data["servicios"] = extract_services(soup)
    data["consultorios"] = extract_addresses(soup)
    data["opiniones"] = extract_reviews(soup, limit=limit_reviews)

    data["resumen_extraccion"] = {
        "total_servicios": len(data["servicios"]),
        "total_consultorios": len(data["consultorios"]),
        "opiniones_extraidas": len(data["opiniones"]),
    }

    return data


def parse_doctoralia_file(
    file_path: str | Path, limit_reviews: int | None = None
) -> dict:
    file_path = Path(file_path)
    html = file_path.read_text(encoding="utf-8", errors="ignore")
    result = parse_doctoralia_html(html, limit_reviews=limit_reviews)
    result["archivo_fuente"] = str(file_path)
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parser local de perfiles Doctoralia")
    parser.add_argument("html_file", help="Ruta al archivo HTML descargado")
    parser.add_argument(
        "--limit-reviews", type=int, default=10, help="Máximo de opiniones a extraer"
    )
    parser.add_argument(
        "--output", default="doctoralia_output.json", help="Archivo JSON de salida"
    )

    args = parser.parse_args()

    data = parse_doctoralia_file(args.html_file, limit_reviews=args.limit_reviews)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK -> JSON guardado en: {args.output}")
    print(f"Nombre: {data.get('nombre')}")
    print(f"Opiniones extraídas: {len(data.get('opiniones', []))}")


def normalize_context(text: str | None) -> str | None:
    if not text:
        return None
    text = text.replace("•", " ").replace("|", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None