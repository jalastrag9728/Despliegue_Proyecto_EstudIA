#!/usr/bin/env python3
"""Pruebas I01-I05 de Nodo Ruta con medicion de tiempos y evidencia (requiere Docker).

Usa SOLO los scripts del reto (datos.py y verificar_servicio.py) mas docker compose, y deja en
evidencias/auto_<fecha>/ : informe.md (fichas de prueba), resultado.json, los JSON de verificar_servicio y registros.log.

  python scripts/pruebas_automaticas.py                  # prueba completa
  python scripts/pruebas_automaticas.py --reiniciar-datos  # recrea data/pedidos.json desde pedidos.json
  python scripts/pruebas_automaticas.py --limpiar        # al final ejecuta "docker compose down"

I06 (repetir con otro integrante) NO es automatizable: queda marcada "No realizado".
Una demostracion local NO prueba tolerancia al fallo del computador. Ver docs/LIMITACIONES.md.
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
ORIGINAL = RAIZ / "pedidos.json"
TRABAJO = RAIZ / "data" / "pedidos.json"
PUERTO = "8080"
URL = f"http://127.0.0.1:{PUERTO}"
MARCA = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
EVID = RAIZ / "evidencias" / f"auto_{MARCA}"
VERSION_ESPERADA = "datos-v1"
fichas = []


# ------------------------------------------------------------------ utilidades
def run(cmd, check=True):
    p = subprocess.run(cmd, cwd=RAIZ, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"Fallo: {' '.join(map(str, cmd))}\n{p.stdout}\n{p.stderr}")
    return p


def compose(*args, check=True):
    return run(["docker", "compose", *args], check=check)


def py(script, *args, check=True):
    return run([sys.executable, str(SCRIPTS / script), *args], check=check)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ahora():
    return dt.datetime.now().strftime("%H:%M:%S")


def get(ruta, timeout=3.0):
    """(http|None, cuerpo_json|None) consultando por el acceso comun."""
    try:
        with urllib.request.urlopen(URL + ruta, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except ValueError:
            return e.code, None
    except Exception:
        return None, None


def esperar(cond, timeout, paso=0.3):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        v = cond()
        if v:
            return v, time.monotonic() - t0
        time.sleep(paso)
    return None, time.monotonic() - t0


def instancias_vistas(n=10):
    vistas = set()
    for _ in range(n):
        st, d = get("/health")
        if st == 200 and d:
            vistas.add(d.get("instancia"))
    return vistas


def verificar(nombre, esperadas, peticiones=10):
    """Ejecuta verificar_servicio.py guardando evidencia con nombre unico. Devuelve (ok, resumen, ruta)."""
    salida = EVID / f"{nombre}.json"
    p = py("verificar_servicio.py", f"{URL}/pedidos", "--peticiones", str(peticiones),
           "--esperadas", esperadas, "--salida", str(salida), check=False)
    resumen = {}
    if salida.exists():
        d = json.loads(salida.read_text(encoding="utf-8"))
        resumen = {"resultado": d["resultado"], "instancias_observadas": d["instancias_observadas"],
                   "http": sorted({str(c.get("http")) for c in d["consultas"]})}
    return p.returncode == 0, resumen, salida.relative_to(RAIZ).as_posix()


def ficha(id_, objetivo, estado_inicial, pasos, esperado, observado, inicio, fin, duracion, evidencia, estado, error="", repetir=""):
    f = dict(id=id_, objetivo=objetivo, estado_inicial=estado_inicial, pasos=pasos, esperado=esperado,
             observado=observado, inicio=inicio, fin=fin, duracion_s=duracion, evidencia=evidencia,
             estado=estado, error_y_ajuste=error or "Ninguno", resultado_al_repetir=repetir or "No aplica")
    fichas.append(f)
    print(f"[{estado.upper():10}] {id_} - {objetivo}: {observado}")
    return f


# ------------------------------------------------------------------ preparacion
def preparar(reiniciar):
    if reiniciar and TRABAJO.exists():
        TRABAJO.unlink()
    if not TRABAJO.exists():
        print(py("datos.py", "preparar").stdout.strip())
    elif sha(TRABAJO) != sha(ORIGINAL):
        sys.exit("data/pedidos.json existe y difiere del original. Use --reiniciar-datos para empezar limpio.")
    print(">> Construyendo y levantando (la primera vez descarga imagenes)...")
    compose("up", "-d", "--build", "--force-recreate")
    ok, t = esperar(lambda: len(instancias_vistas(8)) >= 2, 120, paso=1.0)
    if not ok:
        compose("ps", check=False)
        sys.exit("No aparecieron app1 y app2 por el acceso comun en 120 s. Revise: docker compose logs")
    print(f">> Servicio listo en {t:.1f} s")
    return t


# ------------------------------------------------------------------ pruebas
def i01():
    inicio = ahora()
    ok, r, ev = verificar("I01_inicio", "app1,app2")
    ficha("I01", "Consultar por el acceso comun y observar app1 y app2",
          f"Version {VERSION_ESPERADA}, 2 instancias levantadas",
          "verificar_servicio.py --esperadas app1,app2 (10 consultas)", "10 respuestas HTTP 200; aparecen app1 y app2",
          json.dumps(r, ensure_ascii=False), inicio, ahora(), "", ev, "Cumple" if ok else "No cumple")
    return ok


def i02():
    inicio = ahora()
    t_stop = time.monotonic()
    compose("stop", "app1")
    dur_stop = time.monotonic() - t_stop
    # consulta continua 15 s para registrar errores sin ocultarlos
    t0 = time.monotonic()
    muestras = []
    primera_app2 = None
    while time.monotonic() - t0 < 15:
        ts = time.monotonic() - t0
        st, d = get("/pedidos")
        inst = d.get("instancia") if d else None
        muestras.append((round(ts, 2), st, inst))
        if st == 200 and inst == "app2" and primera_app2 is None:
            primera_app2 = time.monotonic() - t_stop
        time.sleep(0.1)
    errores = [m for m in muestras if m[1] != 200]
    atendieron = sorted({m[2] for m in muestras if m[1] == 200 and m[2]})
    ok_v, r, ev = verificar("I02_fallo_app1", "app2")
    ok = ok_v and atendieron == ["app2"] and len(errores) <= max(1, int(0.05 * len(muestras)))
    obs = (f"Tras detener app1 respondio solo {atendieron}; {len(muestras)} consultas, {len(errores)} con error "
           f"{[m[:2] for m in errores][:5]}; primera respuesta de app2 {primera_app2 and round(primera_app2, 2)} s "
           f"despues de iniciar el stop (el stop tardo {dur_stop:.1f} s)")
    ficha("I02", "Detener app1 y consultar por app2; registrar errores y tiempo",
          "app1 y app2 sanas", "docker compose stop app1; consulta continua 15 s; verificar_servicio.py --esperadas app2",
          "Responde app2. Pueden verse errores breves: se registran, no se ocultan", obs, inicio, ahora(),
          round(primera_app2 or 0, 2), ev, "Cumple" if ok else ("Parcial" if atendieron else "No cumple"))
    return ok


def i03():
    inicio = ahora()
    t0 = time.monotonic()
    compose("start", "app1")
    visto, t = esperar(lambda: {"app1", "app2"} <= instancias_vistas(6), 120, paso=1.0)
    ok_v, r, ev = verificar("I03_recuperacion_app1", "app1,app2")
    ok = bool(visto) and ok_v
    ficha("I03", "Recuperar app1 y observar nuevamente ambas instancias",
          "app1 detenida, app2 sirviendo", "docker compose start app1; consultar hasta ver app1 y app2",
          "Vuelven a aparecer app1 y app2",
          f"{'Ambas instancias visibles' if visto else 'app1 no reaparecio en 120 s'}; reintegro en {t:.1f} s; {json.dumps(r, ensure_ascii=False)}",
          inicio, ahora(), round(time.monotonic() - t0, 1), ev, "Cumple" if ok else "No cumple")
    return ok


def i04():
    inicio = ahora()
    antes = sha(TRABAJO)
    id_antes = compose("ps", "-q", "app1").stdout.strip()
    t0 = time.monotonic()
    compose("up", "-d", "--force-recreate", "app1")
    visto, t = esperar(lambda: {"app1", "app2"} <= instancias_vistas(6), 120, paso=1.0)
    id_desp = compose("ps", "-q", "app1").stdout.strip()
    st, d = get("/health")
    despues = sha(TRABAJO)
    ok_v, r, ev = verificar("I04_recreacion_app1", "app1,app2")
    ok = bool(visto) and id_antes != id_desp and antes == despues and ok_v and d and d.get("version_datos") == VERSION_ESPERADA
    ficha("I04", "Recrear una instancia y comprobar que conserva los datos externos",
          f"Version {VERSION_ESPERADA}; sha256 {antes[:12]}...",
          "docker compose up -d --force-recreate app1; comparar contenedor, version y sha256 de data/pedidos.json",
          "Contenedor nuevo; misma version y mismo contenido",
          f"Contenedor {'nuevo' if id_antes != id_desp else 'IGUAL'}; version {d and d.get('version_datos')}; "
          f"sha256 {'identico' if antes == despues else 'DIFERENTE'}; app1 de vuelta en {t:.1f} s",
          inicio, ahora(), round(time.monotonic() - t0, 1), ev, "Cumple" if ok else "No cumple",
          error="Nota: recrear NO es respaldo; persistir y respaldar son cosas distintas.")
    return ok


def i05():
    inicio = ahora()
    hash_ok = sha(TRABAJO)
    out = py("datos.py", "respaldar").stdout
    ruta = out.split("Respaldo creado:")[1].strip().replace("\\", "/")
    py("datos.py", "simular-error")
    # observar el 503 a traves del acceso comun
    cod503, _ = esperar(lambda: get("/health")[0] == 503, 15, paso=0.2)
    st_p, _ = get("/pedidos")
    t_det = time.monotonic()
    t_det_h = ahora()
    py("datos.py", "restaurar", "--respaldo", ruta)

    def recuperado():
        st, d = get("/health")
        if st != 200 or not d or d.get("version_datos") != VERSION_ESPERADA:
            return None
        st2, p = get("/pedidos")
        return p if st2 == 200 and p and len(p.get("pedidos", [])) == 6 else None

    rec, _ = esperar(recuperado, 30, paso=0.2)
    rto = time.monotonic() - t_det
    iguales = sha(TRABAJO) == hash_ok
    ok_v, r, ev = verificar("I05_restauracion", "app1,app2")
    ok = bool(cod503) and st_p == 503 and bool(rec) and iguales and ok_v
    ficha("I05", "Alterar la copia de datos, observar 503, restaurar y comprobar contenido",
          f"Version {VERSION_ESPERADA}, 6 pedidos, sha256 {hash_ok[:12]}...",
          f"datos.py respaldar ({ruta}); datos.py simular-error; consultar /health y /pedidos; datos.py restaurar --respaldo {ruta}",
          "503 mientras la copia es invalida (ambas instancias); tras restaurar 200, version y 6 pedidos correctos",
          f"/health 503 {'observado' if cod503 else 'NO observado'}; /pedidos {st_p}; recuperado={bool(rec)}; "
          f"contenido {'identico al original' if iguales else 'DIFERENTE'}; tiempo de recuperacion {rto:.1f} s "
          f"medido desde la deteccion del 503 ({t_det_h}) hasta 200 con datos correctos",
          inicio, ahora(), round(rto, 2), f"{ev}; {ruta}", "Cumple" if ok else "No cumple",
          error="La restauracion escribe sobre el archivo montado y puede producir un 503 breve durante la operacion.")
    return ok


def i06():
    ficha("I06", "Repetir el despliegue o la recuperacion con otro integrante y las instrucciones del equipo",
          "-", "Otro integrante sigue el README sin ayuda", "Logra levantar y recuperar solo con el README",
          "No automatizable: requiere a otra persona", "-", "-", "", "-", "No realizado")


# ------------------------------------------------------------------ informe
def escribir_informe(t_listo):
    EVID.mkdir(parents=True, exist_ok=True)
    (EVID / "resultado.json").write_text(json.dumps({"segundos_hasta_listo": round(t_listo, 1), "fichas": fichas},
                                                   ensure_ascii=False, indent=2), encoding="utf-8")
    logs = compose("logs", "--no-color", "--tail", "200", check=False).stdout
    (EVID / "registros.log").write_text(logs, encoding="utf-8")
    L = [f"# Evidencias automaticas - {MARCA}", "",
         f"Servicio listo en {t_listo:.1f} s desde `docker compose up`.", "",
         "| ID | Prueba | Estado | Duracion (s) | Observado |", "|---|---|---|---|---|"]
    for f in fichas:
        L.append(f"| {f['id']} | {f['objetivo']} | **{f['estado']}** | {f['duracion_s'] or '-'} | {str(f['observado']).replace('|', '/')} |")
    L += ["", "---", ""]
    for f in fichas:
        L += [f"## {f['id']} - {f['objetivo']}", "",
              f"- Estado inicial: {f['estado_inicial']}", f"- Pasos para repetir: {f['pasos']}",
              f"- Resultado esperado: {f['esperado']}", f"- Resultado observado: {f['observado']}",
              f"- Inicio / fin: {f['inicio']} / {f['fin']}  (duracion: {f['duracion_s'] or '-'} s)",
              f"- Evidencia: {f['evidencia']}", f"- Cumple: {f['estado']}",
              f"- Error encontrado y ajuste: {f['error_y_ajuste']}",
              f"- Resultado al repetir: {f['resultado_al_repetir']}", ""]
    L += ["> Prueba local con contenedores en un solo computador: NO demuestra tolerancia al fallo de ese computador "
          "ni alta disponibilidad de produccion. El computador, el proxy y el archivo de datos son puntos unicos de fallo.",
          f"> Registros consultados: `registros.log` (proxy y aplicaciones)."]
    (EVID / "informe.md").write_text("\n".join(L), encoding="utf-8")
    print(f"\nEvidencias en {EVID.relative_to(RAIZ)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reiniciar-datos", action="store_true", help="Recrea data/pedidos.json desde pedidos.json")
    ap.add_argument("--limpiar", action="store_true", help="Ejecuta 'docker compose down' al terminar")
    a = ap.parse_args()
    if run(["docker", "compose", "version"], check=False).returncode != 0:
        sys.exit("No se encontro 'docker compose'. Inicie Docker Desktop y vuelva a intentar. "
                 "Si solo puede usar Python, documente la demostracion parcial (ver README).")
    EVID.mkdir(parents=True, exist_ok=True)
    t_listo = 0.0
    try:
        t_listo = preparar(a.reiniciar_datos)
        for prueba in (i01, i02, i03, i04, i05):
            prueba()
        i06()
    except SystemExit:
        raise
    except Exception as exc:
        print("ERROR inesperado:", exc)
        ficha("EJEC", "Ejecucion del script", "-", "-", "-", f"Error inesperado: {exc}", "-", ahora(), "", "-", "No cumple")
    escribir_informe(t_listo)
    if a.limpiar:
        compose("down", check=False)
    malas = [f for f in fichas if f["estado"] not in ("Cumple", "No realizado")]
    sys.exit(1 if malas else 0)


if __name__ == "__main__":
    main()
