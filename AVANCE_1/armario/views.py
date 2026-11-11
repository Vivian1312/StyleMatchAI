
from pathlib import Path
from mimetypes import guess_type

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_safe

from .forms import EditarPrendaForm, FotoArmarioForm
from .models import FotoArmario


# REGISTRO DE USUARIOS
def registro(request):
    if request.user.is_authenticated:
        return redirect("mi_armario")

    formulario = UserCreationForm(
        request.POST or None
    )

    if request.method == "POST" and formulario.is_valid():
        usuario = formulario.save()
        login(request, usuario)
        messages.success(
            request,
            "Tu cuenta fue creada correctamente."
        )
        return redirect("mi_armario")

    return render(
        request,
        "armario/registro.html",
        {"formulario": formulario}
    )


# ARMARIO PRIVADO
@login_required
def mi_armario(request):
    formulario = FotoArmarioForm()

    if request.method == "POST":
        formulario = FotoArmarioForm(
            request.POST,
            request.FILES
        )

        if formulario.is_valid():
            prenda = formulario.save(commit=False)

            # Asociar la prenda al usuario actual
            prenda.propietario = request.user

            nombre_archivo = Path(
                request.FILES["imagen"].name
            ).stem

            prenda.nombre = (
                nombre_archivo.replace("_", " ")
                .replace("-", " ")
                .strip()[:120] or "Prenda"
            )

            prenda.save()

            messages.success(
                request,
                "Prenda guardada correctamente."
            )
            return redirect("mi_armario")



        else:
            print(
                "ERROR AL GUARDAR PRENDA:",
                formulario.errors.as_json()
            )

            messages.error(
                request,
                "No se pudo guardar la prenda. "
                "Revisa los datos seleccionados."
            )


    # Consultar SOLO las prendas del usuario actual
    prendas = FotoArmario.objects.filter(
        propietario=request.user
    ).order_by("-fecha_subida", "-pk")

    total_prendas = prendas.count()

    busqueda = (request.GET.get("q") or "").strip()[:80]
    categoria_actual = (
        request.GET.get("categoria") or ""
    ).strip()

    categorias_validas = {
        codigo for codigo, _ in FotoArmario.CATEGORIAS
    }

    if categoria_actual not in (
        categorias_validas | {"", "sin_categoria"}
    ):
        categoria_actual = ""

    if busqueda:
        prendas = prendas.filter(
            Q(nombre__icontains=busqueda)
            | Q(imagen__icontains=busqueda)
        )

    if categoria_actual == "sin_categoria":
        prendas = prendas.filter(
            Q(categoria="")
            | Q(categoria__isnull=True)
        )
    elif categoria_actual:
        prendas = prendas.filter(
            categoria=categoria_actual
        )

    paginador = Paginator(prendas, 8)
    pagina = paginador.get_page(
        request.GET.get("page")
    )

    rango_paginas = paginador.get_elided_page_range(
        number=pagina.number,
        on_each_side=1,
        on_ends=1
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


# EDITAR SOLO PRENDAS PROPIAS
@login_required
@require_POST
def editar_prenda(request, pk):
    prenda = get_object_or_404(
        FotoArmario,
        pk=pk,
        propietario=request.user
    )

    formulario = EditarPrendaForm(
        request.POST,
        instance=prenda
    )

    if formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            "Prenda actualizada correctamente."
        )
    else:
        messages.error(
            request,
            "No se pudo actualizar la prenda."
        )

    return redirect("mi_armario")


# ELIMINAR SOLO PRENDAS PROPIAS
@login_required
@require_POST
def eliminar_foto(request, pk):
    prenda = get_object_or_404(
        FotoArmario,
        pk=pk,
        propietario=request.user
    )

    prenda.imagen.delete(save=False)
    prenda.delete()

    messages.success(
        request,
        "Prenda eliminada correctamente."
    )
    return redirect("mi_armario")


# VISUALIZACION PRIVADA DE FOTOGRAFIAS
@login_required
@require_safe
def ver_imagen_privada(request, pk):
    prenda = get_object_or_404(
        FotoArmario,
        pk=pk,
        propietario=request.user
    )

    try:
        archivo = prenda.imagen.open("rb")
    except OSError:
        raise Http404("Fotografía no encontrada")

    tipo, _ = guess_type(prenda.imagen.name)

    respuesta = FileResponse(
        archivo,
        content_type=tipo or "application/octet-stream"
    )

    respuesta["Cache-Control"] = "private, no-store"
    respuesta["X-Content-Type-Options"] = "nosniff"

    return respuesta
