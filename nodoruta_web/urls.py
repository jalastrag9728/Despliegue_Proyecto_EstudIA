"""Rutas HTTP de Nodo Ruta."""
from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.inicio),
    path("health", views.health),
    path("pedidos", views.pedidos),
    path("panel", views.panel),
    path("panel/", views.panel),
    re_path(r"^(?P<_ruta>.+)$", views.no_encontrado),
]
