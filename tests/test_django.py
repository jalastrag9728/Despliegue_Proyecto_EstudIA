"""Pruebas unitarias para la aplicación Django de Nodo Ruta (sin Docker)."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nodoruta_web.settings")

import django  # noqa: E402

django.setup()

from django.test import Client  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


class PruebasDjango(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name) / "pedidos.json"
        shutil.copy2(RAIZ / "pedidos.json", self.work)

        self._prev_data = os.environ.get("DATA_PATH")
        self._prev_inst = os.environ.get("INSTANCE_ID")
        os.environ["DATA_PATH"] = str(self.work)
        os.environ["INSTANCE_ID"] = "django-test"
        self.addCleanup(self._restaurar_env)
        self.client = Client()

    def _restaurar_env(self):
        if self._prev_data is None:
            os.environ.pop("DATA_PATH", None)
        else:
            os.environ["DATA_PATH"] = self._prev_data
        if self._prev_inst is None:
            os.environ.pop("INSTANCE_ID", None)
        else:
            os.environ["INSTANCE_ID"] = self._prev_inst

    def test_inicio_health_y_pedidos(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["instancia"], "django-test")

        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {"estado": "ok", "instancia": "django-test", "version_datos": "datos-v1"},
        )

        r = self.client.get("/pedidos")
        self.assertEqual(r.status_code, 200)
        datos = r.json()
        self.assertEqual(datos["instancia"], "django-test")
        self.assertEqual(len(datos["pedidos"]), 6)

    def test_ruta_inexistente_404(self):
        r = self.client.get("/nada")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["instancia"], "django-test")

    def test_datos_danados_devuelve_503(self):
        self.work.write_text("{ json roto", encoding="utf-8")
        self.assertEqual(self.client.get("/health").status_code, 503)
        self.assertEqual(self.client.get("/pedidos").status_code, 503)

    def test_panel_html(self):
        r = self.client.get("/panel")
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r["Content-Type"])
        self.assertIn("Nodo Ruta", r.content.decode("utf-8"))
