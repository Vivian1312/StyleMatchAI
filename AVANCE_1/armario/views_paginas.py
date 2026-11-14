"""Vistas de coincidencias con filtro de categoria y ordenamiento por similitud."""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import FotoArmario
from .motor_similitud import buscar_top_3_similares


@login_required
def coincidencias(request):
    """Muestra la interfaz de busqueda con filtros de categoria y orden."""
    total_prendas = FotoArmario.objects.exclude(
        vector_caracteristicas__isnull=True
    ).exclude(vector_caracteristicas="").count()
    return render(
        request,
        "armario/coincidencias.html",
        {
            "total_prendas": total_prendas,
            "categorias": FotoArmario.CATEGORIAS,
        },
    )


@login_required
@require_POST
def buscar_similares_api(request):
    """Recibe imagen, categoria y orden, y devuelve el Top 3 filtrado y ordenado."""
    archivo = request.FILES.get("imagen")
    if not archivo:
        return JsonResponse({"error": "No se recibio ninguna imagen."}, status=400)

    categoria = (request.POST.get("categoria") or "").strip()
    orden = (request.POST.get("orden") or "desc").strip()

    try:
        top_3 = buscar_top_3_similares(
            archivo,
            usuario=request.user,
            categoria=categoria,
            orden=orden,
        )
        return JsonResponse({"resultados": top_3})
    except Exception as e:
        return JsonResponse({"error": f"Error procesando imagen: {str(e)}"}, status=500)


@login_required
def recomendaciones(request):
    """Pagina de destino provisional para la siguiente actividad EDT."""
    return render(request, "armario/recomendaciones.html")
