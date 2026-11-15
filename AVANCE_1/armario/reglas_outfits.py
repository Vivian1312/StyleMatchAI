"""Recomendador hibrido local: reglas de categorias + armonia cromatica.

Conserva las siete reglas preexistentes. El color es una heuristica orientativa;
no se presenta como una probabilidad ni como una medida de gusto personal.
Las prendas recibidas deben estar filtradas por propietario en la vista Django.
"""

from collections import defaultdict
from itertools import islice, product
from types import SimpleNamespace

from .analisis_colores import analizar_colores_prenda
from .compatibilidad_outfits import evaluar_conjunto
from .servicio_paletas import paleta_api


PATRONES = (
    ("Look casual", "Una combinacion sencilla para el dia a dia.", ("tops", "pantalones", "calzado")),
    ("Look con falda", "Una alternativa con falda para variar tu armario.", ("tops", "faldas", "calzado")),
    ("Look con vestido", "Un vestido combinado con tu calzado.", ("vestidos", "calzado")),
    ("Look en capas", "Un conjunto con chaqueta para complementar.", ("tops", "pantalones", "calzado", "chaquetas")),
    ("Look con falda y chaqueta", "Una opcion con una capa adicional.", ("tops", "faldas", "calzado", "chaquetas")),
    ("Look con accesorio", "Un conjunto completado con un accesorio.", ("tops", "pantalones", "calzado", "accesorios")),
    ("Look con vestido y accesorio", "Vestido, calzado y un accesorio.", ("vestidos", "calzado", "accesorios")),
)

CATEGORIAS_NOMBRES = {
    "tops": "Tops", "pantalones": "Pantalones", "faldas": "Faldas",
    "vestidos": "Vestidos", "calzado": "Calzado", "chaquetas": "Chaquetas",
    "accesorios": "Accesorios",
}


def generar_outfits(prendas, base, max_resultados=3, color_externo=None):
    """Hasta tres looks distintos que incluyen la prenda base.

    El ranking considera el color de las prendas disponibles y penaliza la
    repeticion de piezas, en especial accesorios y calzado. No modifica BD.
    """
    if base is None or base.categoria not in CATEGORIAS_NOMBRES:
        return []
    max_resultados = max(0, min(int(max_resultados), 6))
    if not max_resultados:
        return []

    por_categoria = defaultdict(list)
    for prenda in prendas:
        if prenda.categoria in CATEGORIAS_NOMBRES:
            por_categoria[prenda.categoria].append(prenda)
    for categoria in list(por_categoria):
        por_categoria[categoria] = por_categoria[categoria][:12]

    # La prenda externa no esta en la BD: nunca se intenta abrir su archivo.
    paletas = {}
    for grupo in por_categoria.values():
        for prenda in grupo:
            if prenda.pk != -1 and prenda.pk not in paletas:
                paletas[prenda.pk] = analizar_colores_prenda(prenda)
    if base.pk != -1 and base.pk not in paletas:
        paletas[base.pk] = analizar_colores_prenda(base)

    paleta_base = color_externo if base.pk == -1 else paletas.get(base.pk)
    hexa_base = None
    if paleta_base and paleta_base.get("colores"):
        hexa_base = paleta_base["colores"][0]["hex"]
    colores_api = paleta_api(hexa_base) if hexa_base else []

    candidatos = []
    vistos = set()
    for titulo, descripcion, categorias in PATRONES:
        if base.categoria not in categorias:
            continue
        if any(not por_categoria.get(categoria) for categoria in categorias if categoria != base.categoria):
            continue
        grupos = [[base] if categoria == base.categoria else por_categoria[categoria]
                  for categoria in categorias]
        for conjunto in islice(product(*grupos), 1800):
            ids = tuple(prenda.pk for prenda in conjunto)
            if len(ids) != len(set(ids)):
                continue
            llave = frozenset(ids)
            if llave in vistos:
                continue
            vistos.add(llave)
            evaluacion = evaluar_conjunto(conjunto, paletas, paleta_externa=color_externo, colores_api=colores_api)
            candidatos.append({
                "titulo": titulo,
                "descripcion": descripcion,
                "prendas": conjunto,
                "etiquetas": [CATEGORIAS_NOMBRES[prenda.categoria] for prenda in conjunto],
                **evaluacion,
            })

    # Seleccion codiciosa: buen encaje cromatico + variedad de prendas y reglas.
    elegidos = []
    usados_por_prenda = defaultdict(int)
    usados_por_patron = defaultdict(int)
    while candidatos and len(elegidos) < max_resultados:
        def puntuacion_ajustada(outfit):
            otros = [p.pk for p in outfit["prendas"] if p.pk != base.pk]
            repeticion = sum(usados_por_prenda[pk] * 16 for pk in otros)
            repeticion_patron = 12 * usados_por_patron[outfit["titulo"]]
            # Sin colores legibles, la diversidad sigue funcionando.
            return outfit["puntuacion_color"] - repeticion - repeticion_patron

        mejor = max(candidatos, key=puntuacion_ajustada)
        candidatos.remove(mejor)
        elegidos.append(mejor)
        usados_por_patron[mejor["titulo"]] += 1
        for prenda in mejor["prendas"]:
            if prenda.pk != base.pk:
                usados_por_prenda[prenda.pk] += 1
    return elegidos


def categorias_faltantes(prendas, base):
    """Categorias faltantes de la regla mas cercana a completarse."""
    if base is None or base.categoria not in CATEGORIAS_NOMBRES:
        return []
    disponibles = {p.categoria for p in prendas}
    alternativas = []
    for _, _, categorias in PATRONES:
        if base.categoria in categorias:
            alternativas.append([c for c in categorias if c not in disponibles])
    if not alternativas:
        return []
    return [CATEGORIAS_NOMBRES[c] for c in min(alternativas, key=len)]


def generar_outfits_prenda_externa(prendas, categoria, max_resultados=3, color_externo=None):
    """Simula una prenda virtual sin guardarla en la base de datos."""
    if categoria not in CATEGORIAS_NOMBRES:
        return []
    externa = SimpleNamespace(pk=-1, categoria=categoria, nombre="Prenda externa que quieres comprar")
    return generar_outfits([*prendas, externa], externa,
                           max_resultados=max_resultados, color_externo=color_externo)
