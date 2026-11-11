from django.db import models


class FotoArmario(models.Model):
    CATEGORIAS = [
        ("tops", "Tops"),
        ("pantalones", "Pantalones"),
        ("chaquetas", "Chaquetas"),
        ("vestidos", "Vestidos"),
        ("faldas", "Faldas"),
        ("calzado", "Calzado"),
        ("accesorios", "Accesorios"),
    ]

    # Los campos preexistentes se conservan para no afectar al motor visual.
    imagen = models.ImageField(upload_to="prendas/")
    fecha_subida = models.DateTimeField(auto_now_add=True)
    vector_caracteristicas = models.TextField(blank=True, null=True)

    # Campos opcionales: las fotos ya almacenadas permanecen sin categoria.
    nombre = models.CharField(max_length=120, blank=True, default="")
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIAS,
        blank=True,
        default="",
    )

    def __str__(self):
        return self.nombre or f"Prenda {self.pk}"
