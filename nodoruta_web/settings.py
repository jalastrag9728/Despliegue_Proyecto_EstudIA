"""Configuración mínima de Django para el servicio Nodo Ruta."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-local-nodoruta-cambiar-en-produccion")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost,app1,app2,nodoruta,testserver",
    ).split(",")
    if h.strip()
]

INSTALLED_APPS = []

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "nodoruta_web.urls"
WSGI_APPLICATION = "nodoruta_web.wsgi.application"

# Los datos se leen desde DATA_PATH (data/pedidos.json) montado en solo lectura.
DATABASES = {}

LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True
APPEND_SLASH = False
