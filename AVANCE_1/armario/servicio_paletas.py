"""Consulta opcional a The Color API (solo HEX), con alternativa local.

Desactivada por defecto: STYLEMATCH_COLOR_API=1 habilita la consulta web.
Nunca envia fotografias, usuarios, nombres de prendas ni vectores.
"""

from functools import lru_cache
import json
import os
import re
from urllib.parse import urlencode
from urllib.request import urlopen


@lru_cache(maxsize=64)
def paleta_api(hexadecimal):
    if os.getenv("STYLEMATCH_COLOR_API", "0") != "1":
        return []
    if not isinstance(hexadecimal, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", hexadecimal):
        return []
    params = urlencode({"hex": hexadecimal[1:], "mode": "analogic", "count": 5})
    try:
        with urlopen(f"https://www.thecolorapi.com/scheme?{params}", timeout=2) as respuesta:
            if respuesta.status != 200:
                return []
            data = json.load(respuesta)
        resultado = []
        for color in data.get("colors", [])[:5]:
            valor = color.get("hex", {}).get("value")
            if isinstance(valor, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", valor):
                resultado.append(valor.upper())
        return resultado
    except (OSError, ValueError, KeyError, TypeError):
        return []
