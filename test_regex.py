import re
from backend.app.services.busqueda_service import _regex_ci

patron = _regex_ci("dentista")["$regex"]
print("Patron:", patron)
match = re.search(patron, "Dentista - Odontólogo", re.IGNORECASE)
print("Match dentista:", bool(match))

patron = _regex_ci("dentista-odontologo")["$regex"]
print("Patron odont:", patron)
match = re.search(patron, "Dentista - Odontólogo", re.IGNORECASE)
print("Match dentista-odontologo:", bool(match))
