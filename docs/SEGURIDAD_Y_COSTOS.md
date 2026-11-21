# Seguridad y costos

| Riesgo | Medida aplicada | Dónde verificar |
|---|---|---|
| Secretos filtrados | El MVP **no usa secretos**; `.gitignore` bloquea `.env`, `*.pem`, `*.key`, `secrets/` | `.gitignore`, `.env.example` |
| Contenedor comprometido escala privilegios | Usuario no-root, `read_only`, `cap_drop: ALL`, `no-new-privileges` en las apps; `no-new-privileges` en el proxy | `Dockerfile`, `compose.yaml` |
| Exposición de red | Un solo puerto publicado, solo en `127.0.0.1`; las apps solo en la red interna | `compose.yaml` |
| App dañando los datos | Montaje de datos **solo lectura** para las apps | `compose.yaml` |
| Respaldo corrupto o manipulado | SHA-256 por respaldo, verificado **antes** de restaurar; solo se restaura desde `respaldos/` | `scripts/datos.py` (probado en `tests/`) |
| Pérdida del respaldo junto con los datos | Respaldo en carpeta separada de la copia de trabajo (frente a la falla del computador completo seguiría habiendo un punto único de fallo) | `respaldos/` |
| Fallos probados sobre datos reales | La alteración solo toca `data/pedidos.json`; el original y los respaldos quedan intactos | `datos.py simular-error` |
| Datos sensibles | Solo datos **sintéticos** (6 pedidos) | `pedidos.json` |
| Sin HTTPS ni autenticación | Fuera del alcance de la demo local. *Mejora:* HTTPS en el balanceador administrado e identidad corporativa | - |
| Imagen con vulnerabilidades | Base oficial sin dependencias extra. *Mejora:* escaneo en CI y fijar versiones por *digest* | `Dockerfile` |
| Servidor HTTP de laboratorio | `http.server` de Python **no es para producción** (indicado en la guía) | `app.py` |

> Excepción consciente: el proxy NGINX no usa `read_only` ni `cap_drop: ALL` porque su imagen oficial necesita iniciar con privilegios mínimos
> para abrir su puerto y escribir temporales; se priorizó que arranque de forma fiable.

## Costos

- **Ejecución local: cero** (herramientas gratuitas; Docker Desktop puede tener condiciones de licencia en empresas grandes, revise las suyas).
- Controles incluidos: límites de CPU/memoria (`mem_limit`, `cpus`), rotación de logs (10 MB × 3).
- Costos en nube: factores en [`NUBE_EQUIVALENTE.md`](NUBE_EQUIVALENTE.md). No se inventan precios.
