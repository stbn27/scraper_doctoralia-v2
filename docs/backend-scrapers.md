# Backend: scrapers y utilidades

Esta documentación cubre los módulos Python de `backend/app/scraper` y `backend/test`. Los ejemplos son representativos y se enfocan en la forma de los datos que entra y sale.

## `app/scraper/catalog_extractor.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `clean_text(text)` | Texto o `None`. | Texto sin espacios repetidos, o `None`. | Entrada: `"  Cardio   logía "` -> salida: `"Cardio logía"` |
| `slugify_name(name)` | Nombre de especialidad o ciudad. | Slug sin acentos. | Entrada: `"Cirugía Plástica"` -> salida: `"cirugia-plastica"` |
| `extract_specialties(soup)` | `BeautifulSoup` de la página de búsqueda. | Lista de especialidades. | Salida: `[{"nombre": "Cardiólogo", "slug": "cardiologo"}]` |
| `canonical_url(url)` | URL con query o fragmento. | URL limpia. | Entrada: `"https://x/a?b=1#c"` -> salida: `"https://x/a"` |
| `extract_pairs(soup, known_slugs=None)` | `BeautifulSoup` y set opcional de slugs válidos. | Tupla `(presenciales, online)`. | Salida: `([{"especialidad_slug": "endodoncia", "ciudad_slug": "cdmx", "url": "..."}], [{"especialidad_slug": "psicologia", "modalidad": "online", "url": "..."}])` |
| `build_catalog(html_text, source_path)` | HTML y path fuente. | Catálogo completo con `meta`, `especialidades`, `pares_presencial`, `pares_online`. | Entrada: HTML de `/buscar` -> salida: `{"meta": {"total_especialidades": 50}, "especialidades": [...], ...}` |
| `save_catalog(catalog, output_path)` | Catálogo y path de salida. | `None`; escribe JSON. | Entrada: `catalog`, `fixtures/catalogo_doctoralia.json` -> salida: archivo JSON creado. |
| `extract_from_file(html_path=..., output_path=...)` | HTML local y path de salida. | Catálogo generado. | Entrada: `inicio_doctoralia.html` -> salida: `{"meta": ..., "especialidades": [...]}` |

## `app/scraper/catalog_refresher.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `download_html(url)` | URL a descargar. | HTML como `str`. | Entrada: `"https://www.doctoralia.com.mx/buscar"` -> salida: `"<html>..."` |
| `refresh_catalog()` | No recibe parámetros. | Catálogo generado desde la web. También guarda HTML latest y JSON. | Salida: `{"meta": {"total_especialidades": 50}, ...}` |

## `app/scraper/listing_scraper.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `clean_text(text)` | Texto o `None`. | Texto normalizado o `None`. | Entrada: `" Ana   Pérez "` -> salida: `"Ana Pérez"` |
| `clean_url(url, base_url=BASE_DOMAIN)` | URL relativa, protocol-relative o absoluta. | URL absoluta sin query ni fragmento. | Entrada: `"/ana?p=1#x"` -> salida: `"https://www.doctoralia.com.mx/ana"` |
| `parse_int(value)` | Texto, número o `None`. | `int` o `None`. | Entrada: `"15.0"` -> salida: `15` |
| `parse_float(value)` | Texto, número o `None`. | `float` o `None`. | Entrada: `"4.8"` -> salida: `4.8` |
| `empty_doctor()` | No recibe parámetros. | Dict base de doctor con campos en `None`. | Salida: `{"doctoralia_id": None, "nombre": None, "direccion": {...}}` |
| `normalize_specialties(value)` | Lista, string separado por comas o `None`. | Lista limpia o `None`. | Entrada: `"Endodoncia, Odontología"` -> salida: `["Endodoncia", "Odontología"]` |
| `parse_available_service(value)` | Dict/list JSON-LD con servicio. | Servicio normalizado. | Entrada: `{"name": "Consulta", "offers": {"price": "900", "priceCurrency": "MXN"}}` -> salida: `{"nombre": "Consulta", "precio": 900, "moneda": "MXN"}` |
| `extract_jsonld_items(soup)` | `BeautifulSoup`. | Items JSON-LD tipo `ItemList`. | Salida: `[{"name": "Dra. Ana", "url": "..."}]` |
| `extract_doctors_from_jsonld(soup)` | `BeautifulSoup`. | Dict por URL con doctores desde JSON-LD. | Salida: `{"https://.../ana": {"nombre": "Dra. Ana", ...}}` |
| `extract_doctors_from_html(soup)` | `BeautifulSoup`. | Dict por URL con doctores desde tarjetas HTML. | Salida: `{"https://.../ana": {"doctoralia_id": 123, "tiene_calendario": true, ...}}` |
| `merge_doctors(jsonld, html)` | Dos diccionarios por URL. | Lista combinada de doctores. | Entrada: datos JSON-LD y HTML de la misma URL -> salida: `[{"nombre": "Dra. Ana", "doctoralia_id": 123, ...}]` |
| `extract_pagination(soup)` | `BeautifulSoup`. | Tupla `(pagina_actual, total_paginas)`. | Salida: `(1, 8)` |
| `build_listing_result(html_text, source_path, specialty_slug, city_slug, page)` | HTML, fuente y contexto de búsqueda. | Dict con `meta` y `doctores`. | Entrada: HTML listado, `"endodoncia"`, `"cdmx"`, `1` -> salida: `{"meta": {...}, "doctores": [...]}` |
| `save_listing(result, output_path)` | Resultado y path. | `None`; escribe JSON. | Entrada: resultado, `fixtures/listado_...json` -> salida: archivo JSON. |
| `fetch_listing_html(specialty_slug, city_slug, page)` | Slugs y página. | HTML remoto. | Entrada: `"endodoncia"`, `"ciudad-de-mexico"`, `1` -> salida: `"<html>..."` |
| `extract_from_file(html_path, specialty_slug, city_slug, page)` | HTML local y contexto. | Resultado de listado. | Entrada: `listado.html`, `"endodoncia"`, `"cdmx"`, `1` -> salida: `{"meta": ..., "doctores": [...]}` |
| `scrape_listing(specialty_slug, city_slug, page)` | Slugs y página. | Tupla `(resultado, total_pages)`. | Entrada: `"endodoncia"`, `"cdmx"`, `1` -> salida: `({"doctores": [...]}, 8)` |
| `main()` | Argumentos CLI. | `None`; guarda JSON de listado. | Uso: `python -m app.scraper.listing_scraper --especialidad endodoncia --ciudad ciudad-de-mexico --pagina 1 --local` |

## `app/scraper/reviews_scraper.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `limpiar_texto(text)` | Texto o `None`. | Texto sin espacios repetidos o `None`. | Entrada: `" Muy   bien "` -> salida: `"Muy bien"` |
| `convertir_entero(value)` | Texto, número o `None`. | `int` o `None`. | Entrada: `"10.0"` -> salida: `10` |
| `convertir_decimal(value)` | Texto, número o `None`. | `float` o `None`. | Entrada: `"4.5"` -> salida: `4.5` |
| `fetch_pagina_opiniones(doctor_id, page)` | ID Doctoralia y página. | HTML de opiniones desde endpoint AJAX. | Entrada: `123`, `1` -> salida: `"<article ...>"` |
| `extract_opinion_id(node)` | Nodo HTML de opinión. | ID numérico o `None`. | Entrada: nodo con `data-opinion-id="10"` -> salida: `10` |
| `extract_rating(node)` | Nodo HTML de opinión. | Rating `float` o `None`. | Entrada: nodo con `data-score="5"` -> salida: `5.0` |
| `extract_review_fields(node)` | Nodo HTML de opinión. | Dict normalizado de opinión. | Salida: `{"opinion_id": 10, "autor": "Paciente", "rating": 5.0, "texto": "...", "fecha": "2026-05-01"}` |
| `parse_opinions(html_text)` | HTML de una página de opiniones. | Lista de opiniones. | Entrada: `"<div data-test-id='opinion-block'>..."` -> salida: `[{...}]` |
| `construir_resultado_opiniones(doctor_id, total_opiniones, max_opiniones=None)` | ID, total conocido y límite opcional. | Dict con `meta` y `opiniones`. | Entrada: `123`, `25`, `10` -> salida: `{"meta": {"opiniones_extraidas": 10}, "opiniones": [...]}` |
| `save_reviews(result, output_path)` | Resultado y path. | `None`; escribe JSON. | Entrada: resultado, `fixtures/opiniones2_123.json` -> salida: archivo JSON. |
| `main()` | Argumentos CLI. | `None`; scrapea y guarda opiniones. | Uso: `python -m app.scraper.reviews_scraper 123 40 --max 10` |

## `app/scraper/doctoralia.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `clean_text(value)` | Texto o `None`. | Texto limpio o `None`. | Entrada: `" Dra.   Ana "` -> salida: `"Dra. Ana"` |
| `safe_text(node)` | Nodo BeautifulSoup o `None`. | Texto limpio del nodo o `None`. | Entrada: `<h1>Dra. Ana</h1>` -> salida: `"Dra. Ana"` |
| `normalize_context(text)` | Texto contextual. | Texto sin separadores visuales repetidos. | Entrada: `"Consulta • Presencial | CDMX"` -> salida: `"Consulta Presencial CDMX"` |
| `extract_number(text)` | Texto con número. | `int` o `None`. | Entrada: `"42 opiniones"` -> salida: `42` |
| `extract_price(text)` | Texto con precio. | `int` o `None`. | Entrada: `"Desde $1,200"` -> salida: `1200` |
| `first_text_by_selectors(soup, selectors)` | `BeautifulSoup` y selectores CSS. | Primer texto encontrado. | Entrada: selectors `["h1", ".name"]` -> salida: `"Dra. Ana"` |
| `clean_address_parts(parts)` | Partes de dirección. | Dirección combinada. | Entrada: `["Av. X 1", "Ciudad de México", "04500"]` -> salida: `"Av. X 1, Ciudad de México, 04500"` |
| `extract_specialty(soup)` | HTML de perfil. | Especialidad principal o `None`. | Salida: `"Cardiólogo"` |
| `extract_profile_header(soup)` | HTML de perfil. | Datos principales del perfil. | Salida: `{"nombre": "Dra. Ana", "especialidad": "Endodoncia", "ciudad": "Ciudad de México", "total_opiniones": 42}` |
| `extract_experiencia(soup)` | HTML de perfil. | Lista de experiencia. | Salida: `["Especialista en endodoncia", "15 años de experiencia"]` |
| `extract_services(soup)` | HTML de perfil. | Lista de servicios con precio. | Salida: `[{"nombre": "Endodoncia", "precio_desde": 1200, "precio_texto": "Desde $1,200"}]` |
| `extract_addresses(soup)` | HTML de perfil. | Lista de consultorios. | Salida: `[{"direccion": "Av. X 1, CDMX", "clinica": "Clínica Centro"}]` |
| `extract_reviews(soup, limit=None)` | HTML de perfil y límite opcional. | Lista de opiniones embebidas. | Entrada: `limit=3` -> salida: hasta 3 opiniones con autor, fecha, rating y texto. |
| `extract_pacientes(soup)` | HTML de perfil. | Flags de tipos de pacientes y texto original. | Salida: `{"atiende_ninos": true, "atiende_adultos": true, "atiende_adolescentes": false, "texto_original": [...]}` |
| `get_latest_review_date(reviews)` | Lista de opiniones. | Fecha máxima o `None`. | Entrada: `[{"fecha": "2026-05-01"}, {"fecha": "2026-05-10"}]` -> salida: `"2026-05-10"` |
| `parse_doctoralia_html(html, url=None)` | HTML de perfil y URL opcional. | Perfil normalizado. | Salida: `{"nombre": "Dra. Ana", "servicios": [...], "consultorios": [...], "scraping_meta": {...}}` |
| `parse_doctoralia_file(file_path, url=None)` | Path de HTML local y URL opcional. | Perfil normalizado con `archivo_fuente`. | Entrada: `fixtures/views/alejandro_perez.html` -> salida: `{"archivo_fuente": "...", "nombre": "..."}` |
| `fetch_and_parse_profile(url)` | URL real de perfil. | Perfil normalizado sin `archivo_fuente`. | Entrada: `"https://www.doctoralia.com.mx/..."` -> salida: `{"nombre": "...", "scraping_meta": {"url_origen": "..."}}` |

## `app/scraper/utils/base.py`

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `espera_humana(min_seg=2.0, max_seg=6.0)` | Rango de segundos. | `None` después de dormir. | Entrada: `1`, `2` -> pausa aleatoria entre 1 y 2 segundos. |
| `scroll_humano(page)` | Página Playwright. | `None`; hace scroll gradual. | Entrada: `page` -> ejecuta varios `window.scrollTo(...)`. |
| `get_user_agent()` | No recibe parámetros. | User-Agent aleatorio. | Salida: `"Mozilla/5.0 (...)"` |
| `configurar_pagina_sigilosa(browser)` | Browser Playwright. | Página configurada. | Entrada: `browser` -> salida: `page` con locale `es-MX` y scripts anti-detección. |
| `fetch_con_reintento(page, url, max_intentos=3)` | Página, URL y número de intentos. | `bool`. | Entrada: `page`, `"https://..."`, `3` -> salida: `True` si cargó sin bloqueo/CAPTCHA. |

## `app/scraper/utils/rate_limiter.py`

| Función / método | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `RateLimiter.__init__(max_requests=10, ventana_segundos=60)` | Límite y ventana. | Instancia con historial vacío. | Entrada: `RateLimiter(5, 60)` -> objeto que permite 5 requests por minuto. |
| `RateLimiter.esperar_si_necesario()` | No recibe parámetros. | `None`; puede hacer `sleep`. | Si ya hubo 10 requests en 60s, espera hasta liberar la ventana. |

## `app/scraper/utils/scheduler.py`

| Función / método | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `Scheduler.__init__(intervalo_horas=24)` | Intervalo en horas. | Instancia detenida. | Entrada: `Scheduler(12)` -> ejecutor cada 12 horas. |
| `Scheduler.iniciar(tarea)` | Función async. | Bucle async hasta llamar `detener()`. | Entrada: `scheduler.iniciar(scraper.ejecutar)` -> ejecuta la tarea periódicamente. |
| `Scheduler.detener()` | No recibe parámetros. | `None`; cambia `corriendo` a `False`. | Entrada: `scheduler.detener()` -> el bucle termina tras el ciclo actual. |

## `backend/test/test_doctoralia_local.py`

Este archivo se comporta más como script generador de fixture que como test automatizado.

| Función | Qué recibe | Qué devuelve | Ejemplo |
| --- | --- | --- | --- |
| `slugify_name(value)` | Nombre de médico. | Slug seguro para nombre de archivo. | Entrada: `"Dr. Alejandro Pérez"` -> salida: `"dr_alejandro_perez"` |

Al importarse o ejecutarse, el módulo recorre `HTML_FILES`, parsea HTML local con `parse_doctoralia_file()` y escribe un JSON con timestamp en `backend/fixtures`.

