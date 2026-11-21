"""Pruebas locales SIN Docker. Ejecutar:  python -m unittest discover -s tests -v

Verifican (1) la app original y (2) el ciclo de datos preparar/respaldar/simular-error/restaurar,
incluyendo los rechazos de seguridad (respaldo alterado, ruta fuera de respaldos).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import importlib.util
from http.server import ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def cargar_app(ruta_datos, instancia):
    spec = importlib.util.spec_from_file_location("nodo_app_test", RAIZ / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.DATA = Path(ruta_datos)
    mod.INSTANCE = instancia
    return mod


def get(base, ruta):
    try:
        with urllib.request.urlopen(base + ruta, timeout=3) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


class Entorno:
    """Copia temporal del paquete (mismas rutas relativas que usa datos.py)."""
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "scripts").mkdir()
        shutil.copy2(RAIZ / "pedidos.json", self.dir / "pedidos.json")
        shutil.copy2(RAIZ / "scripts" / "datos.py", self.dir / "scripts" / "datos.py")

    def datos(self, *args):
        p = subprocess.run([sys.executable, str(self.dir / "scripts" / "datos.py"), *args],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr


class PruebasApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = Entorno()
        cls.env.datos("preparar")
        cls.work = cls.env.dir / "data" / "pedidos.json"
        cls.mod = cargar_app(cls.work, "app-test")
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), cls.mod.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close(); cls.env.tmp.cleanup()

    def test_conjunto_original_tiene_seis_pedidos(self):
        d = json.loads((RAIZ / "pedidos.json").read_text(encoding="utf-8"))
        self.assertEqual(d["version"], "datos-v1")
        self.assertEqual(len(d["pedidos"]), 6)

    def test_health_pedidos_e_instancia(self):
        st, d = get(self.base, "/health")
        self.assertEqual((st, d["estado"], d["instancia"], d["version_datos"]), (200, "ok", "app-test", "datos-v1"))
        st, d = get(self.base, "/pedidos")
        self.assertEqual((st, len(d["pedidos"]), d["instancia"]), (200, 6, "app-test"))

    def test_ruta_inexistente_404(self):
        self.assertEqual(get(self.base, "/nada")[0], 404)


class PruebasDatos(unittest.TestCase):
    def setUp(self):
        self.env = Entorno()
        self.addCleanup(self.env.tmp.cleanup)
        self.work = self.env.dir / "data" / "pedidos.json"
        self.original = (self.env.dir / "pedidos.json").read_bytes()

    def test_ciclo_completo_respaldar_error_restaurar(self):
        rc, out = self.env.datos("preparar"); self.assertEqual(rc, 0, out)
        self.assertEqual(self.work.read_bytes(), self.original)
        rc, out = self.env.datos("respaldar"); self.assertEqual(rc, 0, out)
        ruta = out.split("Respaldo creado:")[1].strip().replace("\\", "/")
        self.assertTrue(ruta.startswith("respaldos/"))
        rc, out = self.env.datos("simular-error"); self.assertEqual(rc, 0, out)
        with self.assertRaises(ValueError):
            json.loads(self.work.read_text(encoding="utf-8"))
        rc, out = self.env.datos("restaurar", "--respaldo", ruta); self.assertEqual(rc, 0, out)
        self.assertEqual(self.work.read_bytes(), self.original)

    def test_preparar_no_sobrescribe(self):
        self.env.datos("preparar")
        self.work.write_text('{"version":"x","pedidos":[]}', encoding="utf-8")
        rc, _ = self.env.datos("preparar")
        self.assertNotEqual(rc, 0)
        self.assertIn('"x"', self.work.read_text(encoding="utf-8"))

    def test_respaldo_alterado_se_rechaza(self):
        self.env.datos("preparar")
        _, out = self.env.datos("respaldar")
        ruta = out.split("Respaldo creado:")[1].strip()
        (self.env.dir / ruta).write_text('{"version":"malicioso","pedidos":[]}', encoding="utf-8")
        rc, out = self.env.datos("restaurar", "--respaldo", ruta)
        self.assertNotEqual(rc, 0)
        self.assertIn("huella", out)
        self.assertEqual(self.work.read_bytes(), self.original)   # la copia de trabajo no se tocó

    def test_ruta_fuera_de_respaldos_se_rechaza(self):
        self.env.datos("preparar")
        rc, out = self.env.datos("restaurar", "--respaldo", "pedidos.json")
        self.assertNotEqual(rc, 0)
        self.assertIn("dentro de", out)


if __name__ == "__main__":
    unittest.main()
