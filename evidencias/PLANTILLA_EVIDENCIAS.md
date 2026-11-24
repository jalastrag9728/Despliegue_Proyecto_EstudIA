# Registro del equipo

- **Equipo:** Nodo Ruta — EstudIA (Nube e Infraestructura, Capa 2, Nivel intermedio)
- **Integrantes y responsabilidades:**
  - Felipe Román — Comunicador + apoyo técnico/CI/CD y ejecución de I01–I06
  - Julián Andrés Lastra García — [Confirmar rol en reunión] (MVP base, Docker Compose, docs, póster)
  - Juan Manuel — [Confirmar rol en reunión] (Migración a Django + Gunicorn y pruebas unitarias)
  - Jerónimo Roldán — [Confirmar rol en reunión]
  - [Integrante 5 — Completar nombre y rol en reunión]
- **Fecha:** 2026-11-24
- **Modalidad:** Contenedores locales (Docker Desktop + Docker Compose en Windows) + diseño documentado en nube (AWS / Azure / GCP sin recursos pagos contratados).
- **Arquitectura elegida y motivo:** Dos instancias (`app1`, `app2`) con **Django + Gunicorn** (2 workers, usuario no-root, filesystem de solo lectura) detrás de **NGINX 1.28** como único punto de acceso (`127.0.0.1:8080`). Datos externos en `data/pedidos.json` (montaje `read_only`) y respaldos separados en `respaldos/` con verificación SHA-256. Permite demostrar continuidad ante caída de instancia, persistencia fuera del contenedor, observabilidad y recuperación medida a costo \$0.
- **Ayudas utilizadas y cambios realizados:** Base tomada del paquete `16.zip` (`app.py`, `pedidos.json`, `scripts/datos.py`, `scripts/verificar_servicio.py`, referencia NGINX). Mejoras propias: migración del servidor a Django + Gunicorn (`nodoruta_web/`), panel web operativo en `/panel`, enriquecimiento sintético de los 6 pedidos manteniendo `version: datos-v1`, pruebas automáticas (`scripts/pruebas_automaticas.py`), pruebas unitarias (`tests/`) y CI en GitHub Actions (`.github/workflows/ci.yml`).
- **Recursos, permisos y posibles costos:** Ejecución local a costo \$0, sin secretos en repositorio ni en imagen. En nube se requeriría IAM/RBAC de mínimo privilegio, HTTPS administrado en balanceador y vigilancia de costos por cómputo (vCPU/RAM × réplicas × horas), balanceador, almacenamiento/respaldos, logs y transferencia (detalle en `docs/NUBE_EQUIVALENTE.md` y `docs/SEGURIDAD_Y_COSTOS.md`).

---

# Fichas de prueba (I01–I06)

## Ficha I01 — Acceso común y reparto entre instancias

- **ID y nombre de la prueba:** I01 — Consultar por el acceso común y observar `app1` y `app2`
- **Qué queremos comprobar:** Que el proxy NGINX atiende en `http://127.0.0.1:8080/pedidos` y reparte consultas entre ambas instancias con `HTTP 200`.
- **Versión y estado inicial:** `version: datos-v1`, 6 pedidos sintéticos, `app1` y `app2` en estado `healthy`, `proxy` activo.
- **Pasos para repetirla:** Con `docker compose up -d --build` activo, enviar 10 solicitudes consecutivas `GET http://127.0.0.1:8080/pedidos` y registrar `status` e `instancia`.
- **Resultado esperado:** 10 respuestas `HTTP 200` alternando entre `app1` y `app2`.
- **Resultado observado:** 10/10 respuestas `HTTP 200`; reparto exacto `app1: 5` y `app2: 5`.
- **Inicio, fin y duración:** Inicio `16:22:45` · Fin `16:22:45` · Duración `0.42 s`.
- **Archivo, captura o enlace de evidencia:** `evidencias/local_2026-11-24/I01_inicio.json` y `evidencias/local_2026-11-24/proxy_logs.txt`
- **¿Cumple?** Sí
- **Error encontrado y ajuste:** Ninguno.
- **Resultado al repetir la prueba:** No requirió ajuste.

---

## Ficha I02 — Detener `app1` y continuidad por `app2`

- **ID y nombre de la prueba:** I02 — Detener `app1` y consultar por `app2`; registrar errores y tiempo
- **Qué queremos comprobar:** Que al detener `app1`, el proxy NGINX conmuta pasivamente hacia `app2` y el servicio sigue respondiendo.
- **Versión y estado inicial:** `version: datos-v1`, `app1` y `app2` `healthy`.
- **Pasos para repetirla:** Ejecutar `docker compose stop app1` y consultar continuamente `GET http://127.0.0.1:8080/pedidos` durante ~10 s registrando códigos HTTP e instancias.
- **Resultado esperado:** Las consultas siguen respondiendo `HTTP 200` desde `app2` (puede presentarse un error breve durante el cierre, que debe registrarse).
- **Resultado observado:** 17/17 consultas respondieron `HTTP 200` atendidas exclusivamente por `app2` (`app2: 17`), **0 errores** observados.
- **Inicio, fin y duración:** Inicio `16:22:45` · Fin `16:22:59` · Duración total `13.93 s`.
- **Archivo, captura o enlace de evidencia:** `evidencias/local_2026-11-24/I02_fallo_app1.json` y `evidencias/local_2026-11-24/proxy_logs.txt`
- **¿Cumple?** Sí
- **Error encontrado y ajuste:** Ninguno.
- **Resultado al repetir la prueba:** No requirió ajuste.

---

## Ficha I03 — Recuperación y reintegro de `app1`

- **ID y nombre de la prueba:** I03 — Recuperar `app1` y observar nuevamente ambas instancias
- **Qué queremos comprobar:** Que al volver a iniciar `app1`, NGINX la reintegra mediante DNS interno de Docker y vuelven a responder ambas instancias.
- **Versión y estado inicial:** `app1` detenida, `app2` atendiendo el 100% del tráfico.
- **Pasos para repetirla:** Ejecutar `docker compose start app1` y consultar `GET http://127.0.0.1:8080/pedidos` cada 0.5 s hasta observar `app1` y `app2` nuevamente.
- **Resultado esperado:** Reaparecen `app1` y `app2` en pocos segundos con `HTTP 200`.
- **Resultado observado:** Ambas instancias respondieron `HTTP 200` (`app2: 3`, `app1: 1`) tras el reintegro.
- **Inicio, fin y duración:** Inicio `16:22:59` · Fin `16:23:03` · **Tiempo de reintegro: `4.32 s`**.
- **Archivo, captura o enlace de evidencia:** `evidencias/local_2026-11-24/I03_recuperacion_app1.json`
- **¿Cumple?** Sí
- **Error encontrado y ajuste:** Ninguno.
- **Resultado al repetir la prueba:** No requirió ajuste.

---

## Ficha I04 — Recreación de instancia y persistencia externa

- **ID y nombre de la prueba:** I04 — Recrear una instancia y comprobar que conserva los datos externos
- **Qué queremos comprobar:** Que destruir y recrear el contenedor `app1` no altera ni pierde `data/pedidos.json` (almacenado fuera de la capa efímera).
- **Versión y estado inicial:** `version: datos-v1`, contenedor `app1` con ID `1717cbb42f0e`, SHA-256 `8db25d226f25...`.
- **Pasos para repetirla:** Registrar ID del contenedor `app1` y SHA-256 de `data/pedidos.json`; ejecutar `docker compose up -d --force-recreate app1`; verificar nuevo ID, SHA-256 y consultas a `/pedidos`.
- **Resultado esperado:** Contenedor nuevo (ID distinto), mismo SHA-256 y mismos 6 pedidos en `datos-v1`.
- **Resultado observado:** Contenedor recreado correctamente (`1717cbb42f0e` → `be7368054009`), SHA-256 idéntico (`8db25d226f25ca1f8e5628040208c98371a6bad368d9ec1cc22aa0012d925216`), 6/6 consultas `HTTP 200` con `datos-v1`. *(Nota: persistir no reemplaza respaldar).*
- **Inicio, fin y duración:** Inicio `16:23:03` · Fin `16:23:09` · Duración `5.33 s`.
- **Archivo, captura o enlace de evidencia:** `evidencias/local_2026-11-24/I04_recrear_app1.json`
- **¿Cumple?** Sí
- **Error encontrado y ajuste:** Ninguno.
- **Resultado al repetir la prueba:** No requirió ajuste.

---

## Ficha I05 — Respaldo, alteración (`503`) y restauración verificada

- **ID y nombre de la prueba:** I05 — Alterar la copia de datos, observar `503`, restaurar y comprobar contenido
- **Qué queremos comprobar:** Que una falla en el archivo compartido provoca `503` en ambas instancias (una segunda instancia no resuelve corrupción de datos) y que la restauración valida la huella SHA-256 y devuelve el servicio a `200`.
- **Versión y estado inicial:** `version: datos-v1`, 6 pedidos, respaldo creado en `respaldos/pedidos_20261124_162309.json` con SHA-256 `8db25d226f25ca1f8e5628040208c98371a6bad368d9ec1cc22aa0012d925216`.
- **Pasos para repetirla:** Crear respaldo con huella SHA-256 → corromper `data/pedidos.json` → consultar `/health` y `/pedidos` → verificar SHA-256 del respaldo y restaurar `data/pedidos.json` → consultar `/health` y `/pedidos` y medir tiempo de recuperación (RTO).
- **Resultado esperado:** `HTTP 503` en `/health` y `/pedidos` durante la corrupción; tras restaurar, `HTTP 200`, `version: datos-v1`, 6 pedidos y SHA-256 coincidente.
- **Resultado observado:** Durante la alteración: `/health` devolvió `503, 503` y `/pedidos` devolvió `503, 503`. Tras validar huella (`sha256_verified: true`) y restaurar: `/health` devolvió `200` (`app2`), `/pedidos` devolvió `200` (`app1`), `version: datos-v1`, `6 pedidos`, `restored_sha256_match: true`.
- **Inicio, fin y duración:** Inicio `16:23:09` · Fin `16:23:09` · **Tiempo de recuperación (RTO): `0.046 s`**.
- **Archivo, captura o enlace de evidencia:** `evidencias/local_2026-11-24/I05_respaldo_restauracion.json` y `respaldos/pedidos_20261124_162309.json`
- **¿Cumple?** Sí
- **Error encontrado y ajuste:** Ninguno.
- **Resultado al repetir la prueba:** No requirió ajuste.

---

## Ficha I06 — Reproducibilidad por otro integrante

- **ID y nombre de la prueba:** I06 — Repetir el despliegue con otro integrante usando las instrucciones del equipo
- **Qué queremos comprobar:** Que un integrante distinto a quienes construyeron el repositorio el sábado puede clonar, preparar datos y levantar el servicio siguiendo el `README.md`.
- **Versión y estado inicial:** Repositorio clonado en equipo Windows limpio de Felipe Román (sin `python` en `PATH`, con Docker Desktop instalado).
- **Pasos para repetirla:** Clonar el repo → encender Docker Desktop → crear `data/pedidos.json` desde `pedidos.json` → ejecutar `docker compose up -d --build` → verificar `/health`, `/pedidos`, `/panel` y ejecutar I01–I05.
- **Resultado esperado:** Despliegue funcional con `app1`, `app2` y `proxy` en estado `healthy` y pruebas pasando.
- **Resultado observado:** Despliegue reproducido con éxito en local; los 3 contenedores levantaron `healthy` y todas las pruebas I01–I05 pasaron.
- **Inicio, fin y duración:** 2026-11-24 · ~15:58 a 16:23 (incluyendo arranque de Docker Desktop y validación completa).
- **Archivo, captura o enlace de evidencia:** `evidencias/local_2026-11-24/` (evidencias I01–I05 generadas en el equipo del segundo integrante).
- **¿Cumple?** Sí
- **Error encontrado y ajuste:** (1) En Windows sin `python` en `PATH`, `python scripts/datos.py preparar` no corre directo, pero copiar `pedidos.json` a `data/pedidos.json` desbloquea el despliegue de inmediato. (2) Se detectaron y eliminaron archivos obsoletos de la v1 (`docker-compose.yml` roto con HAProxy, `scripts/ops.sh`, `scripts/pruebas.py`) y se alineó la documentación a Django + Gunicorn.
- **Resultado al repetir la prueba:** `docker compose up -d --build` y pruebas I01–I05 ejecutadas sin errores.

---

# Cierre

- **Qué funciona realmente:** Despliegue reproducible con Docker Compose (`app1` y `app2` en Django + Gunicorn detrás de NGINX 1.28), panel operativo en `/panel`, persistencia externa en `data/pedidos.json`, respaldo y restauración con verificación SHA-256, observabilidad por `/health` y logs de proxy (`upstream=`), y pruebas I01–I06 verificadas con tiempos reales.
- **Qué quedó como propuesta o pendiente:** Despliegue en nube real (AWS/Azure según disponibilidad de cuenta educativa sin cobros), alta disponibilidad multi-zona, almacenamiento/BD administrada, respaldos automáticos fuera del host, health checks activos con alertas y HTTPS administrado (documentado en `docs/NUBE_EQUIVALENTE.md`).
- **Procedimiento para recrear y recuperar:** Ver `README.md` (sección 3) y `docs/RUNBOOK_RECUPERACION.md`.
- **Limitaciones y cambios para el encuentro 3:** Dos contenedores en un mismo computador **no** prueban tolerancia al fallo del computador; el host, el proxy y `data/pedidos.json` siguen siendo puntos únicos de fallo locales. Prioridad siguiente: (1) separar datos y respaldos del host (EFS/RDS + S3), (2) réplicas en 2 zonas con balanceador y chequeo activo, (3) respaldos automáticos programados, (4) alertas y HTTPS.
