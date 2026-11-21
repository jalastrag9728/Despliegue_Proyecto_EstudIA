# Qué se probó y qué quedó como diseño

## Mecanismos PROBADOS (demostración local con contenedores)

| Mecanismo | Cómo se prueba | Evidencia |
|---|---|---|
| Despliegue reproducible con un comando | `docker compose up -d --build` | `pruebas.py` (prueba 0) |
| Reparto de solicitudes entre 2 instancias | 20 consultas, se cuentan instancias distintas | prueba 1 |
| Conmutación ante la detención de 1 instancia | `docker stop` + consulta continua 15 s; se registran errores y ventana de error | prueba 2a |
| Reintegro de la instancia | `docker start`; se mide el tiempo hasta que vuelve a atender | prueba 2b |
| Datos fuera del almacenamiento efímero | Recrear contenedores; misma versión y mismo hash de datos | prueba 3 |
| Respaldo, alteración y restauración | `ops backup / tamper / restore`; se compara versión y SHA-256 | prueba 4 |
| Tiempo de recuperación | Desde la detección de la alteración hasta datos correctos servidos | prueba 4c |

## Qué se verificó al construir este kit

- Pruebas unitarias de la app (6 pruebas) y cierre limpio ante `SIGTERM`.
- Script `ops.sh`: respaldo, alteración, restauración, rechazo de respaldo corrupto y retención.
- Sintaxis de `pruebas.py` y `docker-compose.yml`.
- **No se ejecutó Docker durante la construcción** (entorno sin Docker). La primera ejecución completa de `pruebas.py` debe hacerse en su equipo o en GitHub Actions;
  si algún ajuste menor es necesario (versiones de imagen, rutas en Windows), quedará reflejado en las evidencias.

## Lo que queda como DISEÑO (no probado)

- Despliegue en nube (ver `NUBE_EQUIVALENTE.md`).
- Alta disponibilidad real entre zonas; tolerancia a la caída de un centro de datos.
- Replicación de datos; respaldo en otra región/cuenta.
- TLS, autenticación, alertas automáticas, escaneo de vulnerabilidades en CI.
- Actualización gradual (*rolling update*) sin interrupción: hoy `--force-recreate` reemplaza las instancias casi a la vez y puede haber una pausa breve.

## Limitaciones a declarar en el pitch

1. **Dos contenedores en un mismo computador NO son alta disponibilidad.** Si el computador cae, cae todo.
2. El volumen `datos` es un **punto único de falla**; el respaldo reduce el daño pero no evita una pérdida entre respaldos (RPO = intervalo de respaldo).
3. El balanceador es **una sola pieza**; en nube sería un servicio administrado y redundante.
4. Las pruebas usan tráfico mínimo y datos sintéticos: no miden capacidad ni rendimiento.
5. Los tiempos medidos son de **este** entorno y **esta** prueba; no son un compromiso de disponibilidad.

## Mejoras propuestas para el encuentro 3

1. Despliegue en nube gratuita/educativa con 2+ réplicas en zonas distintas y balanceador administrado.
2. Respaldo automático a almacenamiento de objetos con versionado + prueba de restauración programada.
3. Alertas (salud, 5xx, respaldo fallido) y un tablero simple.
4. Actualización gradual con *rollback* automático por health check.
5. Escaneo de imagen y de dependencias en CI; fijar imágenes por *digest*.
