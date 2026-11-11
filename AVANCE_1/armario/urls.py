from django.urls import path
from . import views

urlpatterns = [
    path("", views.mi_armario, name="mi_armario"),
    path("eliminar/", views.eliminar_foto, name="eliminar_foto"),
    path("prenda/<int:pk>/editar/", views.editar_prenda, name="editar_prenda"),
    path("prenda/<int:pk>/eliminar/", views.eliminar_foto, name="eliminar_prenda"),
]
