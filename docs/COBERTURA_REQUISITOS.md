# Cobertura de los requisitos del reto

| Requisito del documento | Cómo lo cubre este repositorio | Dónde |
|---|---|---|
| Despliegue **reproducible** con contenedores | `docker compose up -d --build`; todo versionado en archivos | `docker-compose.yml`, `app/Dockerfile` |
| **Dos instancias** del servicio | `deploy.replicas: 2` (escalable con `REPLICAS`) | `docker-compose.yml` |
| **Punto de acceso común** / balanceo o proxy inverso | HAProxy en `:8080` | `haproxy/haproxy.cfg` |
| **Datos fuera** del sistema de archivos efímero | Volumen `datos` | `docker-compose.yml` |
| **Respaldo y restauración** definidos | `ops backup / restore`, SHA-256, retención | `scripts/ops.sh`, `docs/RUNBOOK_RECUPERACION.md` |
| Forma de **comprobar la salud** | `/health`, health checks de HAProxy y de Docker | `app/app.py`, `haproxy.cfg` |
| Consultar **registros** | Logs JSON + logs de acceso + panel `/stats` | `docker compose logs`, `:8404/stats` |
| Reconocer **qué instancia atendió** | `X-Instance` y campo `instancia` | `app/app.py` |
| Entregar archivos/instrucciones para **recrear** el despliegue | Este repo + README paso a paso | `README.md` |
| **Esquema de arquitectura** | Diagrama Mermaid + póster | `docs/ARQUITECTURA.md`, póster PDF |
| **Evidencias de pruebas** | Informe, JSON y registros automáticos | `scripts/pruebas.py`, `evidencias/` |
| Mecanismo simple de conmutación/recuperación y **explicar su alcance** | Reintento + health check activo; alcance en `LIMITACIONES.md` | `docs/LIMITACIONES.md` |
| Sin multirregión ni BD distribuida | No se incluyen (declarado) | `docs/LIMITACIONES.md` |
| **3 situaciones**: normal, caída de instancia, pérdida/modificación de datos | Pruebas 1, 2 y 4 (+3 recrear) | `scripts/pruebas.py` |
| Prueba **pequeña y repetible** | Un comando; ~2-4 min | `scripts/pruebas.py` |
| Consultar por el punto común e identificar instancias | Prueba 1 | `pruebas.py` |
| Detener una instancia y seguir consultando; **registrar errores** | Prueba 2a (cuenta errores y ventana de error) | `pruebas.py` |
| Actualizar/recrear contenedor y verificar datos | Prueba 3 | `pruebas.py` |
| Respaldar, alterar copia de trabajo, restaurar, **comparar versión y contenido** | Prueba 4 (versión + SHA-256) | `pruebas.py`, `ops.sh` |
| **Medir tiempo de recuperación**, documentar pasos, registros, limitaciones y mejoras | Prueba 4c + runbook + limitaciones | `pruebas.py`, `docs/` |
| **No declarar alta disponibilidad** por 2 contenedores en un PC | Declarado explícitamente | `README.md`, `LIMITACIONES.md` |
| Decisiones de **arquitectura, seguridad y costo** | Documentadas | `ARQUITECTURA.md`, `SEGURIDAD_Y_COSTOS.md` |
| Identificar **componentes, relaciones y factores de costo** sin comprar recursos | Tablas de equivalencia y factores | `NUBE_EQUIVALENTE.md` |
| Si no hay cuenta sin cobros: **demo local + diseño en nube**, limitación explícita | Es lo que se entrega | `README.md`, `NUBE_EQUIVALENTE.md` |
| **Sin secretos** en imagen ni repo | `.gitignore`, sin secretos requeridos | `.gitignore`, `SEGURIDAD_Y_COSTOS.md` |
| **Limitar exposición de red** | Puertos solo en `127.0.0.1` | `docker-compose.yml` |
| Pruebas de fallo sobre **copias controladas**; respaldo **fuera** de la copia modificada | `ops tamper` solo toca la copia de trabajo; respaldos en carpeta aparte | `ops.sh`, `docker-compose.yml` |
| **Explicar qué se probó y qué quedó como diseño** | Tabla específica | `docs/LIMITACIONES.md` |
| Datos **sintéticos** y entorno autorizado | Seis pedidos ficticios | `app/seed/pedidos.json` |
| Plan por encuentros (1 planear, 2 construir/probar, 3 mejorar/pitch) | Plan de 2 h + mejoras | `docs/PLAN_2_HORAS.md`, `LIMITACIONES.md` |
