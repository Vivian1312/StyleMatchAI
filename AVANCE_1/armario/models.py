from django.db import models


class FotoArmario(models.Model):
    imagen = models.ImageField(upload_to="prendas/")
    fecha_subida = models.DateTimeField(auto_now_add=True)
    vector_caracteristicas = models.TextField(blank=True, null=True) # Nuevo campo para el vector

    def __str__(self):
        return f"Fotografía {self.id}"
