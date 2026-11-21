# Nodo Ruta - Servicio de consulta de entregas: desplegado, observable y recuperable (MVP)

> **Caso ficticio** de EstudIA (Nube e infraestructura, nivel intermedio). Todos los datos son sintéticos.

Este repositorio levanta un servicio web con **dos instancias** detrás de **un único punto de acceso**, con los datos **fuera del contenedor**
y con un procedimiento de **respaldo y restauración** probado. Está pensado para quien **no es experto en nube**: no necesita cuentas de
proveedor ni pagar nada. Se construye sobre el paquete del reto (`app.py`, `pedidos.json` y los scripts de `scripts/` **no se modificaron**).

---

## 1. Explicado sin tecnicismos

Una tienda con dos cajas registradoras:

| En la tienda | En el proyecto | Para qué sirve |
|---|---|---|
| Las dos cajas | `app1` y `app2` (contenedores) | Si una se apaga, la otra sigue atendiendo |
| El portero | `proxy` (NGINX) | Todos entran por él; reparte y, si una caja no contesta, prueba con la otra |
| La bodega de papeles | `data/pedidos.json` | Los datos viven **fuera** de las cajas: si se cambia una caja, los papeles siguen |
| Las fotocopias en otro cuarto | `respaldos/` con sello SHA-256 | Si los papeles se dañan, se restauran de la copia (se comprueba el sello antes) |
| El diario | `docker compose logs` | Quién atendió cada consulta y con qué resultado |

```
 Usted ──► [ proxy NGINX  127.0.0.1:8080 ] ──┬──► [ app1 ] ──┐
            (reintenta si una instancia no    └──► [ app2 ] ──┴──► data/pedidos.json  (solo lectura para las apps)
             responde; registra el upstream)
 python scripts/datos.py ──► escribe data/pedidos.json y guarda copias con huella en respaldos/
```

## 2. Lo que necesita

1. **Docker Desktop** (Windows/Mac) o Docker Engine + Compose (Linux). Ábralo y espere a que diga *running*.
2. **Python 3** (en Windows suele ser `py` en vez de `python`) y **Git**.

Compruebe: `docker version`, `docker compose version`, `python --version`.
*Tener Docker instalado no garantiza que esté iniciado.* Si solo puede usar Python, vea el [modo sin Docker](#7-si-no-puede-usar-docker).

## 3. Puesta en marcha (5 minutos)

```bash
git clone <URL-de-su-repositorio>
cd nodoruta-mvp
python scripts/datos.py preparar          # 1. crea data/pedidos.json (copia de trabajo)
docker compose up -d --build              # 2. construye y levanta (la 1.ª vez descarga imágenes)
docker compose ps                         # 3. espere a ver app1 y app2 en "healthy"
```

Abra <http://127.0.0.1:8080/health> y <http://127.0.0.1:8080/pedidos>. Refresque varias veces: el campo **`instancia`** alterna entre `app1` y `app2`.
Todo lo anterior queda reproducible desde `compose.yaml`, `Dockerfile` y `proxy/nginx.conf`.

> Windows PowerShell: use `curl.exe` (con `.exe`) y `py` si `python` no existe.

## 4. Las pruebas del reto (I01-I06)

### Opción A - automática (recomendada)

```bash
python scripts/pruebas_automaticas.py --reiniciar-datos
```

Ejecuta I01-I05, mide los tiempos y deja en `evidencias/auto_<fecha>/` el **informe con una ficha por prueba** (mismo formato de
`PLANTILLA_EVIDENCIAS.md`), los JSON de `verificar_servicio.py` y los registros. Añada `--limpiar` para apagar al final.
En GitHub, el mismo script corre en cada `push` (pestaña **Actions**).

### Opción B - a mano (cada ID con sus comandos)

| ID | Qué se comprueba | Comandos | Qué debe ver |
|---|---|---|---|
| I01 | Acceso común y las dos instancias | `python scripts/verificar_servicio.py --esperadas app1,app2 --salida evidencias/inicio.json` | `CUMPLE`, 200 en todas, `app1` y `app2` |
| I02 | Cae `app1` | `docker compose stop app1` y luego `python scripts/verificar_servicio.py --esperadas app2 --salida evidencias/fallo_app1.json` | Responde `app2`. Puede haber errores breves: **anótelos** y el tiempo |
| I03 | Vuelve `app1` | `docker compose start app1` y repetir la verificación con `--esperadas app1,app2 --salida evidencias/recuperacion.json` | Reaparecen ambas (puede tardar unos segundos) |
| I04 | Recrear una instancia | `docker compose up -d --force-recreate app1` | Contenedor nuevo, **misma** versión y contenido de datos (*recrear no es respaldar*) |
| I05 | Datos dañados | `python scripts/datos.py respaldar` → `python scripts/datos.py simular-error` → ver 503 en `/health` y `/pedidos` → `python scripts/datos.py restaurar --respaldo respaldos/ARCHIVO.json` | 503 con ambas instancias; tras restaurar, 200, `datos-v1` y 6 pedidos |
| I06 | Repetir con otro integrante | Otra persona sigue este README sin ayuda | Lo logra solo (**no se automatiza**) |

Registros: `docker compose logs --tail 50`. En el proxy verá `http=` (lo que recibió el usuario), `upstream=` (qué instancia atendió) y
`upstream_http=`. Guía de recuperación: [`docs/RUNBOOK_RECUPERACION.md`](docs/RUNBOOK_RECUPERACION.md).

## 5. Escalar

Agregar una instancia es copiar un bloque en `compose.yaml` y **una línea** en `proxy/nginx.conf`: [`docs/ESCALAR.md`](docs/ESCALAR.md).
El salto a la nube, pieza por pieza: [`docs/NUBE_EQUIVALENTE.md`](docs/NUBE_EQUIVALENTE.md).

## 6. Qué hay en cada carpeta

```
nodoruta-mvp/
├─ app.py  pedidos.json            <- ORIGINALES del reto (sin cambios)
├─ Dockerfile                      <- imagen de la app (usuario sin privilegios)
├─ compose.yaml                    <- el "plano": app1, app2 y proxy
├─ proxy/nginx.conf                <- reparto, reintentos, DNS dinámico y registro
├─ scripts/
│  ├─ datos.py  ejecutar_local.py  verificar_servicio.py   <- ORIGINALES del reto (sin cambios)
│  └─ pruebas_automaticas.py       <- I01-I05 + tiempos + informe (nuevo)
├─ tests/test_kit.py               <- pruebas locales sin Docker
├─ data/                           <- copia de trabajo (se crea con "preparar"; fuera de git)
├─ respaldos/   evidencias/        <- copias de seguridad y resultados (fuera de git)
├─ docs/                           <- arquitectura, explicación del despliegue, nube, seguridad, límites, runbook, plan
└─ .github/workflows/ci.yml        <- validación y pruebas automáticas
```

## 7. Si no puede usar Docker

Documente la **demostración parcial** (lo pide la guía): `python scripts/ejecutar_local.py --puerto 8080 --id local-1`, luego
`python scripts/verificar_servicio.py` y el ciclo `respaldar → simular-error → restaurar`. Esto prueba la app y los datos, **no** el despliegue en contenedores.

## 8. Seguridad en una mirada

- **Sin secretos** en imagen ni repositorio (`.gitignore` bloquea `.env`, llaves y certificados). El MVP no los necesita.
- Apps **sin privilegios**: no-root, sistema de archivos de solo lectura, `cap_drop: ALL`, límites de CPU/memoria.
- **Un solo puerto publicado**, solo en `127.0.0.1:8080`. Las apps solo se ven dentro de la red interna.
- Datos montados **solo lectura** para las apps; respaldo **separado** y con huella SHA-256 verificada antes de restaurar.

Detalle: [`docs/SEGURIDAD_Y_COSTOS.md`](docs/SEGURIDAD_Y_COSTOS.md).

## 9. Subir a GitHub

1. En github.com: **New repository** → `nodoruta-mvp` → *sin* README/.gitignore → **Create**.
2. En la carpeta del proyecto:

```bash
git init
git add .
git commit -m "MVP Nodo Ruta: dos instancias, proxy, respaldo y restauración"
git branch -M main
git remote add origin https://github.com/<su-usuario>/nodoruta-mvp.git
git push -u origin main
```

3. Pestaña **Actions**: verá la validación y las pruebas. Descargue el artefacto `evidencias`.

## 10. Límites (léalos antes del pitch)

- **Dos contenedores en un mismo computador no prueban tolerancia al fallo de ese computador.** El computador, el proxy y el archivo de datos
  compartido son **puntos únicos de fallo**.
- El proxy hace **detección pasiva** (se entera cuando una consulta falla); no es un monitor activo de `/health`. Docker puede mostrar una
  instancia *unhealthy* **sin** reiniciarla ni retirarla por sí solo.
- Una segunda instancia **no** resuelve un fallo de datos compartido (por eso I05 da 503 en ambas).
- La parte en nube es **diseño**, no se contrató nada. Lista de lo probado vs. diseñado: [`docs/LIMITACIONES.md`](docs/LIMITACIONES.md).

## 11. Limpieza

```bash
docker compose down        # retira los contenedores; data/, respaldos/ y evidencias/ permanecen
```
No use comandos de limpieza global de Docker ni borre recursos ajenos al ejercicio.

## 12. Problemas frecuentes

| Síntoma | Qué hacer |
|---|---|
| No conecta con el motor | Inicie Docker Desktop (o el motor autorizado) y repita `docker version` |
| Puerto 8080 ocupado | Detenga `ejecutar_local.py` o ponga `PUBLIC_PORT=8081` en un archivo `.env` y use esa URL |
| "bind source path does not exist" | Falta `python scripts/datos.py preparar` |
| `/health` devuelve 503 | `data/pedidos.json` no es JSON válido o falta: restaure desde un respaldo |
| Solo aparece una instancia | `docker compose ps`, `docker compose logs`, y repita más consultas |
| "La salida ya existe" al verificar | Use otro nombre en `--salida` (no sobrescribe evidencia) |
| La imagen no descarga | Revise conexión/acceso a Docker Hub y los registros; no marque la prueba como realizada |
