"""Combinaciones sencillas de armario, sin IA ni inferencia de estilos/colores.

Este modulo no accede a la base de datos y no altera las prendas: recibe las
prendas del usuario ya filtradas en la vista de Django.
"""

from collections import defaultdict
from itertools import product


# (Titulo, breve descripcion, categorias requeridas)
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
    "tops": "Tops",
    "pantalones": "Pantalones",
    "faldas": "Faldas",
    "vestidos": "Vestidos",
    "calzado": "Calzado",
    "chaquetas": "Chaquetas",
    "accesorios": "Accesorios",
}


def generar_outfits(prendas, base, max_resultados=3):
    """Retorna hasta max_resultados looks, todos incluyen la prenda base.

    No crea resultados falsos cuando faltan categorias. Alterna entre
    patrones para dar diversidad en lugar de llenar con variaciones del mismo.
    """
    if base is None or base.categoria not in CATEGORIAS_NOMBRES:
        return []

    por_categoria = defaultdict(list)
    for prenda in prendas:
        if prenda.categoria in CATEGORIAS_NOMBRES:
            por_categoria[prenda.categoria].append(prenda)

    # No se procesan combinaciones enormes: maximo 20 opciones por categoria.
    for categoria in list(por_categoria):
        por_categoria[categoria] = por_categoria[categoria][:20]

    iteradores = []
    for titulo, descripcion, categorias in PATRONES:
        if base.categoria not in categorias:
            continue
        if any(not por_categoria.get(categoria) for categoria in categorias):
            continue

        # Fijar la prenda base en la categoria que le corresponde.
        grupos = [
            [base] if categoria == base.categoria else por_categoria[categoria]
            for categoria in categorias
        ]
        iteradores.append((titulo, descripcion, iter(product(*grupos))))

    outfits = []
    usados = set()
    while iteradores and len(outfits) < max_resultados:
        pendientes = []
        for titulo, descripcion, combinaciones in iteradores:
            try:
                conjunto = next(combinaciones)
            except StopIteration:
                continue
            pendientes.append((titulo, descripcion, combinaciones))
            ids = tuple(prenda.pk for prenda in conjunto)
            if len(ids) != len(set(ids)):
                continue
            llave = frozenset(ids)
            if llave in usados:
                continue
            usados.add(llave)
            outfits.append({
                "titulo": titulo,
                "descripcion": descripcion,
                "prendas": conjunto,
                "etiquetas": [CATEGORIAS_NOMBRES[c] for c in (
                    prenda.categoria for prenda in conjunto
                )],
            })
            if len(outfits) >= max_resultados:
                break
        iteradores = pendientes

    return outfits


def categorias_faltantes(prendas, base):
    """Indica las categorias faltantes de la regla mas cercana a cumplirse."""
    if base is None or base.categoria not in CATEGORIAS_NOMBRES:
        return []

    disponibles = {p.categoria for p in prendas}
    alternativas = []
    for _, _, categorias in PATRONES:
        if base.categoria in categorias:
            faltantes = [c for c in categorias if c not in disponibles]
            alternativas.append(faltantes)

    if not alternativas:
        return []
    faltantes = min(alternativas, key=len)
    return [CATEGORIAS_NOMBRES[c] for c in faltantes]
