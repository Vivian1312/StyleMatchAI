"""Ranking cromatico explicable: familias, brillo, saturacion y contraste.

Las puntuaciones son heuristicas internas para ordenar alternativas; no son
porcentajes ni predicciones de gusto personal. La base sigue siendo la regla
de categorias en reglas_outfits.py.
"""

import colorsys
from itertools import combinations
from math import atan2, degrees, sqrt

from .analisis_colores import _lab_de_rgb


_NEUTROS = {"negro", "blanco", "crema", "gris", "beige", "marron"}


def _datos(color):
    if not color:
        return None
    hexa = color.get("hex", "")
    try:
        if not isinstance(hexa, str) or len(hexa) != 7 or hexa[0] != "#":
            return None
        rgb = tuple(int(hexa[i:i + 2], 16) for i in (1, 3, 5))
    except ValueError:
        return None
    l, a, b = _lab_de_rgb(rgb)
    c = sqrt(a * a + b * b)
    hue_lab = (degrees(atan2(b, a)) + 360) % 360
    _, saturacion, _ = colorsys.rgb_to_hsv(*(canal / 255 for canal in rgb))
    familia = color.get("familia", "")
    es_neutro = familia in _NEUTROS or c < 9
    return {"familia": familia, "L": l, "C": c, "hue": hue_lab,
            "s": saturacion, "neutro": es_neutro}


def _distancia_angular(a, b):
    distancia = abs(a - b) % 360
    return min(distancia, 360 - distancia)


def _relacion(color_a, color_b):
    """Puntos orientativos para una pareja, y la relacion que los justifica."""
    a, b = _datos(color_a), _datos(color_b)
    if a is None or b is None:
        return 0.0, "sin_datos"
    luminosidad = abs(a["L"] - b["L"])
    contraste_suave = min(9, luminosidad * .20)

    if a["neutro"] and b["neutro"]:
        # Neutrals can work together, with subtle reward for tonal contrast.
        return round(77 + contraste_suave, 2), "neutros"
    if a["neutro"] or b["neutro"]:
        # Not every colorful+neutral pairing receives the same score.
        saturacion_color = b["s"] if a["neutro"] else a["s"]
        score = 76 + contraste_suave + min(3, saturacion_color * 4)
        return round(score, 2), "neutra"

    distancia = _distancia_angular(a["hue"], b["hue"])
    exceso_saturacion = 3 if a["s"] > .8 and b["s"] > .8 and luminosidad < 12 else 0
    if a["familia"] == b["familia"] or distancia <= 24:
        return round(80 + min(7, luminosidad * .12) - exceso_saturacion, 2), "monocromatica"
    if distancia <= 55:
        return round(83 - (distancia - 24) * .05 - exceso_saturacion, 2), "analoga"
    if abs(distancia - 180) <= 26:
        return round(83 - exceso_saturacion, 2), "complementaria"
    if abs(distancia - 120) <= 24:
        return round(77 - exceso_saturacion, 2), "separacion_120"
    return round(62 - exceso_saturacion, 2), "contraste_libre"


def evaluar_conjunto(prendas, paletas, paleta_externa=None, colores_api=None):
    """Retorna la misma estructura usada por ambas interfaces existentes."""
    principales = []
    colores = []
    incompletas = 0
    poca_confianza = 0
    for prenda in prendas:
        paleta = paleta_externa if prenda.pk == -1 else paletas.get(prenda.pk)
        valores = (paleta or {}).get("colores") or []
        principal = valores[0] if valores else None
        principales.append(principal)
        if principal is None:
            incompletas += 1
        elif (paleta or {}).get("metodo") == "zona_central_aproximada":
            poca_confianza += 1
        if principal and principal.get("familia") not in {c["familia"] for c in colores}:
            colores.append({"nombre": principal["nombre"], "hex": principal["hex"],
                            "familia": principal["familia"]})

    relaciones, puntos = [], []
    for primero, segundo in combinations(principales, 2):
        puntaje, relacion = _relacion(primero, segundo)
        if relacion != "sin_datos":
            relaciones.append(relacion)
            puntos.append(puntaje)
    if not puntos:
        return {"puntuacion_color": 0, "motivo_color": "Color no evaluado: ordenado por categoria y variedad.",
                "colores": colores[:4], "evaluacion_color": False}

    # A small penalty for partial evidence, never a fabricated color match.
    puntuacion = sum(puntos) / len(puntos) - 4 * incompletas - 2 * poca_confianza
    if colores_api and principales and principales[0]:
        # Optional, very small bonus based on public palette references.
        for color in principales[1:]:
            dato = _datos(color)
            if not dato or dato["neutro"]:
                continue
            for hexa in colores_api[:5]:
                fuente = {"hex": hexa, "familia": "referencia"}
                ref = _datos(fuente)
                if ref and _distancia_angular(dato["hue"], ref["hue"]) <= 18:
                    puntuacion += 2
                    break

    tipos = set(relaciones)
    if tipos.issubset({"neutros"}):
        motivo = "Combina tonos neutros, con contraste de luminosidad orientativo."
    elif "complementaria" in tipos:
        motivo = "Incluye dos tonos aproximadamente complementarios en la rueda cromatica."
    elif "analoga" in tipos:
        motivo = "Incluye tonos cercanos en la rueda cromatica."
    elif "monocromatica" in tipos:
        motivo = "Repite tonos de una familia cromatica, con variacion de luminosidad."
    elif "neutra" in tipos:
        motivo = "Combina un color principal con neutros y considera el contraste de luz."
    elif "separacion_120" in tipos:
        motivo = "Incluye colores separados aproximadamente 120 grados en el circulo cromatico."
    else:
        motivo = "Combina colores contrastantes; revisa si se ajustan a tu gusto."
    if incompletas:
        motivo += " Algunas prendas no pudieron analizarse."
    elif poca_confianza:
        motivo += " La estimacion de alguna prenda es aproximada."

    return {"puntuacion_color": round(max(0, min(100, puntuacion)), 2),
            "motivo_color": motivo, "colores": colores[:4], "evaluacion_color": True}
