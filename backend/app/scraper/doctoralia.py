import json
import re
import httpx
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from app.scraper.utils.base import get_user_agent


def clean_text(value: str | None) -> str | None:
    """Limpia texto quitando espacios repetidos.

    Args:
        value: Texto original o ``None``.

    Returns:
        Texto con espacios normalizados, o ``None`` si la entrada esta vacia.
    """
    if not value:
        return None
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def safe_text(node):
    """Obtiene texto limpio de un nodo HTML de forma segura.

    Args:
        node: Nodo de BeautifulSoup o ``None``.

    Returns:
        Texto del nodo limpio, o ``None`` si el nodo no existe.
    """
    return clean_text(node.get_text(" ", strip=True)) if node else None


def normalize_context(text: str | None) -> str | None:
    """Normaliza texto de contexto de una opinion.

    Reemplaza separadores visuales, como puntos medios y barras verticales, por
    espacios normales. Despues compacta espacios repetidos.

    Args:
        text: Texto de contexto o ``None``.

    Returns:
        Texto normalizado, o ``None`` si no queda contenido.
    """
    if not text:
        return None
    text = text.replace("•", " ").replace("|", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def extract_number(text: str | None) -> int | None:
    """Extrae el primer numero entero encontrado en un texto.

    Args:
        text: Texto que puede contener numeros, por ejemplo ``"12 opiniones"``.

    Returns:
        Primer numero como entero, o ``None`` si no se encuentra.
    """
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
    """Extrae un precio en pesos desde un texto.

    Busca formatos como ``$ 1,200`` o ``$500`` y devuelve solo el numero.

    Args:
        text: Texto que puede contener un precio.

    Returns:
        Precio como entero, o ``None`` si no hay precio reconocible.
    """
    if not text:
        return None
    match = re.search(r"\$ ?([\d,]+)", text)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def first_text_by_selectors(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    """Devuelve el primer texto encontrado usando una lista de selectores CSS.

    Args:
        soup: Documento HTML parseado con BeautifulSoup.
        selectors: Lista de selectores CSS que se probaran en orden.

    Returns:
        Primer texto limpio encontrado, o ``None`` si ningun selector produce
        contenido.
    """
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = safe_text(node)
            if text:
                return text
    return None


def clean_address_parts(parts: list[str]) -> str | None:
    """Une partes de una direccion eliminando vacios y duplicados consecutivos.

    Args:
        parts: Lista de fragmentos de direccion, como calle, ciudad y codigo
            postal.

    Returns:
        Direccion completa como texto, o ``None`` si no hay partes validas.
    """
    cleaned_parts = []
    for p in parts:
        cleaned = clean_text(p)
        if cleaned:
            cleaned_parts.append(cleaned)

    if not cleaned_parts:
        return None

    merged = []
    for p in cleaned_parts:
        if not merged or merged[-1] != p:
            merged.append(p)

    text = ", ".join(merged)
    text = re.sub(
        r"(, Ciudad de México\s+04500, Ciudad de México, 04500)$",
        ", Ciudad de México 04500",
        text,
    )
    text = re.sub(r"\s+,", ",", text)
    return clean_text(text)


# Se cambia para evitar especialidades falsas desde secciones no relacionadas.
def extract_specialty(soup: BeautifulSoup) -> str | None:
    """Intenta detectar la especialidad principal del perfil.

    La funcion evita tomar titulos de secciones como "Opiniones" o "Servicios".
    Primero revisa selectores especificos del encabezado del doctor, despues
    busca cerca del ``h1`` y finalmente usa un fallback acotado al inicio del
    documento.

    Args:
        soup: HTML del perfil parseado con BeautifulSoup.

    Returns:
        Especialidad detectada, o ``None`` si no se encuentra una coincidencia
        confiable.
    """
    section_blacklist = {
        "consultorios",
        "articulos",
        "artículos",
        "experiencia",
        "opiniones",
        "servicios y precios",
        "servicios",
        "formacion",
        "formación",
        "sobre mi",
        "sobre mí",
        "novedades",
        "dudas solucionadas",
        "aseguradoras",
        "pacientes que atiendo",
        "tipos de consulta",
    }

    specialty_regex = re.compile(
        r"\b(cardi[oó]log[oa]|psic[oó]log[oa]|dermat[oó]log[oa]|tric[oó]log[oa]|ginec[oó]log[oa]|ur[oó]log[oa]|oftalm[oó]log[oa])\b",
        re.IGNORECASE,
    )

    def is_section_title(text: str | None) -> bool:
        """Indica si un texto parece ser titulo de seccion, no especialidad.

        Args:
            text: Texto candidato tomado del HTML.

        Returns:
            ``True`` si el texto esta vacio o contiene palabras de secciones
            conocidas que deben ignorarse. ``False`` si puede seguir evaluandose
            como posible especialidad.
        """
        if not text:
            return True
        low = text.lower().strip()
        return any(term in low for term in section_blacklist)

    def specialty_from_text(text: str | None) -> str | None:
        """Busca una especialidad medica dentro de un texto corto.

        Args:
            text: Texto donde se quiere buscar una especialidad.

        Returns:
            Nombre de la especialidad encontrada, o ``None`` si el texto es un
            titulo de seccion, esta vacio o no coincide con el patron esperado.
        """
        if not text:
            return None
        text = clean_text(text)
        if not text or is_section_title(text):
            return None
        m = specialty_regex.search(text)
        if m:
            return clean_text(m.group(1))
        return None

    def specialty_from_specialization_node(node) -> str | None:
        """Obtiene la especialidad desde el nodo especifico de Doctoralia."""
        text = safe_text(node)
        if not text or is_section_title(text):
            return None

        found = specialty_from_text(text)
        if found:
            return found

        candidate = re.split(
            r"\s*·\s*|Ver más|Ver mas",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        candidate = clean_text(candidate)
        return candidate if candidate and not is_section_title(candidate) else None

    # 1) Selectores específicos del header de especializaciones.
    selector_candidates = [
        "[data-test-id='doctor-specializations'] a[title]",
        "[data-test-id='doctor-specializations'] a",
        "[data-test-id='doctor-specializations']",
        "[data-test-id='doctor-specialty']",
        ".doctor-specialty",
        ".specialization",
    ]
    for selector in selector_candidates:
        for node in soup.select(selector):
            if "doctor-specializations" in selector:
                found = specialty_from_specialization_node(node)
            else:
                found = specialty_from_text(safe_text(node))
            if found:
                return found

    # 2) Búsqueda acotada al bloque superior del perfil (cerca del nombre).
    h1 = soup.select_one("h1")
    if h1:
        for parent in [h1, h1.parent, h1.parent.parent if h1.parent else None]:
            if not parent:
                continue
            for node in parent.select(
                "h2, h3, [data-test-id='doctor-specializations'], [data-test-id='doctor-specialty'], .doctor-specialty, .specialization"
            ):
                found = specialty_from_text(safe_text(node))
                if found:
                    return found

            found = specialty_from_text(parent.get_text(" ", strip=True)[:1200])
            if found:
                return found

    # 3) Fallback acotado al inicio del documento (evita coincidencia ciega global).
    top_text = clean_text(soup.get_text("\n", strip=True)[:2500])
    return specialty_from_text(top_text)


def extract_experiencia(soup: BeautifulSoup) -> list[str]:
    """Extrae lineas de experiencia profesional del perfil.

    La funcion toma el bloque de texto que empieza en "Experiencia" y termina
    antes de otras secciones conocidas. Luego limpia lineas, elimina encabezados
    repetidos y quita duplicados.

    Args:
        soup: HTML del perfil parseado con BeautifulSoup.

    Returns:
        Lista de textos de experiencia. Devuelve una lista vacia si no encuentra
        el bloque.
    """
    text = soup.get_text("\n", strip=True)

    m = re.search(
        r"Experiencia\s+(.*?)(?:\s+Enfocado en:|\s+Principales enfermedades tratadas|\s+Pacientes que atiendo|\s+Tipos de consulta)",
        text,
        re.DOTALL | re.IGNORECASE,
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
        "Sobre mí",
        "Novedades",
        "Dudas solucionadas",
    }

    results = []
    seen = set()
    for line in lines:
        if line in blacklist:
            continue
        if len(line) < 8:
            continue
        if re.fullmatch(r"[•\-\s]+", line):
            continue
        if line not in seen:
            seen.add(line)
            results.append(line)

    return results


def extract_profile_photo_url(soup: BeautifulSoup) -> str | None:
    """Extrae la URL de la foto de perfil del doctor.

    Si la imagen es la foto por defecto de Doctoralia, devuelve ``None``.
    Normaliza URLs protocol-relative que empiezan con ``//`` agregando ``https:``.

    Args:
        soup: HTML del perfil parseado con BeautifulSoup.

    Returns:
        URL absoluta de la foto de perfil, o ``None`` si no existe o es default.
    """

    def normalize_photo_url(image_url: str | None) -> str | None:
        image_url = clean_text(image_url)
        if not image_url:
            return None

        if image_url.startswith("//"):
            image_url = f"https:{image_url}"

        if "doctor-default" in image_url:
            return None

        if image_url.startswith("http://") or image_url.startswith("https://"):
            return image_url

        return None

    wrapper = soup.select_one(".unified-doctor-header-info__avatar-wrapper")
    if wrapper:
        image_candidates = wrapper.select(
            "[itemprop='image'], "
            ".unified-doctor-header-info__avatar, "
            ".avatar, "
            "a, "
            "img, "
            "[href], "
            "[content], "
            "[src], "
            "[data-src], "
            "[style]"
        )

        for image_node in image_candidates:
            image_url = (
                image_node.get("href")
                or image_node.get("content")
                or image_node.get("src")
                or image_node.get("data-src")
                or image_node.get("data-lazy-src")
                or image_node.get("data-original")
            )

            if not image_url:
                style = image_node.get("style", "")
                style_match = re.search(
                    r"url\(['\"]?(.*?)['\"]?\)",
                    style,
                    re.IGNORECASE,
                )
                if style_match:
                    image_url = style_match.group(1)

            normalized_url = normalize_photo_url(image_url)
            if normalized_url:
                return normalized_url

    fallback_selectors = [
        "meta[property='og:image']",
        "meta[name='twitter:image']",
        "meta[itemprop='image']",
    ]

    for selector in fallback_selectors:
        node = soup.select_one(selector)
        if not node:
            continue

        normalized_url = normalize_photo_url(node.get("content"))
        if normalized_url and "doctoralia.com.mx/doctor/" in normalized_url:
            return normalized_url

    full_html = str(soup)
    match = re.search(
        r"https?:\/\/s3\.us-east-1\.amazonaws\.com\/doctoralia\.com\.mx\/doctor\/[^\"'\s<>]+?\.(?:jpg|jpeg|png|webp)",
        full_html,
        re.IGNORECASE,
    )
    if match:
        return normalize_photo_url(match.group(0))

    match = re.search(
        r"\/\/s3\.us-east-1\.amazonaws\.com\/doctoralia\.com\.mx\/doctor\/[^\"'\s<>]+?\.(?:jpg|jpeg|png|webp)",
        full_html,
        re.IGNORECASE,
    )
    if match:
        return normalize_photo_url(match.group(0))

    return None


def extract_profile_header(soup: BeautifulSoup) -> dict:
    """Extrae datos generales del encabezado del perfil.

    Busca nombre, foto de perfil, especialidad, ciudad, cedulas profesionales,
    total de opiniones y rating global. Combina selectores HTML y busquedas por
    texto para tolerar cambios pequenos en la estructura de la pagina.

    Args:
        soup: HTML del perfil parseado con BeautifulSoup.

    Returns:
        Diccionario con ``nombre``, ``foto_perfil_url``, ``especialidad``,
        ``ciudad``, ``cedula``, ``cedulas``, ``total_opiniones`` y
        ``rating_global``.
    """
    full_text = soup.get_text("\n", strip=True)

    nombre = None
    h1 = soup.select_one("h1")
    if h1:
        nombre = safe_text(h1)

    if not nombre:
        title = soup.title.get_text(strip=True) if soup.title else ""
        if title:
            nombre = clean_text(title.split("|")[0].split("- Agenda")[0])

    foto_perfil_url = extract_profile_photo_url(soup)
    especialidad = extract_specialty(soup)
    header_candidates = []
    for sel in [
        "h2",
        "h3",
        "[data-test-id='doctor-specialty']",
        ".specialization",
        ".doctor-specialty",
    ]:
        for node in soup.select(sel):
            txt = safe_text(node)
            if txt:
                header_candidates.append(txt)

    ciudad = None
    if re.search(r"\bCiudad de México\b", full_text, re.IGNORECASE):
        ciudad = "Ciudad de México"

    cedulas = re.findall(r"No\.\s*de\s*cédula:\s*([0-9]+)", full_text, re.IGNORECASE)
    cedula = cedulas[0] if cedulas else None

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
        "foto_perfil_url": foto_perfil_url,
        "especialidad": especialidad,
        "ciudad": ciudad,
        "cedula": cedula,
        "cedulas": cedulas,
        "total_opiniones": total_opiniones,
        "rating_global": rating_global,
    }


# Se cambia para priorizar selectores HTML y dejar el texto como fallback.
def extract_services(soup: BeautifulSoup) -> list[dict]:
    """Extrae servicios y precios publicados en el perfil.

    Primero lee los items HTML del bloque de precios porque conservan mejor la
    relacion servicio/precio. Si no existen, intenta leer el bloque textual
    "Servicios y precios". Al final elimina duplicados exactos.

    Args:
        soup: HTML del perfil parseado con BeautifulSoup.

    Returns:
        Lista de diccionarios con ``nombre``, ``precio_desde`` y
        ``precio_texto``.
    """
    ignore = {
        "Servicios populares",
        "Otros servicios",
        "- - - - - - -",
        "- - -",
        "Detalles",
        "Agendar cita",
        "Agenda cita",
    }

    services = []

    service_nodes = soup.select("#profile-pricing [data-id='service-item']")
    if not service_nodes:
        service_nodes = soup.select(
            "[data-tab-id='profile-pricing'] [data-id='service-item']"
        )

    for node in service_nodes:
        nombre = safe_text(
            node.select_one(
                "h3[itemprop='availableService'], [itemprop='availableService'], h3"
            )
        )
        if not nombre or nombre in ignore:
            continue

        raw_text = node.get_text(" ", strip=True)
        price_match = re.search(
            r"(Desde\s*\$\s*[\d,]+|\$\s*\d[\d,]*(?:\s*-\s*\$\s*\d[\d,]*)?)",
            raw_text,
            re.IGNORECASE,
        )
        precio_texto = clean_text(price_match.group(1)) if price_match else None
        services.append(
            {
                "nombre": nombre,
                "precio_desde": extract_price(precio_texto) if precio_texto else None,
                "precio_texto": precio_texto,
            }
        )

    # Fallback: usar texto solo si el HTML no expuso items de servicio.
    if not services:
        text = soup.get_text("\n", strip=True)

        end_markers = (
            r"Consultorios(?:\s*\(\d+\))?",
            r"Opiniones",
            r"Experiencia",
            r"Formaci[oó]n",
            r"Aseguradoras(?:\s+aceptadas)?",
            r"Art[ií]culos",
            r"Sobre\s+m[ií]",
            r"Novedades",
            r"Dudas\s+solucionadas",
            r"Pacientes\s+que\s+atiendo",
            r"Tipos\s+de\s+consulta",
        )
        end_regex = "|".join(end_markers)

        patterns = [
            rf"Servicios y precios\s+(.*?)(?=\s+(?:{end_regex})|$)",
            r"(?s)Servicios y precios\s+(.*?)(?:\n\s*\n|$)",
        ]

        block = None
        for pat in patterns:
            matches = list(re.finditer(pat, text, re.DOTALL | re.IGNORECASE))
            if not matches:
                continue
            selected = None
            for m in matches:
                candidate = m.group(1)
                if re.search(r"\$\s*\d", candidate):
                    selected = candidate
                    break
            block = selected or matches[0].group(1)
            if block:
                break

        if block:
            lines = [clean_text(x) for x in block.split("\n")]
            lines = [x for x in lines if x]

            current_name = None
            for line in lines:
                if line in ignore:
                    continue

                is_price = bool(re.search(r"\$\s*\d", line))
                if is_price:
                    if current_name:
                        services.append(
                            {
                                "nombre": current_name,
                                "precio_desde": extract_price(line),
                                "precio_texto": line,
                            }
                        )
                        current_name = None
                    continue

                if len(line) > 3 and line.lower() not in {
                    "servicios y precios",
                    "servicios",
                }:
                    current_name = line

            if current_name:
                services.append(
                    {
                        "nombre": current_name,
                        "precio_desde": None,
                        "precio_texto": None,
                    }
                )

    unique = []
    seen = set()
    for item in services:
        key = (item["nombre"], item["precio_desde"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


def extract_addresses(soup: BeautifulSoup) -> list[dict]:
    """Extrae consultorios o direcciones del perfil.

    Revisa primero opciones de un selector desplegable y, si no hay resultados,
    busca secciones de direccion del doctor. Cada consultorio se devuelve con
    direccion y nombre de clinica cuando estan disponibles.

    Args:
        soup: HTML del perfil parseado con BeautifulSoup.

    Returns:
        Lista sin duplicados de diccionarios con ``direccion`` y ``clinica``.
    """
    consultorios = []

    options = soup.select(".multiselect__content .multiselect__option .media")
    if not options:
        options = soup.select(".multiselect__single .media")

    for opt in options:
        direccion = safe_text(opt.select_one("h5"))
        clinica = safe_text(opt.select_one(".text-muted"))

        if direccion and direccion.lower() != "ciudad de méxico":
            consultorios.append({"direccion": direccion, "clinica": clinica})

    if not consultorios:
        sections = soup.select('section[data-id="doctor-address-item"]')
        for sec in sections:
            clinica = safe_text(sec.select_one("span.h5, [class~='h5']"))
            if clinica and clinica.lower() == "pacientes que atiendo":
                clinica = None

            street = safe_text(sec.select_one('[itemprop="streetAddress"]'))
            city_node = sec.select_one('[itemprop="addressLocality"]')
            postal_node = sec.select_one('[itemprop="postalCode"]')

            city = city_node.get("content", "").strip() if city_node else ""
            postal = postal_node.get("content", "").strip() if postal_node else ""

            direccion = clean_address_parts([street, city, postal])
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
    """Extrae opiniones visibles directamente en el HTML del perfil.

    Esta funcion no llama al endpoint AJAX de opiniones; solo procesa los
    bloques ya presentes en el HTML recibido.

    Args:
        soup: HTML del perfil parseado con BeautifulSoup.
        limit: Cantidad maxima opcional de opiniones a devolver.

    Returns:
        Lista de opiniones con ``autor``, ``fecha``, ``rating``, ``texto`` y
        ``contexto``. Solo incluye opiniones que tienen texto.
    """
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


def extract_pacientes(soup: BeautifulSoup) -> dict:
    """Extrae el tipo de pacientes que atiende el doctor.

    Busca el bloque "Pacientes que atiendo" y revisa si menciona ninos,
    adultos o adolescentes. Tambien conserva las lineas originales encontradas.

    Args:
        soup: HTML del perfil parseado con BeautifulSoup.

    Returns:
        Diccionario con banderas booleanas ``atiende_ninos``,
        ``atiende_adultos``, ``atiende_adolescentes`` y ``texto_original``.
    """
    text = soup.get_text("\n", strip=True)

    m = re.search(
        r"Pacientes que atiendo\s+(.*?)\s+Tipos de consulta",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    values = []
    if m:
        block = m.group(1)
        lines = [clean_text(x) for x in block.split("\n")]
        values = [x for x in lines if x and len(x) > 2]

    joined = " | ".join(values).lower()

    return {
        "atiende_ninos": "niños" in joined or "ninos" in joined,
        "atiende_adultos": "adultos" in joined,
        "atiende_adolescentes": any(
            x in joined for x in ["adolescentes", "adolescente", "jóvenes", "jovenes"]
        ),
        "texto_original": values,
    }


def get_latest_review_date(reviews: list[dict]) -> str | None:
    """Obtiene la fecha mas reciente dentro de una lista de opiniones.

    Args:
        reviews: Lista de opiniones donde cada elemento puede tener la clave
            ``fecha``.

    Returns:
        Fecha maxima como texto, o ``None`` si ninguna opinion tiene fecha.
    """
    dates = [r.get("fecha") for r in reviews if r.get("fecha")]
    return max(dates) if dates else None


def parse_doctoralia_html(html: str, url: str | None = None) -> dict:
    """Parsea el HTML completo de un perfil de Doctoralia.

    Coordina todos los extractores del archivo para devolver un unico
    diccionario con datos generales, experiencia, servicios, consultorios,
    pacientes y metadatos de scraping.

    Args:
        html: Contenido HTML completo del perfil.
        url: URL de origen opcional. Se guarda en los metadatos.

    Returns:
        Diccionario con la informacion estructurada del perfil.
    """
    soup = BeautifulSoup(html, "lxml")

    data = extract_profile_header(soup)
    data["experiencia"] = extract_experiencia(soup)
    data["servicios"] = extract_services(soup)
    data["consultorios"] = extract_addresses(soup)
    # data["opiniones"] = []
    # data["opiniones"] = extract_reviews(soup, limit=limit_reviews)
    data["pacientes"] = extract_pacientes(soup)

    data["info_meta"] = {
        "total_servicios": len(data["servicios"]),
        "total_consultorios": len(data["consultorios"]),
        # "opiniones_extraidas": len(data["opiniones"]),
        # "ultima_opinion_fecha": get_latest_review_date(data["opiniones"]),
    }

    data["scraping_meta"] = {
        "url_origen": url,
        "fecha_consulta": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    return data


def parse_doctoralia_file(file_path: str | Path, url: str | None = None) -> dict:
    """Lee un archivo HTML local y parsea el perfil de Doctoralia.

    Args:
        file_path: Ruta del archivo HTML local.
        url: URL de origen opcional para registrar en metadatos.

    Returns:
        Diccionario del perfil parseado, incluyendo ``archivo_fuente``.
    """
    file_path = Path(file_path)
    html = file_path.read_text(encoding="utf-8", errors="ignore")
    result = parse_doctoralia_html(html, url=url)
    result["archivo_fuente"] = str(file_path)
    return result


def fetch_and_parse_profile(url: str) -> dict:
    """Descarga un perfil real de Doctoralia y lo parsea.

    Args:
        url: URL completa del perfil en Doctoralia.

    Returns:
        Diccionario estructurado del perfil, igual al que produce
        ``parse_doctoralia_html``.

    Raises:
        httpx.HTTPStatusError: Si el servidor responde con error HTTP.
        httpx.RequestError: Si ocurre un problema de red o timeout.
    """
    headers = {
        "User-Agent": get_user_agent(),
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
    response = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
    response.raise_for_status()
    result = parse_doctoralia_html(response.text, url=url)
    result.pop("archivo_fuente", None)  # no aplica en scraping real
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parser de perfiles Doctoralia")

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", help="Ruta a un archivo HTML local")
    source.add_argument("--url", help="URL real del perfil en Doctoralia")

    parser.add_argument(
        "--output", default="doctoralia_output.json", help="Archivo JSON de salida"
    )
    args = parser.parse_args()

    if args.file:
        data = parse_doctoralia_file(args.file, url=args.url)
    else:
        data = fetch_and_parse_profile(args.url)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK -> JSON guardado en: {args.output}")
    print(f"Nombre: {data.get('nombre')}")
