from pathlib import Path

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import EditarPrendaForm, FotoArmarioForm
from .models import FotoArmario


def mi_armario(request):
    formulario = FotoArmarioForm()

    if request.method == "POST":
        formulario = FotoArmarioForm(request.POST, request.FILES)
        if formulario.is_valid():
            # A diferencia de 1.3.1, NO eliminamos fotografias anteriores.
            prenda = formulario.save(commit=False)
            nombre_archivo = Path(request.FILES["imagen"].name).stem
            prenda.nombre = (
                nombre_archivo.replace("_", " ").replace("-", " ").strip()[:120]
                or "Prenda"
            )
            prenda.save()
            messages.success(request, "Prenda guardada correctamente.")
            return redirect("mi_armario")

    busqueda = (request.GET.get("q") or "").strip()[:80]
    categoria_actual = (request.GET.get("categoria") or "").strip()
    categorias_validas = {codigo for codigo, _ in FotoArmario.CATEGORIAS}
    if categoria_actual not in categorias_validas | {"", "sin_categoria"}:
        categoria_actual = ""

    prendas = FotoArmario.objects.order_by("-fecha_subida", "-pk")
    total_prendas = prendas.count()

    if busqueda:
        prendas = prendas.filter(
            Q(nombre__icontains=busqueda)
            | Q(imagen__icontains=busqueda)
        )

    if categoria_actual == "sin_categoria":
        prendas = prendas.filter(Q(categoria="") | Q(categoria__isnull=True))
    elif categoria_actual:
        prendas = prendas.filter(categoria=categoria_actual)

    paginador = Paginator(prendas, 8)
    pagina = paginador.get_page(request.GET.get("page"))
    rango_paginas = paginador.get_elided_page_range(
        number=pagina.number, on_each_side=1, on_ends=1
    )

    return render(
        request,
        "armario/mi_armario.html",
        {
            "formulario": formulario,
            "prendas": pagina,
            "total_prendas": total_prendas,
            "total_filtradas": paginador.count,
            "categorias": FotoArmario.CATEGORIAS,
            "categoria_actual": categoria_actual,
            "busqueda": busqueda,
            "rango_paginas": rango_paginas,
        },
    )


@require_POST
def editar_prenda(request, pk):
    prenda = get_object_or_404(FotoArmario, pk=pk)
    formulario = EditarPrendaForm(request.POST, instance=prenda)
    if formulario.is_valid():
        formulario.save()
        messages.success(request, "Prenda actualizada correctamente.")
    else:
        messages.error(request, "No se pudo actualizar la prenda.")
    return redirect("mi_armario")


@require_POST
def eliminar_foto(request, pk=None):
    # Mantiene la ruta antigua /eliminar/ por compatibilidad.
    # La galeria siempre envia un ID explicito para eliminar solo esa prenda.
    if pk is None:
        prenda = FotoArmario.objects.order_by("-pk").first()
    else:
        prenda = get_object_or_404(FotoArmario, pk=pk)

    if prenda:
        prenda.imagen.delete(save=False)
        prenda.delete()
        messages.success(request, "Prenda eliminada correctamente.")
    else:
        messages.info(request, "No hay prendas para eliminar.")

    return redirect("mi_armario")
