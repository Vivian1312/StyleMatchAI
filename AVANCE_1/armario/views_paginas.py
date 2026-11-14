"""Vistas de Coincidencias (FashionCLIP) y Recomendaciones (reglas)."""

import logging
from urllib.parse import urlparse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import FotoArmario

logger = logging.getLogger(__name__)
from .motor_similitud import buscar_top_3_similares
from .reglas_outfits import (
    CATEGORIAS_NOMBRES,
    categorias_faltantes,
    generar_outfits,
    generar_outfits_prenda_externa,
)


def _formatear_outfits(outfits):
    """Serializacion de tarjetas; solo URL privada para prendas existentes."""
    salida = []
    for outfit in outfits:
        prendas = []
        for prenda in outfit["prendas"]:
            externa = prenda.pk == -1
            prendas.append({
                "id": None if externa else prenda.pk,
                "nombre": prenda.nombre,
                "categoria": CATEGORIAS_NOMBRES.get(prenda.categoria, "Otro"),
                "externa": externa,
                "imagen_url": None if externa else f"/prenda/{prenda.pk}/imagen/",
            })
        salida.append({
            "titulo": outfit["titulo"],
            "descripcion": outfit["descripcion"],
            "etiquetas": outfit["etiquetas"],
            "prendas": prendas,
        })
    return salida


@login_required
def coincidencias(request):
    total_prendas = (
        FotoArmario.objects.filter(propietario=request.user)
        .exclude(vector_caracteristicas__isnull=True)
        .exclude(vector_caracteristicas="")
        .count()
    )
    return render(request, "armario/coincidencias.html", {
        "total_prendas": total_prendas,
        "categorias": FotoArmario.CATEGORIAS,
    })


@login_required
@require_POST
def buscar_similares_api(request):
    """Mismo endpoint existente: busqueda, outfits existentes y simulacion.

    Mantiene compatible la ruta /coincidencias/buscar/ sin tocar urls.py.
    """
    accion = (request.POST.get("accion") or "buscar").strip()
    if accion in ("outfits_existente", "outfits_externa"):
        prendas = list(FotoArmario.objects.filter(propietario=request.user).order_by("-fecha_subida", "-pk"))
        if accion == "outfits_existente":
            try:
                prenda_id = int(request.POST.get("prenda_id", ""))
            except (ValueError, TypeError):
                return JsonResponse({"error": "Selecciona una prenda valida."}, status=400)
            prenda_base = next((p for p in prendas if p.pk == prenda_id), None)
            if prenda_base is None:
                return JsonResponse({"error": "La prenda no pertenece a tu armario."}, status=404)
            outfits = generar_outfits(prendas, prenda_base, max_resultados=3)
            faltantes = categorias_faltantes(prendas, prenda_base) if not outfits else []
        else:
            categoria = (request.POST.get("categoria") or "").strip()
            if categoria not in CATEGORIAS_NOMBRES:
                return JsonResponse({"error": "Corrige la categoria de la prenda externa antes de simular."}, status=400)
            outfits = generar_outfits_prenda_externa(prendas, categoria, max_resultados=3)
            if outfits:
                faltantes = []
            else:
                from types import SimpleNamespace
                base_virtual = SimpleNamespace(pk=-1, categoria=categoria)
                faltantes = categorias_faltantes([*prendas, base_virtual], base_virtual)
        return JsonResponse({"outfits": _formatear_outfits(outfits), "faltantes": faltantes})

    if accion != "buscar":
        return JsonResponse({"error": "Accion no reconocida."}, status=400)

    archivo = request.FILES.get("imagen")
    url_imagen = (request.POST.get("url_imagen") or "").strip()
    if not archivo and not url_imagen:
        return JsonResponse({"error": "Sube una imagen o pega su URL directa."}, status=400)

    if archivo:
        if archivo.size > 10 * 1024 * 1024:
            return JsonResponse({"error": "La imagen supera el limite maximo de 10 MB."}, status=400)
        fuente = archivo
    else:
        parsed = urlparse(url_imagen)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return JsonResponse({"error": "El enlace debe comenzar por http:// o https://."}, status=400)
        fuente = url_imagen

    categoria = (request.POST.get("categoria") or "auto").strip()
    permitidas = {"auto", "", "sin_categoria", *CATEGORIAS_NOMBRES}
    if categoria not in permitidas:
        return JsonResponse({"error": "Categoria de filtro no valida."}, status=400)
    orden = (request.POST.get("orden") or "desc").strip()
    if orden not in {"asc", "desc"}:
        return JsonResponse({"error": "Orden de resultados no valido."}, status=400)

    try:
        top_3, tiempo_ms, detectada = buscar_top_3_similares(
            fuente,
            usuario=request.user,
            categoria=categoria,
            orden=orden,
            devolver_metricas=True,
            incluir_categoria=True,
        )
        return JsonResponse({
            "resultados": top_3,
            "tiempo_ms": tiempo_ms,
            "categoria_detectada": detectada,
            "categoria_aplicada": detectada if categoria == "auto" else categoria,
            "clasificacion_automatica": categoria == "auto",
        })
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception:
        logger.exception("Error en consulta de similitud FashionCLIP")
        # No mostrar detalles de rutas / modelo en la respuesta publica.
        return JsonResponse({
            "error": "No se pudo analizar la imagen. Prueba con un archivo JPG/PNG o una URL directa a la fotografia."
        }, status=400)


@login_required
def recomendaciones(request):
    """Vista original de 1.3.4; se mantiene su comportamiento."""
    prendas = list(
        FotoArmario.objects.filter(propietario=request.user).order_by("-fecha_subida", "-pk")
    )
    categoria_filtro = ""
    seleccionada = prendas[0] if prendas else None
    busqueda_realizada = "prenda" in request.GET
    seleccion_invalida = False

    if busqueda_realizada:
        try:
            id_solicitado = int(request.GET.get("prenda", ""))
        except (ValueError, TypeError):
            id_solicitado = None
        seleccionada = next((p for p in prendas if p.pk == id_solicitado), None)
        seleccion_invalida = seleccionada is None

    outfits = []
    faltantes = []
    if busqueda_realizada and seleccionada is not None:
        outfits = generar_outfits(prendas, seleccionada, max_resultados=3)
        if not outfits:
            faltantes = categorias_faltantes(prendas, seleccionada)

    return render(request, "armario/recomendaciones.html", {
        "prendas": prendas,
        "seleccionada": seleccionada,
        "busqueda_realizada": busqueda_realizada,
        "seleccion_invalida": seleccion_invalida,
        "outfits": outfits,
        "faltantes": faltantes,
        "categorias": FotoArmario.CATEGORIAS,
        "categoria_filtro": categoria_filtro,
    })
