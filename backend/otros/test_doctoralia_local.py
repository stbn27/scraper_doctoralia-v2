import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from app.scraper.doctoralia import parse_doctoralia_file

BASE_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = BASE_DIR.parent / "fixtures/views"
VIEWS_DIR = FIXTURES_DIR / "output"

# Se agrega para generar nombres de salida estables y seguros desde el nombre del médico.
def slugify_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "medico"

HTML_FILES = [
    "alejandro_perez.html",
    "dr_jorge.html",
    "dr_luis.html",
    "dr_samuel.html",
    "dra_ana.html",
    "dra_maria.html",
    "dra_ximena.html",
    "dra_samantha.html",
]

timestamp = datetime.now().strftime("%d%m%Y%H%M")

for html_name in HTML_FILES:
    html_file = VIEWS_DIR / html_name
    if not html_file.exists():
        print(f"[WARN] No existe: {html_file}")
        continue

    data = parse_doctoralia_file(html_file)
    doctor_slug = slugify_name(data.get("nombre") or html_file.stem)
    output_file = FIXTURES_DIR / f"dr_v1_{doctor_slug}_{timestamp}.json"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Extracción terminada")
    print(f"Doctor: {data.get('nombre')}")
    print(f"Especialidad: {data.get('especialidad')}")
    #print(f"Opiniones extraídas: {len(data.get('opiniones', []))}")
    print(f"Archivo generado: {output_file.resolve()}")
    print("-" * 80)
