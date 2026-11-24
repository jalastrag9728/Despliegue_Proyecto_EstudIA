# Explicación del despliegue (lo que el equipo debe saber defender)

## Las seis preguntas de la guía

| Pregunta | Respuesta |
|---|---|
| **¿Qué construye el Dockerfile?** | La imagen `nodo-ruta-app`: Python 3.12 slim + **Django + Gunicorn** (`nodoruta_web/`, 2 workers), corre como usuario sin privilegios (UID 10001) y escucha en el puerto 8080 **del contenedor**. No contiene los datos ni secretos. |
| **¿Qué conecta Compose?** | Crea una red interna con `app1`, `app2` y `proxy`; monta `data/pedidos.json` (solo lectura) en las apps; define el healthcheck y el orden de arranque (`proxy` espera a que ambas apps estén *healthy*). |
| **¿Para qué sirve el proxy?** | Es el único punto de entrada. Reparte por turnos, reintenta en la otra instancia ante errores de conexión o demora, y registra qué *upstream* atendió. |
| **¿Dónde se leen los datos?** | En **cada consulta**, de `/data/pedidos.json` dentro del contenedor, que es el archivo `data/pedidos.json` del computador montado en solo lectura. Por eso una alteración o una restauración se ven al instante, sin reiniciar. |
| **¿Qué comprueba `/health`?** | Que el archivo exista y sea un JSON con la lista `pedidos`. Devuelve 200 con `instancia` y `version_datos`, o **503** si no puede leer datos válidos. No comprueba lo que contiene cada pedido. |
| **¿Por qué solo se publica un puerto?** | Menos superficie expuesta: solo el proxy es accesible, y solo desde este computador (`127.0.0.1:8080`). Las apps no se publican; se ven únicamente dentro de la red interna. |

## ¿Qué mecanismo detecta cada fallo y qué lo recupera?

| Fallo | Quién lo detecta | Qué ve el usuario | Qué lo recupera |
|---|---|---|---|
| Se detiene `app1` (`docker compose stop app1`) | **NGINX, de forma pasiva**: la conexión falla y reintenta con `app2`; luego deja de enviarle consultas (`max_fails`/`fail_timeout`) y el DNS ya no resuelve `app1` | Normalmente nada; puede haber un error breve (se registra, no se oculta) | `docker compose start app1`; NGINX la reintegra al volver a resolver su nombre |
| El proceso de una app se cae solo | Docker (`restart: unless-stopped`) + NGINX (pasivo) | Normalmente nada | Docker reinicia el contenedor |
| Una app responde pero su healthcheck falla | **Docker** la marca *unhealthy* | Sigue recibiendo tráfico: Docker **no** la retira ni la reinicia por sí solo | Acción manual (revisar registros, reiniciar). *Mejora:* chequeo activo o un orquestador |
| `data/pedidos.json` inválido | Cada app en su `/health` (503) | **503 en todo**: la segunda instancia no ayuda, el dato es compartido | `python scripts/datos.py restaurar --respaldo ...` |
| Se cae el computador / el proxy / el archivo compartido | Nadie | Todo el servicio cae | Fuera del alcance local: ver `NUBE_EQUIVALENTE.md` |

**Por qué el proxy no reintenta ante 503** (`proxy_next_upstream error timeout`): un 503 de `/health` significa "datos dañados" y afecta a *todas* las
instancias. Reintentarlo no sirve, ocultaría el problema y dejaría a ambas instancias marcadas como caídas incluso después de restaurar.

## Decisiones y alternativas

| Decisión | Motivo | Alternativa |
|---|---|---|
| NGINX 1.28 con `resolve` (DNS de Docker) | Es la referencia del reto; arranca sin que existan las dos instancias y las reintegra | HAProxy: tiene chequeo **activo** de salud (mejor), pero añade otra herramienta |
| Compose con `app1`/`app2` explícitas | Los IDs coinciden con las pruebas I01-I05 y el código es fácil de leer | `replicas`: más compacto, pero IDs menos legibles |
| Archivo montado (no volumen) | Es lo que usa `datos.py`; se ve y se edita desde el computador | Volumen de Docker: más "limpio", menos visible para principiantes |
| `datos.py` en el computador (no en un contenedor) | Menos piezas; el respaldo queda fuera de Docker | Contenedor `ops`: más aislado |
| Django + Gunicorn (2 workers) en contenedor | Supera la limitación de `http.server` (solo laboratorio) manteniendo intacto el contrato `/`, `/health`, `/pedidos` | `app.py` (stdlib): más liviano, pero monohilo y no apto para producción |
| `init: true` | Python como proceso principal ignora la señal de apagado: sin esto `docker stop` espera 10 s y se acaba matando | - |
