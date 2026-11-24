"""Vistas HTTP de Nodo Ruta (mantiene el contrato de / , /health y /pedidos)."""
import json
import os
from pathlib import Path

from django.http import HttpResponse, JsonResponse

_PANEL_HTML = (Path(__file__).resolve().with_name("panel.html")).read_text(encoding="utf-8")


def _instancia():
    return os.environ.get("INSTANCE_ID", "instancia-ejemplo")


def _ruta_datos():
    return Path(os.environ.get("DATA_PATH", "pedidos.json"))


def _json(data, status=200):
    return JsonResponse(
        data,
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )


def _cargar_datos():
    data = json.loads(_ruta_datos().read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("pedidos"), list):
        raise ValueError("Formato de datos inválido")
    return data


def inicio(_request):
    inst = _instancia()
    try:
        _cargar_datos()
    except (OSError, ValueError, TypeError, AttributeError):
        return _json({"estado": "error_datos", "instancia": inst}, status=503)
    return _json(
        {
            "servicio": "Nodo Ruta - caso ficticio",
            "instancia": inst,
            "rutas": ["/health", "/pedidos"],
        }
    )


def health(_request):
    inst = _instancia()
    try:
        data = _cargar_datos()
    except (OSError, ValueError, TypeError, AttributeError):
        return _json({"estado": "error_datos", "instancia": inst}, status=503)
    return _json(
        {
            "estado": "ok",
            "instancia": inst,
            "version_datos": data.get("version"),
        }
    )


def pedidos(_request):
    inst = _instancia()
    try:
        data = _cargar_datos()
    except (OSError, ValueError, TypeError, AttributeError):
        return _json({"estado": "error_datos", "instancia": inst}, status=503)
    return _json({"instancia": inst, **data})


def panel(_request):
    return HttpResponse(_PANEL_HTML, content_type="text/html; charset=utf-8")


def no_encontrado(_request, _ruta=""):
    return _json({"error": "Ruta no disponible", "instancia": _instancia()}, status=404)
