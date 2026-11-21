# Nodo Ruta - Servicio de consulta de entregas, desplegado y recuperable (MVP)

> **Caso ficticio** de la hackatón EstudIA (Nube e infraestructura, Capa 2). Todos los datos son sintéticos.

Este repositorio levanta, **con un solo comando**, un servicio web que sigue respondiendo cuando una de sus copias se cae,
guarda sus datos fuera de la aplicación y sabe **respaldarse y restaurarse**. Está escrito para quien **no es experto en nube**:
no necesita cuenta en ningún proveedor ni pagar nada.

---

## 1. ¿Qué problema resuelve?

| Antes (caso Nodo Ruta) | Con este MVP |
|---|---|
| Una sola instancia: si cae, nadie consulta entregas | **Dos instancias** detrás de **un único punto de acceso** (balanceador) |
| Configuración manual | Todo descrito en archivos (`docker-compose.yml`): **reproducible** |
| Datos guardados dentro de la aplicación | Datos en un **volumen separado** (sobreviven a recrear contenedores) |
| Sin procedimiento de recuperación | **Respaldo -> alteración -> restauración** probado y con tiempo medido |
| No se sabe qué instancia respondió ni por qué falló | Cabecera `X-Instance`, **registros** en JSON y **panel de estado** |

## 2. Explicado sin tecnicismos

Piense en una tienda con dos cajas registradoras:

- **Instancias (contenedores)** = las cajas. Son idénticas; si una se apaga, la otra sigue cobrando.
- **Balanceador** = la persona de la puerta que dirige a cada cliente a una caja *libre* y deja de mandar gente a la caja dañada.
- **Volumen de datos** = la bodega: las cajas la consultan, pero la bodega no está *dentro* de ninguna caja. Si cambia una caja, la bodega sigue igual.
- **Respaldo** = una fotocopia de los documentos de la bodega guardada en **otro lugar** (la carpeta `respaldos/`).
- **Health check** = preguntar cada 2 segundos a cada caja "¿estás bien?" (`/health`).

```
 Usuario --> [ Balanceador :8080 ] --+--> [ app instancia A ] --+
                 (HAProxy)           |                         +--> [ Volumen "datos" ]   (solo lectura para las apps)
                                     +--> [ app instancia B ] --+
 [ ops: respaldo / restaurar ] --> escribe en "datos" y guarda copias en ./respaldos  (lugar separado)
```

Más detalle: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md). Glosario: [`docs/GLOSARIO.md`](docs/GLOSARIO.md).

## 3. Lo que necesita

1. **Docker Desktop** (Windows/Mac) o Docker Engine + Compose (Linux). Ábralo y espere a que diga "running".
2. **Git** (para clonar/subir el proyecto) y **Python 3.9+** (solo para el script de pruebas automáticas).

Verifique: `docker compose version` y `python --version`.

## 4. Puesta en marcha (5 minutos)

```bash
git clone <URL-de-su-repositorio>
cd nodoruta-mvp
docker compose up -d --build
```

Espere ~15 segundos y abra:

- Servicio: <http://localhost:8080> y <http://localhost:8080/pedidos>
- Salud: <http://localhost:8080/health>
- Panel de estado del balanceador (qué instancias están **UP/DOWN**): <http://localhost:8404/stats>

Pruebe varias veces `http://localhost:8080/pedidos` y mire el campo **`instancia`**: debe alternar entre dos valores.

> En Windows PowerShell use `curl.exe` (con `.exe`) en vez de `curl`.

## 5. Las pruebas del reto

### Opción A - todo automático (recomendada)

```bash
python scripts/pruebas.py
```

Ejecuta los escenarios, **mide tiempos** y guarda evidencias en `evidencias/` (informe, JSON y registros).
Con `--limpiar` apaga y borra todo al terminar. En GitHub, el mismo script corre solo en cada `push` (pestaña **Actions**).

### Opción B - a mano, paso a paso

| # | Escenario | Comandos | Qué debe ver |
|---|---|---|---|
| 1 | **Normal** | `curl.exe -i http://localhost:8080/pedidos` (repetir 5 veces) | `200`, cabecera `X-Instance` alternando entre 2 valores |
| 2 | **Cae una instancia** | `docker compose ps` -> copie un ID de `app` -> `docker stop <ID>` -> repita `curl.exe -i http://localhost:8080/pedidos` | Sigue respondiendo `200` con la instancia restante. En <http://localhost:8404/stats> la caída aparece en rojo |
| 2b | Vuelve la instancia | `docker start <ID>` | En ~5-10 s vuelve a atender |
| 3 | **Recrear contenedores** | `docker compose up -d --force-recreate app` | Contenedores nuevos, **misma** `version_datos` y 6 pedidos |
| 4 | **Respaldo -> alteración -> restauración** | `docker compose run --rm ops backup`<br>`docker compose run --rm ops tamper`<br>consulte `/pedidos` (verá `version_datos: ALTERADO`)<br>`docker compose run --rm ops restore` | Vuelve a `2026.11-v1` y el `SHA256` coincide con el del respaldo |

Registros (para el informe): `docker compose logs balanceador` y `docker compose logs app`.
Guía detallada de recuperación: [`docs/RUNBOOK_RECUPERACION.md`](docs/RUNBOOK_RECUPERACION.md).

## 6. Escalar (más instancias)

```bash
REPLICAS=4 docker compose up -d        # Linux/Mac
$env:REPLICAS=4; docker compose up -d  # Windows PowerShell
```

El balanceador descubre solas las nuevas instancias (hasta 6; se cambia en `haproxy/haproxy.cfg`). Para el salto a la nube vea
[`docs/NUBE_EQUIVALENTE.md`](docs/NUBE_EQUIVALENTE.md): cada pieza de este repo tiene su equivalente administrado.

**Respaldo automático opcional:** `docker compose --profile auto up -d respaldo-automatico` (cada 5 min; conserva los últimos 10).

## 7. Qué hay en cada carpeta

```
nodoruta-mvp/
├─ docker-compose.yml        <- el "plano": qué piezas existen y cómo se conectan
├─ app/                      <- el servicio (Python, sin dependencias) + Dockerfile + datos de semilla
├─ haproxy/haproxy.cfg       <- balanceador + comprobación de salud
├─ scripts/
│  ├─ ops.sh                 <- respaldar / alterar (prueba) / restaurar / verificar
│  └─ pruebas.py             <- pruebas automáticas + evidencias
├─ tests/                    <- pruebas unitarias de la app
├─ respaldos/                <- copias de seguridad (fuera de git)
├─ evidencias/               <- resultados de pruebas (fuera de git)
├─ docs/                     <- arquitectura, nube equivalente, seguridad, costos, plan de 2 h, runbook, límites
└─ .github/workflows/        <- CI automática (+ publicación opcional de imagen)
```

## 8. Seguridad en una mirada

- **Sin secretos** en imagen ni repositorio (`.gitignore` bloquea `.env`, llaves y certificados). El MVP no los necesita.
- Contenedores **sin privilegios**: usuario no-root, sistema de archivos de solo lectura, `cap_drop: ALL`, límites de CPU/memoria.
- Puertos publicados **solo en `127.0.0.1`**: nada queda expuesto a Internet.
- Datos en el volumen montados **solo lectura** para las apps; las pruebas de fallo se hacen sobre la **copia de trabajo** y el respaldo vive **aparte**.

Detalle: [`docs/SEGURIDAD_Y_COSTOS.md`](docs/SEGURIDAD_Y_COSTOS.md).

## 9. Subir a GitHub (paso a paso)

1. En github.com: **New repository** -> nombre `nodoruta-mvp` -> *sin* README/.gitignore (ya los trae) -> **Create**.
2. En la carpeta del proyecto:

```bash
git init
git add .
git commit -m "MVP Nodo Ruta: despliegue, balanceo, respaldo y restauración"
git branch -M main
git remote add origin https://github.com/<su-usuario>/nodoruta-mvp.git
git push -u origin main
```

3. Abra la pestaña **Actions**: verá la CI validar y ejecutar las pruebas. Descargue el artefacto `evidencias`.
4. *(Opcional)* Cree una etiqueta `v1.0.0` para publicar la imagen en el registro gratuito de GitHub.

## 10. Límites (léalos antes del pitch)

- **Dos contenedores en un mismo computador no son alta disponibilidad.** Esta demo prueba conmutación entre instancias y recuperación
  de datos; **no** demuestra tolerancia a la caída de una máquina o un centro de datos.
- Los datos viven en **un único volumen** (punto único de falla); lo mitiga el respaldo, no la replicación.
- La parte en nube está **documentada como diseño**, no desplegada (no se contrató nada).

Lista completa de lo **probado** vs lo **diseñado**: [`docs/LIMITACIONES.md`](docs/LIMITACIONES.md).
Cobertura de cada requisito del reto: [`docs/COBERTURA_REQUISITOS.md`](docs/COBERTURA_REQUISITOS.md).

## 11. Limpieza

```bash
docker compose down        # apaga, conserva datos
docker compose down -v     # apaga y borra el volumen de datos (los respaldos en ./respaldos se conservan)
```
