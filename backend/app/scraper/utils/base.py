import asyncio
import random


async def espera_humana(min_seg: float = 2.0, max_seg: float = 6.0):
    """Pausa la ejecucion durante un tiempo aleatorio.

    En scraping con navegador es comun insertar pausas entre acciones para no
    hacer todas las operaciones con tiempos exactos. Esta funcion elige un
    numero aleatorio entre ``min_seg`` y ``max_seg`` y espera esa cantidad de
    segundos sin bloquear el event loop de ``asyncio``.

    Args:
        min_seg: Tiempo minimo de espera en segundos.
        max_seg: Tiempo maximo de espera en segundos.

    Returns:
        None. La funcion solo espera y luego continua.
    """
    await asyncio.sleep(random.uniform(min_seg, max_seg))


async def scroll_humano(page):
    """Hace scroll gradual en una pagina abierta con Playwright.

    La funcion calcula la altura total del documento y baja poco a poco usando
    incrementos aleatorios. Esto ayuda a cargar contenido dinamico que aparece
    al hacer scroll y evita un salto instantaneo hasta el final de la pagina.

    Args:
        page: Objeto ``Page`` de Playwright ya abierto.

    Returns:
        None. Modifica visualmente la posicion de scroll de la pagina.
    """
    altura = await page.evaluate("document.body.scrollHeight")
    posicion = 0
    while posicion < altura:
        incremento = random.randint(200, 500)
        posicion = min(posicion + incremento, altura)
        await page.evaluate(f"window.scrollTo(0, {posicion})")
        await asyncio.sleep(random.uniform(0.3, 0.8))


USER_AGENTS = [
    # Chrome en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome en Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Safari en Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    # Edge en Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


def get_user_agent() -> str:
    """Selecciona aleatoriamente un User-Agent conocido.

    Un ``User-Agent`` es el texto que identifica el navegador y sistema
    operativo ante un servidor web. Al elegir uno de la lista se evita enviar
    siempre exactamente la misma identificacion.

    Returns:
        Cadena de texto con un User-Agent de navegador de escritorio.
    """
    return random.choice(USER_AGENTS)


async def configurar_pagina_sigilosa(browser):
    """Crea una pagina de Playwright con configuracion menos detectable.

    Esta funcion abre un nuevo contexto de navegador con idioma, zona horaria,
    viewport y cabeceras similares a las de un usuario real en Mexico. Tambien
    inyecta JavaScript para ocultar algunas señales comunes de automatizacion,
    como ``navigator.webdriver``.

    Args:
        browser: Instancia de navegador de Playwright, por ejemplo la devuelta
            por ``async_playwright().chromium.launch()``.

    Returns:
        Una nueva pagina de Playwright lista para navegar.
    """
    context = await browser.new_context(
        user_agent=get_user_agent(),
        viewport={
            "width": random.choice([1366, 1440, 1920]),
            "height": random.choice([768, 900, 1080]),
        },
        locale="es-MX",
        timezone_id="America/Mexico_City",
        # Headers que envía un navegador real
        extra_http_headers={
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "DNT": "1",
        },
    )
    page = await context.new_page()

    # Sobrescribir propiedades que delatan a Playwright
    await page.add_init_script(
        """
        // Eliminar webdriver flag
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // Simular plugins de navegador real
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });

        // Simular idiomas
        Object.defineProperty(navigator, 'languages', {
            get: () => ['es-MX', 'es', 'en-US', 'en']
        });

        // Ocultar que es headless
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );
    """
    )

    return page


async def fetch_con_reintento(page, url: str, max_intentos: int = 3) -> bool:
    """Navega a una URL con reintentos y esperas progresivas.

    Intenta abrir una pagina con Playwright. Si detecta codigos HTTP asociados
    a bloqueos temporales, como 403, 429 o 503, espera antes de intentar otra
    vez. Tambien revisa el HTML para detectar palabras relacionadas con CAPTCHA
    o robots.

    Args:
        page: Pagina de Playwright donde se realizara la navegacion.
        url: Direccion web que se quiere abrir.
        max_intentos: Numero maximo de intentos antes de rendirse.

    Returns:
        ``True`` si la pagina se pudo cargar sin senales claras de bloqueo.
        ``False`` si todos los intentos fallaron o fueron bloqueados.

    Side Effects:
        Imprime mensajes de error o bloqueo en consola y puede esperar varios
        segundos entre intentos.
    """
    for intento in range(max_intentos):
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=30000)

            # Detectar si nos bloquearon
            if response.status in [403, 429, 503]:
                espera = (2**intento) * random.uniform(5, 10)  # backoff exponencial
                print(f"Bloqueado (HTTP {response.status}), esperando {espera:.1f}s...")
                await asyncio.sleep(espera)
                continue

            # Detectar CAPTCHA en la página
            contenido = await page.content()
            if "captcha" in contenido.lower() or "robot" in contenido.lower():
                print("CAPTCHA detectado, pausando 30s...")
                await asyncio.sleep(30)
                continue

            return True

        except Exception as e:
            print(f"Error en intento {intento + 1}: {e}")
            await asyncio.sleep(random.uniform(3, 7))

    return False  # Falló después de todos los intentos
