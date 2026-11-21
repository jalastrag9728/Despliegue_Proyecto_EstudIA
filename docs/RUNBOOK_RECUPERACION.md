# Runbook de recuperación

Cada paso indica qué mirar y qué anotar (use `evidencias/PLANTILLA_EVIDENCIAS.md`).

## A. Se cayó una instancia
1. `docker compose ps -a` → estado de `app1`/`app2`; `docker compose logs --tail 50`.
2. Consulte por el acceso común (`/pedidos`): debe seguir respondiendo la instancia viva. **Anote** cualquier error.
3. Recupere: `docker compose start app1` (o `docker compose up -d`). Repita consultas hasta ver ambas instancias.
4. **Anote** hora de detención, errores, y tiempo hasta ver otra vez `app1` y `app2`.

> Un `docker stop` manual no se reinicia solo (a propósito, para poder probar). Si el proceso se cae por sí solo, Docker lo reinicia.
> Una instancia *unhealthy* **no** se reinicia ni se retira automáticamente: revise sus registros y reiníciela (`docker compose restart app1`).

## B. Los datos se dañaron o se perdieron (I05)
1. **Confirme**: `/health` y `/pedidos` devuelven **503** en las dos instancias; `docker compose logs` lo muestra.
2. **No toque los respaldos.** Ubique el último: `ls respaldos/` (cada respaldo es un `.json` y su `.sha256`).
3. Restaure: `python scripts/datos.py restaurar --respaldo respaldos/ARCHIVO.json`
   (la huella se valida **antes** de escribir; si no coincide, se rechaza).
4. **Verifique**: `/health` → 200 con la versión esperada; `/pedidos` → registros esperados (6 en el conjunto original).
5. **Anote** inicio, fin y tiempo de recuperación, el respaldo elegido y la observación del 503 breve durante la escritura.

## C. Prueba controlada (para la demostración)
```bash
python scripts/datos.py respaldar        # anote la ruta que imprime
python scripts/datos.py simular-error    # solo altera data/pedidos.json
curl.exe http://127.0.0.1:8080/health    # 503
python scripts/datos.py restaurar --respaldo respaldos/ARCHIVO.json
curl.exe http://127.0.0.1:8080/pedidos   # versión y 6 pedidos
```

**Prueba de punto de recuperación (opcional de la guía):** cambie un estado de pedido y el campo `version` en `data/pedidos.json`, cree un nuevo
respaldo y luego recupere la copia **anterior**. Deje constancia de qué punto eligió y por qué, no solo de que el archivo abre.

## D. Qué NO cubre
Caída del computador o del disco: requiere respaldos fuera del equipo y réplicas en otra máquina/zona (`NUBE_EQUIVALENTE.md`).
