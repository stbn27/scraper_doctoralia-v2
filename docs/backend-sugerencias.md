# Backend: sugerencias, riesgos y código mejorable

Fecha de revisión: 2026-05-25. Alcance: archivos `.py` dentro de `backend/`.

## Hallazgos principales

1. `backend/test/test_doctoralia_local.py` no es un test real de `pytest`.
   - El archivo ejecuta scraping local y escribe JSON al importarse, porque el `for html_name in HTML_FILES:` está en el nivel superior del módulo.
   - Riesgo: al correr `pytest`, se generan archivos en `backend/fixtures` y no hay asserts.
   - Mejora: mover la ejecución a `main()` y proteger con `if __name__ == "__main__":`; crear tests con fixtures y `assert` para `parse_doctoralia_file()`.

2. Hay endpoints síncronos que abren cursores/conexiones sin `try/finally` completo.
   - En `api/usuarios.py`, `register`, `login`, `get_me`, `listar_favoritos`, `guardar_historial` y `listar_historial` cierran manualmente después de la operación.
   - Riesgo: si `cursor.execute()` falla, la conexión puede quedar sin cerrar.
   - Mejora: usar context managers o bloques `try/finally` consistentes.

3. `eliminar_favorito()` declara `status_code=204`, pero su docstring dice que retorna un mensaje.
   - El código no retorna cuerpo, lo cual es correcto para 204.
   - Mejora: corregir documentación del endpoint o cambiar a `200` si se desea mensaje.

4. `agregar_favorito()` captura `Exception` genérico y lo traduce siempre a duplicado.
   - Riesgo: errores de conexión, tabla inexistente o datos inválidos se reportan como `409 Ya está en favoritos`.
   - Mejora: capturar la excepción específica de duplicado de MySQL y dejar que otros errores sean `500` o una respuesta controlada.

5. `guardar_historial()` recibe `especialidad` y `ubicacion` como query params, no como body.
   - Puede ser válido, pero para un `POST` suele ser más claro usar un modelo Pydantic.
   - Mejora: crear `HistorialCreate` con `especialidad` y `ubicacion`.

6. `SECRET_KEY` tiene un valor por defecto fijo en código.
   - Riesgo: si se despliega sin variable de entorno, todos los tokens quedan firmados con una clave pública del repositorio.
   - Mejora: requerir `SECRET_KEY` en producción y fallar al arrancar si no existe.

7. Los modelos Pydantic usan listas mutables como defaults.
   - `EspecialistaModel` define `cedulas: list[str] = []`, `experiencia: list[str] = []`, `servicios: list[...] = []`, `consultorios: list[...] = []`.
   - Pydantic suele manejar copias, pero el patrón recomendado es `Field(default_factory=list)`.
   - Mejora: cambiar a `Field(default_factory=list)` para evitar ambigüedad y futuros bugs.

8. `extract_pairs()` perdió anotaciones completas.
   - Hay una firma comentada `#def extract_pairs(soup: BeautifulSoup) -> tuple[list[dict], list[dict]]:` y la firma activa usa `def extract_pairs(soup, known_slugs: set[str] | None = None):`.
   - Mejora: usar `def extract_pairs(soup: BeautifulSoup, known_slugs: set[str] | None = None) -> tuple[list[dict], list[dict]]:`.

9. Funciones duplicadas de limpieza/conversión.
   - `clean_text` existe en `catalog_extractor.py`, `listing_scraper.py` y `doctoralia.py`; `parse_int/convertir_entero/extract_number` y `parse_float/convertir_decimal` también se solapan.
   - Mejora: extraer utilidades puras a `app/scraper/utils/text.py` o similar, y cubrirlas con tests.

10. Código potencialmente no usado.
    - `doctoralia.first_text_by_selectors()`, `doctoralia.extract_reviews()`, `doctoralia.get_latest_review_date()`, `reviews_scraper.extract_opinion_id()` y `reviews_scraper.extract_rating()` no parecen ser llamadas por otros módulos actuales.
    - `catalogos_repo.listar_catalogos()`, `catalogos_repo.actualizar_catalogo()` y `opiniones_repo.eliminar_opiniones_por_doctor()` no tienen endpoints o servicios que las llamen.
    - `utils/base.py` contiene utilidades Playwright que no se usan desde los scrapers actuales, que usan `httpx`.
    - Mejora: decidir si se exponen, se testean como API interna o se eliminan.

11. Dependencias posiblemente no usadas en backend actual.
    - `pandas` y `ollama` aparecen en `requirements.txt`, pero no se observan imports en los `.py` revisados.
    - `playwright` solo corresponde a utilidades en `utils/base.py`; si esas utilidades no se usan, la dependencia puede ser innecesaria.
    - Mejora: limpiar dependencias o documentar qué script externo las necesita.

12. Los scrapers escriben archivos en rutas de fixtures desde funciones de alto nivel.
    - `catalog_refresher.refresh_catalog()`, `listing_scraper.main()`, `reviews_scraper.main()` y el script en `test` escriben JSON/HTML.
    - Mejora: separar parsing puro, descarga y persistencia; en tests, escribir en `tmp_path`.

13. `RateLimiter.esperar_si_necesario()` usa `.seconds`.
    - `.seconds` ignora días y puede ser menos claro que `total_seconds()`.
    - Mejora: usar `(ahora - self.historial[0]).total_seconds()`.

14. Falta manejo de errores más granular en scraping.
    - `httpx.get(...).raise_for_status()` propaga excepciones crudas hacia servicios/endpoints.
    - Mejora: traducir errores de red, `403/429` y timeouts a errores controlados con mensajes y códigos HTTP adecuados.

15. `buscar_o_scrapear_especialistas()` calcula páginas objetivo con un supuesto fijo de 17 doctores por página.
    - Riesgo: si Doctoralia cambia el tamaño de página, el límite puede extraer menos resultados de los esperados.
    - Mejora: derivar el tamaño desde el primer resultado o seguir páginas hasta cumplir `limite` o llegar a `total_paginas`.

16. `actualizar_especialista()` devuelve `False` cuando el documento existe pero los datos son iguales.
    - `modified_count` es `0` si no hubo cambios, aunque el match exista.
    - Mejora: si importa saber si encontró el documento, usar `matched_count > 0`.

17. En `catalogos_repo.upsert_catalogos()`, se construyen claves aunque falten slugs.
    - Riesgo: documentos con `None` en la clave compuesta pueden chocar en el índice único.
    - Mejora: filtrar o validar documentos sin `especialidad_slug` o `ciudad_slug`.

18. `OpinionesResponse` no serializa `_id`.
    - Las opiniones devueltas desde Mongo pueden incluir `_id`, pero `OpinionModel` no tiene alias ni campo para `_id`.
    - FastAPI puede filtrar campos extra, pero conviene confirmar el comportamiento deseado.
    - Mejora: serializar `_id` como string o excluirlo explícitamente antes de responder.

19. `configurar_pagina_sigilosa()` devuelve solo `page`, no el `context`.
    - Riesgo: quien use esta función no tiene referencia directa para cerrar el contexto.
    - Mejora: devolver `(context, page)` o documentar una función de cierre.

20. Docstrings existentes con formato inconsistente.
    - En `models/usuario.py` varios docstrings empiezan como `""" "`.
    - Mejora: normalizar docstrings para que herramientas de documentación los muestren correctamente.

## Mejoras recomendadas por prioridad

1. Convertir `backend/test/test_doctoralia_local.py` en tests reales y mover escrituras a `tmp_path`.
2. Agregar tests unitarios para parsers puros: `clean_text`, slugs, extracción de servicios, listados, opiniones y catálogo.
3. Reforzar cierre de conexiones MySQL con `try/finally` o context managers.
4. Requerir `SECRET_KEY` por entorno fuera de desarrollo.
5. Centralizar utilidades de parsing para reducir duplicación.
6. Revisar dependencias no usadas y eliminar las que no se necesiten.
7. Agregar validaciones a repositorios antes de upserts masivos.
8. Definir política de errores de scraping para timeouts, bloqueos y cambios de HTML.

## Posibles archivos a crear después

- `backend/test/test_catalog_extractor.py`
- `backend/test/test_listing_scraper.py`
- `backend/test/test_reviews_scraper.py`
- `backend/test/test_doctoralia_parser.py`
- `backend/app/scraper/utils/text.py`
- `backend/app/models/historial.py`

