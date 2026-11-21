# Qué funciona, qué se verificó y qué quedó como diseño

## Mecanismos de la demostración local (se prueban con I01-I05)

| ID | Mecanismo | Evidencia |
|---|---|---|
| I01 | Reparto entre 2 instancias por el acceso común | `verificar_servicio.py` → `CUMPLE`, `app1` y `app2` |
| I02 | Conmutación al detener `app1` | consulta continua 15 s: errores y tiempo |
| I03 | Reintegro de `app1` | tiempo hasta ver ambas instancias |
| I04 | Datos fuera del contenedor (recrear `app1`) | misma versión y mismo SHA-256 de `data/pedidos.json` |
| I05 | Alteración → 503 → restauración | 503 en ambas instancias; versión, 6 pedidos y SHA-256 recuperados; tiempo medido |
| I06 | Repetir con otro integrante | **No realizado** hasta que alguien lo haga |

## Qué se verificó al construir este kit (y qué NO)

| Verificado | Cómo |
|---|---|
| `app.py`, `datos.py` | 7 pruebas locales (`tests/test_kit.py`): `/health`, `/pedidos`, ciclo respaldar → error → restaurar, rechazo de respaldo alterado y de rutas fuera de `respaldos/` |
| Orquestación de `pruebas_automaticas.py` | Ejecutada de punta a punta con un **simulador** de Docker (procesos locales y un proxy sencillo): lectura de resultados, tiempos y generación del informe |
| **NO verificado** | `docker compose` real, la imagen, **la configuración de NGINX** y el comportamiento real de reintentos y DNS. El entorno de construcción no tenía Docker ni NGINX |

> La primera corrida real de `python scripts/pruebas_automaticas.py` (en su equipo o en GitHub Actions) es la que valida el despliegue. Si algo
> necesita ajuste (versiones de imagen, rutas en Windows, tiempos de reintegro), quedará reflejado en el informe. **No marque pruebas como
> realizadas por haber leído estos archivos.**

## Diseño (no probado)

Despliegue en nube; alta disponibilidad entre zonas; replicación de datos; respaldo fuera del computador; HTTPS y permisos; alertas;
chequeo **activo** de salud; actualización gradual con reversión automática.

## Limitaciones a declarar en el pitch

1. Dos contenedores en un solo computador **no prueban tolerancia al fallo de ese computador**.
2. **Puntos únicos de fallo:** el computador, el proxy y el archivo `data/pedidos.json` compartido.
3. **Detección pasiva:** NGINX descubre una instancia caída al intentar usarla; Docker marca *unhealthy* pero no retira ni reinicia por sí solo.
4. Una segunda instancia **no** resuelve el fallo de datos compartidos (por eso I05 da 503 en ambas).
5. Persistir no es respaldar: recrear `app1` conserva datos, pero no protege de una alteración.
6. La restauración escribe sobre el archivo montado y puede producir un **503 breve** durante la operación.
7. El RPO es el tiempo desde el último respaldo (los respaldos son manuales).
8. Los tiempos son de **este** entorno y **esta** prueba; no son un compromiso de disponibilidad. No es una prueba de carga.

## Mejora propuesta para el encuentro 3

Priorizada: (1) separar los datos del computador (almacenamiento/BD administrada) y respaldos fuera del equipo; (2) réplicas en 2 zonas con
balanceador administrado y health checks activos; (3) respaldo automático con restauración probada periódicamente; (4) alertas; (5) HTTPS.
