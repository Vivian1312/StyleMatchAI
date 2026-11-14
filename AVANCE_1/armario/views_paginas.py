"""Vistas de coincidencias con validacion de consultas y optimizacion de rendimiento."""

from urllib.parse import urlparse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import FotoArmario
from .motor_similitud import buscar_top_3_similares


@login_required
def coincidencias(request):
    """Muestra la interfaz de busqueda con filtros de categoria y orden."""
    total_prendas = (
        FotoArmario.objects.exclude(vector_caracteristicas__isnull=True)
        .exclude(vector_caracteristicas="")
        .count()
    )
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
    """Valida archivo o URL externa y devuelve el Top 3 con metricas de tiempo."""
    archivo = request.FILES.get("imagen")
    url_imagen = (request.POST.get("url_imagen") or "").strip()

    if not archivo and not url_imagen:
        return JsonResponse(
            {"error": "Debes subir una imagen JPG/PNG o pegar un enlace valido."},
            status=400,
        )

    fuente = None
    if archivo:
        if archivo.size > 10 * 1024 * 1024:
            return JsonResponse(
                {"error": "La imagen supera el limite maximo de 10 MB."},
                status=400,
            )
        fuente = archivo
    else:
        parsed = urlparse(url_imagen)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return JsonResponse(
                {"error": "El enlace debe comenzar por http:// o https://."},
                status=400,
            )
        fuente = url_imagen

    categoria = (request.POST.get("categoria") or "").strip()
    orden = (request.POST.get("orden") or "desc").strip()

    try:
        top_3, tiempo_ms = buscar_top_3_similares(
            fuente,
            usuario=request.user,
            categoria=categoria,
            orden=orden,
            devolver_metricas=True,
        )
        return JsonResponse({"resultados": top_3, "tiempo_ms": tiempo_ms})
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception:
        return JsonResponse(
            {
                "error": "No se pudo leer la imagen. Verifica que el archivo no este danado o que el enlace apunte directo a una foto JPG/PNG."
            },
            status=400,
        )


@login_required
def recomendaciones(request):
    """Pagina de destino provisional para la siguiente actividad EDT."""
    return render(request, "armario/recomendaciones.html")
