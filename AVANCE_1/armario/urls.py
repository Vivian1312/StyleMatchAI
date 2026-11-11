from django.urls import path
from django.contrib.auth import views as auth_views
from . import views_paginas
from . import views


urlpatterns = [
    # Armario
    path(
        "",
        views.mi_armario,
        name="mi_armario"
    ),

    # Registro
    path(
        "cuenta/registro/",
        views.registro,
        name="registro"
    ),

    # Inicio de sesion
    path(
        "cuenta/iniciar-sesion/",
        auth_views.LoginView.as_view(
            template_name="armario/inicio_sesion.html"
        ),
        name="login"
    ),

    # Cierre de sesion
    path(
        "cuenta/cerrar-sesion/",
        auth_views.LogoutView.as_view(),
        name="logout"
    ),

    # Editar una prenda
    path(
        "prenda/<int:pk>/editar/",
        views.editar_prenda,
        name="editar_prenda"
    ),

    # Eliminar una prenda
    path(
        "prenda/<int:pk>/eliminar/",
        views.eliminar_foto,
        name="eliminar_prenda"
    ),

    # Consultar imagen privada
    path(
        "prenda/<int:pk>/imagen/",
        views.ver_imagen_privada,
        name="ver_imagen_privada"
    ),


    path(
        "coincidencias/",
        views_paginas.coincidencias,
        name="coincidencias"
    ),

    path(
        "recomendaciones/",
        views_paginas.recomendaciones,
        name="recomendaciones"
    ),

]
