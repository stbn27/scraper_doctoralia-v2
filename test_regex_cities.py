import re
from backend.app.services.busqueda_service import _regex_ci

patron = _regex_ci("ocotepec")["$regex"]
print("Patron ocotepec:", patron)
match = re.search(patron, "Ecatepec", re.IGNORECASE)
print("Match ecatepec:", bool(match))
