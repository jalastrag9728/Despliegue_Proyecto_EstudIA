# Arquitectura del MVP

```mermaid
flowchart LR
    U([Equipo de operaciones]) -->|127.0.0.1:8080| P[proxy NGINX<br/>reparte y reintenta<br/>registra el upstream]
    P --> A1[app1<br/>INSTANCE_ID=app1]
    P --> A2[app2<br/>INSTANCE_ID=app2]
    A1 -->|solo lectura| D[(data/pedidos.json<br/>copia de trabajo)]
    A2 -->|solo lectura| D
    S[scripts/datos.py<br/>preparar / respaldar / restaurar] -->|escribe| D
    S -->|copia + SHA-256| R[(respaldos/<br/>lugar separado)]
    O[pedidos.json original] -->|preparar| D
    P -. logs: http, upstream .-> L[docker compose logs]
    A1 -. logs de solicitudes .-> L
    A2 -. logs de solicitudes .-> L
```

**Puntos únicos de fallo (declarados):** el computador, el proxy y el archivo de datos compartido. Mejora propuesta: ver `LIMITACIONES.md`.

## Componentes y requisito que cubren

| Componente | Requisito | Dónde |
|---|---|---|
| `app1`, `app2` | Dos instancias del servicio | `compose.yaml` |
| `proxy` NGINX | Punto de acceso común, distribución, reintentos | `proxy/nginx.conf` |
| `/health` + healthcheck de Docker | Forma de comprobar la salud | `app.py`, `compose.yaml` |
| Campo `instancia` + log del proxy (`upstream=`) | Saber qué instancia atendió | `app.py`, `nginx.conf` |
| `docker compose logs` | Consultar registros | - |
| `data/pedidos.json` montado | Datos fuera del almacenamiento efímero | `compose.yaml` |
| `datos.py respaldar/restaurar` + `respaldos/` | Respaldo y restauración definidos, con integridad | `scripts/datos.py` |
| `verificar_servicio.py` + `pruebas_automaticas.py` | Pruebas repetibles y evidencia | `scripts/` |
| GitHub Actions | Reproducibilidad | `.github/workflows/ci.yml` |

## Flujo de una consulta

1. El usuario llama `http://127.0.0.1:8080/pedidos`.
2. NGINX elige la siguiente instancia (round robin) y le reenvía la consulta.
3. La instancia lee `/data/pedidos.json`, responde con `instancia` y la versión y registra código HTTP en consola.
4. Si la instancia no responde (error de conexión o demora), NGINX **reintenta** con la otra; el usuario normalmente no lo nota.

## Qué NO incluye (a propósito)

Multirregión, base de datos distribuida, escritura concurrente, HTTPS, autenticación de usuarios. Ver [`LIMITACIONES.md`](LIMITACIONES.md).
