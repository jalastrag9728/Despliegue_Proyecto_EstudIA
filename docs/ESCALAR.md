# Cómo agregar una tercera instancia

1. En `compose.yaml`, copie el bloque `app2` completo y renómbrelo `app3` (cambie también `INSTANCE_ID: app3`).
2. En `compose.yaml`, en `proxy` → `depends_on`, agregue `app3` con `condition: service_healthy`.
3. En `proxy/nginx.conf`, dentro de `upstream nodoruta`, agregue:
   `server app3:8080 resolve max_fails=1 fail_timeout=5s;`
4. `docker compose up -d --build` y verifique con `python scripts/verificar_servicio.py --esperadas app1,app2,app3 --salida evidencias/escala.json`.

Más allá de unas pocas instancias en un solo computador, el siguiente paso es un servicio administrado de contenedores con balanceador
(ver [`NUBE_EQUIVALENTE.md`](NUBE_EQUIVALENTE.md)); en ese punto, `app3`, `app4`… se convierten en un parámetro de "número de réplicas".
