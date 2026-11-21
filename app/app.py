#!/usr/bin/env python3
"""Servicio de consulta de entregas de Nodo Ruta (aplicación DEMOSTRATIVA).

- Solo usa la biblioteca estándar de Python (sin dependencias que instalar).
- Lee el archivo de datos en CADA solicitud, de modo que cualquier cambio o
  restauración del archivo se ve de inmediato, sin reiniciar el contenedor.
- Cada respuesta indica qué instancia la atendió (cabecera X-Instance y campo
  "instancia") y cada solicitud queda registrada en JSON por la salida estándar.
"""
import html
import json
import os
import signal
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DATA_FILE = os.environ.get("DATA_FILE", "/data/pedidos.json")
PORT = int(os.environ.get("PORT", "8000"))
INSTANCIA = os.environ.get("INSTANCE_NAME") or socket.gethostname()
APP_VERSION = os.environ.get("APP_VERSION", "local")


class DatosInvalidos(Exception):
    """El archivo de datos no existe o no tiene el formato esperado."""


def cargar_datos(ruta=None):
    ruta = ruta or DATA_FILE
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            datos = json.load(fh)
    except (OSError, ValueError) as exc:
        raise DatosInvalidos(f"No se pudo leer {ruta}: {exc}") from exc
    if not isinstance(datos, dict) or "version_datos" not in datos or not isinstance(datos.get("pedidos"), list):
        raise DatosInvalidos("El archivo no tiene 'version_datos' y 'pedidos'.")
    return datos


def log(**campos):
    campos = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "instancia": INSTANCIA, **campos}
    sys.stdout.write(json.dumps(campos, ensure_ascii=False) + "\n")
    sys.stdout.flush()


class Handler(BaseHTTPRequestHandler):
    server_version = "NodoRutaDemo/1.0"
    sys_version = ""

    # --- utilidades -------------------------------------------------------
    def _enviar(self, status, cuerpo, tipo="application/json; charset=utf-8"):
        data = cuerpo if isinstance(cuerpo, bytes) else cuerpo.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Instance", INSTANCIA)
        self.send_header("X-App-Version", APP_VERSION)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
        self._status = status

    def _json(self, status, obj):
        self._enviar(status, json.dumps(obj, ensure_ascii=False, indent=2))

    def log_message(self, *_args):  # silencia el log por defecto; usamos log()
        pass

    # --- rutas ------------------------------------------------------------
    def do_GET(self):
        t0 = time.perf_counter()
        self._status = 500
        url = urlparse(self.path)
        try:
            self._ruteo(url)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:  # error inesperado: se registra y se responde 500
            try:
                self._json(500, {"error": "error_interno", "instancia": INSTANCIA})
            finally:
                log(nivel="error", error=str(exc))
        finally:
            log(nivel="info", metodo="GET", ruta=url.path, status=self._status,
                ms=round((time.perf_counter() - t0) * 1000, 2),
                cliente=self.headers.get("X-Forwarded-For", self.client_address[0]))

    def _ruteo(self, url):
        ruta = url.path.rstrip("/") or "/"
        if ruta == "/":
            return self._inicio()
        if ruta == "/health":
            return self._health()
        if ruta == "/pedidos":
            return self._pedidos(parse_qs(url.query))
        if ruta.startswith("/pedidos/"):
            return self._pedido(ruta.split("/", 2)[2])
        self._json(404, {"error": "no_encontrado", "instancia": INSTANCIA})

    def _health(self):
        # Una instancia está sana si el proceso responde Y puede leer datos válidos.
        try:
            datos = cargar_datos()
        except DatosInvalidos as exc:
            return self._json(503, {"estado": "degradado", "motivo": str(exc), "instancia": INSTANCIA})
        self._json(200, {"estado": "ok", "instancia": INSTANCIA,
                         "app_version": APP_VERSION, "version_datos": datos["version_datos"]})

    def _pedidos(self, consulta):
        try:
            datos = cargar_datos()
        except DatosInvalidos as exc:
            return self._json(503, {"error": "datos_no_disponibles", "detalle": str(exc), "instancia": INSTANCIA})
        pedidos = datos["pedidos"]
        estado = (consulta.get("estado") or [None])[0]
        if estado:
            pedidos = [p for p in pedidos if str(p.get("estado", "")).lower() == estado.lower()]
        self._json(200, {"instancia": INSTANCIA, "version_datos": datos["version_datos"],
                         "total": len(pedidos), "pedidos": pedidos})

    def _pedido(self, pedido_id):
        try:
            datos = cargar_datos()
        except DatosInvalidos as exc:
            return self._json(503, {"error": "datos_no_disponibles", "detalle": str(exc), "instancia": INSTANCIA})
        for p in datos["pedidos"]:
            if p.get("id") == pedido_id:
                return self._json(200, {"instancia": INSTANCIA, "version_datos": datos["version_datos"], "pedido": p})
        self._json(404, {"error": "pedido_no_encontrado", "id": pedido_id, "instancia": INSTANCIA})

    def _inicio(self):
        try:
            version = cargar_datos()["version_datos"]
        except DatosInvalidos:
            version = "no disponible"
        pagina = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Nodo Ruta - Consulta de entregas</title>
<style>body{{font-family:system-ui,sans-serif;max-width:640px;margin:3rem auto;padding:0 1rem;color:#1b2a41}}
code{{background:#eef2f7;padding:2px 6px;border-radius:4px}}.tag{{color:#b45309}}</style></head><body>
<h1>Nodo Ruta - Consulta de entregas</h1>
<p class="tag">Aplicación demostrativa con datos sintéticos.</p>
<ul><li>Atendido por la instancia: <code>{html.escape(INSTANCIA)}</code></li>
<li>Versión de la aplicación: <code>{html.escape(APP_VERSION)}</code></li>
<li>Versión de los datos: <code>{html.escape(str(version))}</code></li></ul>
<p>Rutas: <a href="/pedidos">/pedidos</a> &middot; <a href="/health">/health</a></p>
</body></html>"""
        self._enviar(200, pagina, "text/html; charset=utf-8")


def main():
    servidor = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    servidor.daemon_threads = True

    def apagar(*_):
        # Cierre ordenado ante SIGTERM (docker stop); evita esperar 10 s a un SIGKILL.
        log(nivel="info", evento="apagando")
        threading.Thread(target=servidor.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, apagar)
    signal.signal(signal.SIGINT, apagar)
    log(nivel="info", evento="iniciado", puerto=PORT, data_file=DATA_FILE, app_version=APP_VERSION)
    servidor.serve_forever()
    servidor.server_close()
    log(nivel="info", evento="detenido")


if __name__ == "__main__":
    main()
