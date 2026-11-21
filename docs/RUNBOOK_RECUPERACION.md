# Runbook de recuperación (paso a paso)

Úselo ante una falla. Cada paso indica **qué mirar** y **qué anotar** para la evidencia.

## A. Se cayó una instancia

1. Mire el panel <http://localhost:8404/stats>: la fila `app…` en rojo es la caída.
2. `docker compose ps -a` -> estado de los contenedores.
3. Registros de la instancia: `docker compose logs --tail 100 app` y del balanceador: `docker compose logs --tail 100 balanceador`.
4. Si solo se detuvo: `docker start <ID>` (o `docker compose up -d`). En ~5-10 s vuelve al panel en verde.
5. **Anote**: hora, instancia, errores vistos por el usuario, tiempo hasta recuperar.

> Si el proceso se cae por sí solo, Docker lo reinicia (`restart: unless-stopped`). Un `docker stop` manual **no** se reinicia solo, a propósito, para poder probar.

## B. Una actualización introdujo un error

1. Compruebe `http://localhost:8080/health` y los registros (`docker compose logs app`).
2. Vuelva a la versión anterior: `APP_VERSION=<anterior> docker compose up -d --build` (o `git checkout <commit-bueno>` y reconstruir).
3. Verifique `version_datos` y total de pedidos en `/pedidos`.

## C. Los datos se perdieron o fueron modificados

1. **Confirme el daño**: `curl.exe http://localhost:8080/pedidos` (versión/contenido inesperado) o `docker compose run --rm ops status` (versión y hash).
2. **No modifique el respaldo.** Liste los disponibles: `docker compose run --rm ops list`.
3. Restaure el más reciente: `docker compose run --rm ops restore`
   (o uno concreto: `docker compose run --rm ops restore pedidos_YYYYMMDDTHHMMSSZ.json`).
   El script **verifica la huella SHA-256 del respaldo antes** de usarlo y reemplaza el archivo de forma atómica.
4. **Verifique**: `/pedidos` debe mostrar la `version_datos` esperada y el total correcto; `ops status` debe dar el mismo `SHA256` que el respaldo.
5. **Anote**: hora de detección, hora de verificación (= tiempo de recuperación), respaldo usado, hash antes/después.

## D. Prueba controlada de pérdida de datos (para la demostración)

```bash
docker compose run --rm ops backup     # 1. respalda
docker compose run --rm ops tamper     # 2. altera SOLO la copia de trabajo
curl.exe http://localhost:8080/pedidos # 3. se ve "ALTERADO"
docker compose run --rm ops restore    # 4. restaura
curl.exe http://localhost:8080/pedidos # 5. versión original
```

## E. Qué NO cubre este procedimiento

Caída del computador anfitrión, del disco o del centro de datos: requiere respaldos fuera del equipo y réplicas en otra máquina/zona (ver `NUBE_EQUIVALENTE.md`).
