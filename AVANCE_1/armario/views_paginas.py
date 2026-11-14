"""Vistas de coincidencias con inferencia real Fashion-CLIP (Top 3)."""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import FotoArmario
from .motor_similitud import buscar_top_3_similares


@login_required
def coincidencias(request):
    """Muestra la interfaz de busqueda de coincidencias reales."""
    total_prendas = FotoArmario.objects.exclude(
        vector_caracteristicas__isnull=True
    ).exclude(vector_caracteristicas="").count()
    return render(
        request,
        "armario/coincidencias.html",
        {"total_prendas": total_prendas},
    )


@login_required
@require_POST
def buscar_similares_api(request):
    """Recibe una imagen externa y devuelve el Top 3 mas similar por coseno."""
    archivo = request.FILES.get("imagen")
    if not archivo:
        return JsonResponse({"error": "No se recibio ninguna imagen."}, status=400)

    try:
        top_3 = buscar_top_3_similares(archivo, usuario=request.user)
        return JsonResponse({"resultados": top_3})
    except Exception as e:
        return JsonResponse({"error": f"Error procesando imagen: {str(e)}"}, status=500)


@login_required
def recomendaciones(request):
    """Pagina de destino provisional para la siguiente actividad EDT."""
    return render(request, "armario/recomendaciones.html")
