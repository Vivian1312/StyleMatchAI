"""Vectoriza las prendas existentes de un usuario sin eliminar imágenes."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from armario.models import FotoArmario
from armario.servicio_vectores import vectorizar_prenda


class Command(BaseCommand):
    help = "Calcula embeddings FashionCLIP para prendas existentes de un usuario."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True, help="Nombre de usuario Django")
        parser.add_argument("--forzar", action="store_true", help="Recalcular también los vectores existentes")

    def handle(self, *args, **options):
        nombre = options["usuario"]
        usuario = get_user_model().objects.filter(username=nombre).first()
        if usuario is None:
            raise CommandError(f"El usuario '{nombre}' no existe.")

        prendas = FotoArmario.objects.filter(propietario=usuario).order_by("pk")
        if not options["forzar"]:
            prendas = prendas.filter(
                Q(vector_caracteristicas__isnull=True) | Q(vector_caracteristicas="")
            )

        total = prendas.count()
        exitos = 0
        fallidos = 0
        self.stdout.write(f"Fotografías pendientes: {total}")
        for prenda in prendas.iterator():
            try:
                vectorizar_prenda(prenda)
                exitos += 1
                self.stdout.write(self.style.SUCCESS(f"OK prenda #{prenda.pk}: {prenda.nombre}"))
            except Exception as exc:
                fallidos += 1
                self.stderr.write(f"ERROR prenda #{prenda.pk}: {type(exc).__name__}: {exc}")

        self.stdout.write(f"Proceso terminado. Correctas: {exitos}. Fallidas: {fallidos}.")
        if fallidos:
            raise CommandError("Algunas prendas no se pudieron vectorizar; no se eliminaron datos.")
