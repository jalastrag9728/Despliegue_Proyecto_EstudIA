#!/usr/bin/env python3
"""Pruebas automáticas del MVP de Nodo Ruta (solo biblioteca estándar; requiere Docker).

Ejecuta los tres escenarios del caso y deja evidencias en ./evidencias/:
  1) Funcionamiento normal  -> el punto de acceso común reparte entre instancias.
  2) Caída de una instancia -> el servicio sigue respondiendo; se mide el tiempo y los errores.
  3) Recrear contenedores   -> los datos se conservan fuera del almacenamiento efímero.
  4) Pérdida/alteración de datos -> respaldo, alteración, restauración y tiempo de recuperación.

Uso:  python scripts/pruebas.py            (borra el volumen de datos al inicio para partir de cero)
      python scripts/pruebas.py --sin-reinicio   (reutiliza el despliegue actual)
      python scripts/pruebas.py --limpiar        (al terminar, apaga todo con "docker compose down -v")

IMPORTANTE: una demostración local NO demuestra alta disponibilidad de producción ni tolerancia a la
caída de un centro de datos. Ver docs/LIMITACIONES.md.
"""
import argparse
import csv
import datetime as dt
import io
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EVID = RAIZ / "evidencias"
URL = "http://127.0.0.1:8080"
URL_STATS = "http://127.0.0.1:8404/stats;csv"

resultados = []


# ----------------------------------------------------------------------------- utilidades
def ejecutar(cmd, check=True):
    p = subprocess.run(cmd, cwd=RAIZ, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise RuntimeError(f"Falló: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p


def compose(*args, check=True):
    return ejecutar(["docker", "compose", *args], check=check)


def ops(*args):
    """Ejecuta una operación de datos y devuelve sus líneas CLAVE=valor como diccionario."""
    p = compose("run", "--rm", "-T", "ops", *args)
    salida = {}
    for linea in p.stdout.splitlines():
        if "=" in linea:
            k, v = linea.split("=", 1)
            salida[k.strip()] = v.strip()
    return salida


def get(ruta, timeout=2.0):
    """GET al punto de acceso común. Devuelve (status|None, instancia|None, cuerpo_json|None)."""
    try:
        with urllib.request.urlopen(URL + ruta, timeout=timeout) as r:
            cuerpo = r.read().decode()
            try:
                datos = json.loads(cuerpo)
            except ValueError:
                datos = None
            return r.status, r.headers.get("X-Instance"), datos
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("X-Instance"), None
    except Exception:
        return None, None, None


def esperar(condicion, timeout, paso=0.5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        valor = condicion()
        if valor:
            return valor, time.time() - t0
        time.sleep(paso)
    return None, time.time() - t0


def instancias_activas(n=12):
    vistas = set()
    for _ in range(n):
        st, inst, _ = get("/health")
        if st == 200 and inst:
            vistas.add(inst)
    return vistas


def estado_balanceador():
    try:
        with urllib.request.urlopen(URL_STATS, timeout=2) as r:
            filas = list(csv.DictReader(io.StringIO(r.read().decode().lstrip("# "))))
        return {f["svname"]: f["status"] for f in filas if f["pxname"] == "servicio" and f["svname"].startswith("app")}
    except Exception as exc:
        return {"error": str(exc)}


def ids_contenedores_app():
    return [x for x in compose("ps", "-q", "app").stdout.split() if x]


def hostname(cid):
    return ejecutar(["docker", "inspect", "--format", "{{.Config.Hostname}}", cid]).stdout.strip()


def registrar(nombre, ok, detalle, metricas=None):
    resultados.append({"prueba": nombre, "resultado": "APROBADA" if ok else "FALLIDA",
                       "detalle": detalle, "metricas": metricas or {}})
    print(f"[{'OK ' if ok else 'FALLO'}] {nombre}: {detalle}")


# ----------------------------------------------------------------------------- pruebas
def desplegar(desde_cero):
    print(">> Desplegando (esto puede tardar la primera vez: descarga imágenes)...")
    if desde_cero:
        compose("down", "-v", "--remove-orphans")
    compose("up", "-d", "--build")
    ok, t = esperar(lambda: len(instancias_activas(10)) >= 2, 90)
    registrar("0. Despliegue reproducible", bool(ok),
              f"2 instancias respondiendo por el punto de acceso común en {t:.1f} s" if ok
              else "No se alcanzaron 2 instancias sanas en 90 s", {"segundos_hasta_listo": round(t, 1)})
    if not ok:
        raise SystemExit(finalizar(1))


def prueba_normal():
    estados = [get("/pedidos") for _ in range(20)]
    oks = [e for e in estados if e[0] == 200]
    inst = {e[1] for e in oks}
    versiones = {e[2]["version_datos"] for e in oks if e[2]}
    totales = {e[2]["total"] for e in oks if e[2]}
    ok = len(oks) == 20 and len(inst) >= 2 and totales == {6}
    registrar("1. Funcionamiento normal", ok,
              f"{len(oks)}/20 respuestas 200; instancias que atendieron: {sorted(inst)}; versión de datos: {sorted(versiones)}",
              {"instancias": sorted(inst), "estado_balanceador": estado_balanceador()})
    return next(iter(versiones), None)


def prueba_caida_instancia():
    ids = ids_contenedores_app()
    if len(ids) < 2:
        registrar("2. Caída de una instancia", False, "Se necesitan al menos 2 instancias en ejecución")
        return
    victima = ids[0]
    nombre_v = hostname(victima)
    t_stop = time.time()
    ejecutar(["docker", "stop", victima])
    dur_stop = time.time() - t_stop

    # Consulta continua (10 solicitudes/s durante 15 s) para registrar errores o interrupciones
    muestras, t0 = [], time.time()
    while time.time() - t0 < 15:
        ts = time.time() - t0
        st, inst, _ = get("/pedidos", timeout=3)
        muestras.append((ts, st, inst))
        time.sleep(0.1)
    errores = [m for m in muestras if m[1] != 200]
    atendieron = {m[2] for m in muestras if m[1] == 200}
    # ventana de error más larga (segundos entre el primer y el último error consecutivo)
    ventana = 0.0
    inicio = None
    for ts, st, _ in muestras:
        if st != 200:
            inicio = ts if inicio is None else inicio
            ventana = max(ventana, ts - inicio)
        else:
            inicio = None
    ok = (len(errores) / len(muestras) <= 0.05) and nombre_v not in atendieron and len(atendieron) >= 1
    registrar("2a. Caída de una instancia (conmutación)", ok,
              f"Instancia detenida: {nombre_v}. {len(muestras)} consultas, {len(errores)} con error "
              f"(ventana máx. {ventana:.1f} s). Atendió: {sorted(i for i in atendieron if i)}",
              {"instancia_detenida": nombre_v, "consultas": len(muestras), "errores": len(errores),
               "ventana_error_max_s": round(ventana, 2), "tiempo_docker_stop_s": round(dur_stop, 2),
               "estado_balanceador_tras_caida": estado_balanceador()})

    # Reintegro de la instancia
    t_start = time.time()
    ejecutar(["docker", "start", victima])
    vistas, t = esperar(lambda: nombre_v in instancias_activas(10), 90)
    registrar("2b. Reintegro de la instancia", bool(vistas),
              f"{nombre_v} volvió a atender tras {t:.1f} s" if vistas else f"{nombre_v} no volvió en 90 s",
              {"segundos_hasta_reintegro": round(time.time() - t_start, 1),
               "estado_balanceador": estado_balanceador()})


def prueba_persistencia(version_antes):
    antes = {hostname(c) for c in ids_contenedores_app()}
    sha_antes = ops("status").get("SHA256")
    t0 = time.time()
    compose("up", "-d", "--force-recreate", "--no-deps", "app")

    def listo():
        act = instancias_activas(10)
        return len(act) >= 2 and not (act & antes)

    ok_rec, t = esperar(listo, 120)
    st, inst, datos = get("/pedidos")
    sha_despues = ops("status").get("SHA256")
    version_despues = datos["version_datos"] if datos else None
    ok = bool(ok_rec) and version_despues == version_antes and sha_antes == sha_despues and datos and datos["total"] == 6
    registrar("3. Recrear contenedores conserva los datos", ok,
              f"Contenedores nuevos (distintos a {sorted(antes)}); versión {version_antes} -> {version_despues}; "
              f"hash de datos {'idéntico' if sha_antes == sha_despues else 'DIFERENTE'}; listos en {t:.1f} s",
              {"segundos_recreacion": round(time.time() - t0, 1), "sha256": sha_despues})


def prueba_respaldo_restauracion(version_original):
    b = ops("backup")
    archivo, sha_resp = b.get("BACKUP_FILE"), b.get("SHA256")
    registrar("4a. Respaldo creado fuera de la copia de trabajo", bool(archivo),
              f"{archivo} (versión {b.get('VERSION')}, sha256 {str(sha_resp)[:12]}...)",
              {"archivo": archivo, "sha256": sha_resp})
    if not archivo:
        return

    ops("tamper")
    _, inst, datos = get("/pedidos")
    alterado = bool(datos) and datos["version_datos"] != version_original
    registrar("4b. Alteración de la copia de trabajo detectada", alterado,
              f"El servicio ahora reporta versión '{datos['version_datos'] if datos else '?'}' (esperada: {version_original})")

    t0 = time.time()                       # el tiempo de recuperación se mide desde la detección
    r = ops("restore", archivo)

    def recuperado():
        _, _, d = get("/pedidos")
        return d if d and d["version_datos"] == version_original and d["total"] == 6 else None

    d, _ = esperar(recuperado, 30, paso=0.2)
    rto = time.time() - t0
    sha_final = ops("status").get("SHA256")
    ok = bool(d) and sha_final == sha_resp
    registrar("4c. Restauración y tiempo de recuperación", ok,
              f"Versión recuperada {d['version_datos'] if d else '?'}; hash {'coincide' if sha_final == sha_resp else 'NO coincide'} "
              f"con el respaldo; tiempo de recuperación medido: {rto:.1f} s (incluye el arranque del contenedor de operaciones)",
              {"rto_segundos": round(rto, 2), "restaurado_desde": r.get("RESTORED_FROM")})


# ----------------------------------------------------------------------------- informe
def finalizar(codigo_previo=0):
    EVID.mkdir(exist_ok=True)
    marca = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    (EVID / f"resultado_{marca}.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    logs = compose("logs", "--no-color", "--tail", "300", "balanceador", "app", check=False).stdout
    (EVID / f"registros_{marca}.log").write_text(logs, encoding="utf-8")
    lineas = [f"# Evidencias de pruebas - {marca}", "",
              "| Prueba | Resultado | Detalle |", "|---|---|---|"]
    for r in resultados:
        lineas.append(f"| {r['prueba']} | {r['resultado']} | {r['detalle'].replace('|', '/')} |")
    lineas += ["", "Registros consultados: `registros_%s.log` (balanceador + instancias)." % marca, "",
               "> Prueba local con contenedores en un solo computador: NO demuestra alta disponibilidad de producción "
               "ni tolerancia a la caída de un centro de datos."]
    (EVID / f"informe_{marca}.md").write_text("\n".join(lineas), encoding="utf-8")
    fallidas = [r for r in resultados if r["resultado"] != "APROBADA"]
    print(f"\nResumen: {len(resultados) - len(fallidas)}/{len(resultados)} aprobadas. Evidencias en {EVID}")
    return 1 if (fallidas or codigo_previo) else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sin-reinicio", action="store_true", help="No borra el volumen de datos al inicio")
    ap.add_argument("--limpiar", action="store_true", help="Apaga y borra los recursos de prueba al terminar")
    a = ap.parse_args()

    if ejecutar(["docker", "compose", "version"], check=False).returncode != 0:
        sys.exit("No se encontró 'docker compose'. Instale Docker Desktop y ábralo antes de continuar.")
    try:
        desplegar(desde_cero=not a.sin_reinicio)
        version = prueba_normal()
        prueba_caida_instancia()
        prueba_persistencia(version)
        prueba_respaldo_restauracion(version)
    except SystemExit:
        raise
    except Exception as exc:
        registrar("Ejecución", False, f"Error inesperado: {exc}")
    codigo = finalizar()
    if a.limpiar:
        compose("down", "-v", "--remove-orphans", check=False)
    sys.exit(codigo)


if __name__ == "__main__":
    main()
