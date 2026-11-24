# Cobertura de los requisitos del reto y de la guía

| Requisito | Cómo se cubre | Dónde |
|---|---|---|
| Despliegue **reproducible** con contenedores | `docker compose up -d --build` | `compose.yaml`, `Dockerfile` |
| **Dos instancias** | `app1`, `app2` | `compose.yaml` |
| **Acceso común** / proxy o balanceo | NGINX | `proxy/nginx.conf` |
| Datos **fuera** del almacenamiento efímero | Montaje de `data/pedidos.json` | `compose.yaml` |
| **Respaldo y restauración** | `datos.py respaldar/restaurar` con SHA-256 | `scripts/datos.py`, runbook |
| Comprobar **salud** | `/health` + healthcheck de Docker | `nodoruta_web/views.py`, `compose.yaml` |
| Consultar **registros** | `docker compose logs` (proxy con `upstream=`) | `nginx.conf` |
| Saber **qué instancia atendió** | Campo `instancia` y `upstream=` | `nodoruta_web/views.py`, `nginx.conf` |
| Archivos/instrucciones para **recrear** | README paso a paso | `README.md` |
| **Esquema de arquitectura** | Diagrama + póster | `docs/ARQUITECTURA.md`, póster |
| **Puntos únicos de fallo** y mejora | Computador, proxy, archivo; mejora priorizada | `docs/LIMITACIONES.md` |
| I01 Acceso común, app1 y app2 | `verificar_servicio.py --esperadas app1,app2` | `pruebas_automaticas.py` |
| I02 Detener app1, registrar errores y tiempo | Consulta continua + evidencia | ídem |
| I03 Recuperar app1 | Tiempo de reintegro | ídem |
| I04 Recrear instancia, conservar datos | Comparación de contenedor, versión y SHA-256 | ídem |
| I05 Alterar → 503 → restaurar → comprobar | `datos.py` + tiempo de recuperación | ídem |
| I06 Repetir con otro integrante | Reproducido y documentado en bitácora | `evidencias/PLANTILLA_EVIDENCIAS.md` |
| Explicar **qué mecanismo detecta cada fallo** y qué lo recupera | Tabla específica | `docs/EXPLICACION_DEL_DESPLIEGUE.md` |
| Explicar Dockerfile, Compose, proxy, datos, `/health`, un puerto | Seis respuestas | ídem |
| **Persistir ≠ respaldar** | Declarado | `LIMITACIONES.md`, glosario |
| 2 contenedores en un PC **no** prueban tolerancia al fallo del PC | Declarado | `README.md`, `LIMITACIONES.md` |
| Arquitectura, **permisos, HTTPS y costos** en nube sin precios | Equivalencias y factores | `docs/NUBE_EQUIVALENTE.md` |
| Si no hay cuenta habilitada: demo local + diseño pendiente | Es lo que se entrega | `README.md`, `NUBE_EQUIVALENTE.md` |
| Sin secretos; limitar exposición | `.gitignore`; solo `127.0.0.1:8080` | `SEGURIDAD_Y_COSTOS.md` |
| Fallos sobre copias controladas | Solo se altera `data/pedidos.json` | `datos.py` |
| **Qué se probó y qué quedó como diseño** | Tabla específica | `docs/LIMITACIONES.md` |
| Datos **sintéticos** | 6 pedidos ficticios | `pedidos.json` |
| Bitácora/plantilla de evidencias | Informe automático con fichas y plantilla | `evidencias/` |
