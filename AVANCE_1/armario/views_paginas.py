"""Vistas de las paginas de Coincidencias y Recomendaciones de StyleMatch AI."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import FotoArmario
from .reglas_outfits import categorias_faltantes, generar_outfits


@login_required
def coincidencias(request):
    """Interfaz de consulta externa, sin simular inferencias de IA."""
    total_prendas = FotoArmario.objects.filter(
        propietario=request.user
    ).count()
    return render(
        request,
        "armario/coincidencias.html",
        {"total_prendas": total_prendas},
    )


@login_required
def recomendaciones(request):
    """Crea outfits con reglas de categorias y prendas del usuario actual."""
    prendas = list(
        FotoArmario.objects.filter(propietario=request.user).order_by("-fecha_subida", "-pk")
    )
    categoria_filtro = ""  # El filtro visual lo aplica recomendaciones.js
    seleccionada = prendas[0] if prendas else None
    busqueda_realizada = "prenda" in request.GET
    seleccion_invalida = False

    if busqueda_realizada:
        try:
            id_solicitado = int(request.GET.get("prenda", ""))
        except (ValueError, TypeError):
            id_solicitado = None

        # Nunca buscar por pk sin filtrar propietario: evita ver prendas ajenas.
        seleccionada = next((p for p in prendas if p.pk == id_solicitado), None)
        seleccion_invalida = seleccionada is None

    outfits = []
    faltantes = []
    if busqueda_realizada and seleccionada is not None:
        outfits = generar_outfits(prendas, seleccionada, max_resultados=3)
        if not outfits:
            faltantes = categorias_faltantes(prendas, seleccionada)

    return render(
        request,
        "armario/recomendaciones.html",
        {
            "prendas": prendas,
            "seleccionada": seleccionada,
            "busqueda_realizada": busqueda_realizada,
            "seleccion_invalida": seleccion_invalida,
            "outfits": outfits,
            "faltantes": faltantes,
            "categorias": FotoArmario.CATEGORIAS,
            "categoria_filtro": categoria_filtro,
        },
    )
