"""Vista de interfaz 1.3.3. No realiza inferencia de inteligencia artificial."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import FotoArmario


@login_required
def coincidencias(request):
    """Muestra la interfaz de consulta externa sin simular coincidencias reales."""
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
    """Pagina de destino provisional para la siguiente actividad EDT."""
    return render(request, "armario/recomendaciones.html")
