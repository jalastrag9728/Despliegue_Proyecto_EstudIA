"""Pruebas unitarias mínimas de la app (no requieren Docker): python -m unittest discover -s tests -v"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SEMILLA = RAIZ / "app" / "seed" / "pedidos.json"
sys.path.insert(0, str(RAIZ / "app"))
import app as servicio  # noqa: E402


def pedir(base, ruta):
    try:
        with urllib.request.urlopen(base + ruta, timeout=3) as r:
            return r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()


class PruebasApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.archivo = Path(cls.tmp.name) / "pedidos.json"
        cls.archivo.write_text(SEMILLA.read_text(encoding="utf-8"), encoding="utf-8")
        servicio.DATA_FILE = str(cls.archivo)
        servicio.INSTANCIA = "instancia-test"
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), servicio.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def setUp(self):
        self.archivo.write_text(SEMILLA.read_text(encoding="utf-8"), encoding="utf-8")

    def test_semilla_tiene_seis_pedidos_y_version(self):
        d = json.loads(SEMILLA.read_text(encoding="utf-8"))
        self.assertEqual(len(d["pedidos"]), 6)
        self.assertTrue(d["version_datos"])

    def test_pedidos_e_instancia(self):
        st, h, cuerpo = pedir(self.base, "/pedidos")
        self.assertEqual(st, 200)
        self.assertEqual(h["X-Instance"], "instancia-test")
        d = json.loads(cuerpo)
        self.assertEqual(d["total"], 6)
        self.assertEqual(d["instancia"], "instancia-test")

    def test_filtro_y_detalle(self):
        _, _, c = pedir(self.base, "/pedidos?estado=entregado")
        self.assertEqual(json.loads(c)["total"], 2)
        st, _, _ = pedir(self.base, "/pedidos/NR-1001")
        self.assertEqual(st, 200)
        st, _, _ = pedir(self.base, "/pedidos/NO-EXISTE")
        self.assertEqual(st, 404)

    def test_health_ok_y_degradado(self):
        st, _, _ = pedir(self.base, "/health")
        self.assertEqual(st, 200)
        self.archivo.write_text("{ esto no es json", encoding="utf-8")
        st, _, _ = pedir(self.base, "/health")
        self.assertEqual(st, 503)

    def test_cambio_de_datos_se_ve_sin_reiniciar(self):
        d = json.loads(self.archivo.read_text(encoding="utf-8"))
        d["version_datos"] = "alterada"
        self.archivo.write_text(json.dumps(d), encoding="utf-8")
        _, _, c = pedir(self.base, "/pedidos")
        self.assertEqual(json.loads(c)["version_datos"], "alterada")

    def test_inicio_html(self):
        st, h, c = pedir(self.base, "/")
        self.assertEqual(st, 200)
        self.assertIn("text/html", h["Content-Type"])
        self.assertIn("instancia-test", c)


if __name__ == "__main__":
    unittest.main()
