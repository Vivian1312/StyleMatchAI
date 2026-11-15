"""Analisis cromatico local y orientativo de fotografias de prendas.

Sin llamadas de red y sin persistir datos. Se usa CIELAB (aproximacion D65)
para distinguir blancos frios, cremas y beiges con baja saturacion.
El aislamiento de la prenda es aproximado, no una segmentacion semantica.
"""

from collections import Counter, defaultdict
import colorsys
from io import BytesIO
from math import atan2, degrees, sqrt
from statistics import median

from PIL import Image, ImageOps, UnidentifiedImageError


_NOMBRES = {
    "negro": "Negro", "blanco": "Blanco", "crema": "Crema",
    "gris": "Gris", "beige": "Beige", "marron": "Marron",
    "rojo": "Rojo", "naranja": "Naranja", "amarillo": "Amarillo",
    "verde": "Verde", "turquesa": "Turquesa", "azul": "Azul",
    "morado": "Morado", "rosa": "Rosa",
}
_NEUTROS = {"negro", "blanco", "crema", "gris", "beige", "marron"}


def _lineal(canal):
    canal = canal / 255.0
    return canal / 12.92 if canal <= 0.04045 else ((canal + 0.055) / 1.055) ** 2.4


def _lab_de_rgb(rgb):
    """Transformacion sRGB -> CIELAB D65, sin dependencias externas."""
    r, g, b = (_lineal(valor) for valor in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t):
        return t ** (1.0 / 3.0) if t > 0.008856451679 else (t / (3 * (6 / 29) ** 2) + 4 / 29)

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _delta_e(lab_a, lab_b):
    """Distancia Delta E 1976 para descarte de fondo (aproximada)."""
    return sqrt(sum((a - b) ** 2 for a, b in zip(lab_a, lab_b)))


def _familia(rgb):
    l, a, b = _lab_de_rgb(rgb)
    c = sqrt(a * a + b * b)
    h_lab = (degrees(atan2(b, a)) + 360) % 360
    h, s, _ = colorsys.rgb_to_hsv(*(valor / 255 for valor in rgb))
    h *= 360

    if l < 15 or (l < 24 and c < 18):
        return "negro"

    # Warm, pale, low-chroma shades are not necessarily white.
    # A neutral-grey cast stays grey unless its yellow component is noticeable.
    calido = 48 <= h_lab <= 113 and b >= 6 and a >= -5
    if calido and l >= 89 and c <= 26 and b >= 5.3:
        return "crema"
    if calido and 63 <= l < 89 and c <= 37 and b >= 5.3:
        return "beige"
    if calido and 29 <= l < 63 and b >= 8:
        return "marron"

    if c < 8 or s < 0.10:
        if l >= 91:
            return "blanco"
        if l < 31:
            return "negro"
        return "gris"

    # Warm high-chroma whites / yellows still need a chromatic label.
    if 24 <= h <= 58 and l > 60 and s < .43:
        return "beige"
    if 10 <= h <= 55 and l < 60 and s < .75:
        return "marron"
    if h < 14 or h >= 346:
        return "rojo"
    if h < 45:
        return "naranja"
    if h < 70:
        return "amarillo"
    if h < 165:
        return "verde"
    if h < 195:
        return "turquesa"
    if h < 261:
        return "azul"
    if h < 307:
        return "morado"
    return "rosa"


def _analizar_pil(imagen):
    imagen = ImageOps.exif_transpose(imagen)
    imagen.thumbnail((180, 180))
    tiene_alfa = "A" in imagen.getbands() or "transparency" in imagen.info
    rgba = imagen.convert("RGBA")
    canal_alfa = rgba.getchannel("A")
    if tiene_alfa:
        alfa_valores = list(canal_alfa.get_flattened_data() if hasattr(canal_alfa, "get_flattened_data") else canal_alfa.getdata())
    else:
        alfa_valores = None
    fondo_blanco = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    fondo_blanco.alpha_composite(rgba)
    imagen = fondo_blanco.convert("RGB")

    ancho, alto = imagen.size
    if ancho < 6 or alto < 6:
        return None
    pixeles = list(imagen.get_flattened_data() if hasattr(imagen, "get_flattened_data") else imagen.getdata())
    borde = max(2, min(ancho, alto) // 14)
    esquinas = []
    for y in list(range(borde)) + list(range(alto - borde, alto)):
        for x in list(range(borde)) + list(range(ancho - borde, ancho)):
            esquinas.append(pixeles[y * ancho + x])
    fondo_rgb = tuple(int(median(p[i] for p in esquinas)) for i in range(3))
    fondo_lab = _lab_de_rgb(fondo_rgb)
    dispersion = sum(_delta_e(_lab_de_rgb(p), fondo_lab) for p in esquinas) / len(esquinas)
    fondo_uniforme = dispersion < 11

    def candidatos_primarios():
        candidatos = []
        for y in range(0, alto, 2):
            for x in range(0, ancho, 2):
                pos = y * ancho + x
                if alfa_valores is not None and alfa_valores[pos] < 100:
                    continue
                rgb = pixeles[pos]
                if fondo_uniforme and alfa_valores is None:
                    lab = _lab_de_rgb(rgb)
                    diferencia = _delta_e(lab, fondo_lab)
                    # El umbral general elimina correctamente fondos lisos,
                    # pero tambien puede eliminar prendas beige/crema claras
                    # sobre fondos casi blancos o grises. Conservar ese matiz
                    # calido si esta en la zona central y se separa del fondo.
                    zona_prenda = (
                        ancho * .10 <= x <= ancho * .90
                        and alto * .08 <= y <= alto * .92
                    )
                    fondo_claro_poco_saturado = (
                        fondo_lab[0] > 72 and abs(fondo_lab[1]) < 8
                        and abs(fondo_lab[2]) < 14
                    )
                    matiz_calido_diferente = (
                        lab[2] >= 5.0
                        and lab[2] - fondo_lab[2] >= 3.0
                        and lab[0] <= fondo_lab[0] + 1.5
                    )
                    conservar_beige_claro = (
                        zona_prenda and fondo_claro_poco_saturado
                        and matiz_calido_diferente and diferencia >= 4.0
                    )
                    if diferencia < 11 and not conservar_beige_claro:
                        continue
                elif not fondo_uniforme and not (ancho * .12 <= x <= ancho * .88 and alto * .10 <= y <= alto * .90):
                    continue
                candidatos.append(rgb)
        return candidatos

    candidatos = candidatos_primarios()
    metodo = "fondo_aproximado"
    if len(candidatos) < max(18, (ancho * alto) // 220):
        # White-on-white or transparent imagery can be indistinguishable
        # from the background. This fallback is explicitly low confidence.
        candidatos = [
            pixeles[y * ancho + x]
            for y in range(int(alto * .22), int(alto * .80), 2)
            for x in range(int(ancho * .22), int(ancho * .80), 2)
            if alfa_valores is None or alfa_valores[y * ancho + x] >= 100
        ]
        metodo = "zona_central_aproximada"
    if not candidatos:
        return None

    conteo = Counter()
    canales = defaultdict(lambda: [0, 0, 0])
    for rgb in candidatos:
        familia = _familia(rgb)
        conteo[familia] += 1
        for i in range(3):
            canales[familia][i] += rgb[i]

    total = len(candidatos)
    colores = []
    for familia, cantidad in conteo.most_common(3):
        if colores and cantidad / total < 0.16:
            continue
        promedio = tuple(round(suma / cantidad) for suma in canales[familia])
        colores.append({
            "familia": familia,
            "nombre": _NOMBRES[familia],
            "hex": "#{:02X}{:02X}{:02X}".format(*promedio),
            "proporcion": round(cantidad / total, 3),
            "neutro": familia in _NEUTROS,
        })
        if len(colores) == 2:
            break
    return {"colores": colores, "metodo": metodo} if colores else None


def analizar_colores_imagen(fuente):
    """Lee bytes o archivo subido; no escribe archivos ni transmite fotos."""
    try:
        if isinstance(fuente, (bytes, bytearray)):
            fuente = BytesIO(fuente)
        if hasattr(fuente, "seek"):
            fuente.seek(0)
        with Image.open(fuente) as imagen:
            imagen.verify()
        if hasattr(fuente, "seek"):
            fuente.seek(0)
        with Image.open(fuente) as imagen:
            return _analizar_pil(imagen)
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
        return None
    finally:
        if hasattr(fuente, "seek"):
            try:
                fuente.seek(0)
            except (OSError, ValueError):
                pass


def analizar_colores_prenda(prenda):
    """Analiza una imagen en storage Django sin modificar el modelo."""
    imagen = getattr(prenda, "imagen", None)
    if imagen is None or not getattr(imagen, "name", None):
        return None
    try:
        with imagen.storage.open(imagen.name, "rb") as archivo:
            return analizar_colores_imagen(archivo)
    except (OSError, ValueError):
        return None
