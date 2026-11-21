# Seguridad y costos (decisiones del MVP)

## Seguridad

| Riesgo | Medida aplicada | Dónde verificar |
|---|---|---|
| Secretos filtrados en imagen o repo | El MVP **no usa secretos**; `.gitignore` bloquea `.env`, `*.pem`, `*.key`, `secrets/`; `.env.example` solo trae valores no sensibles | `.gitignore`, `.env.example` |
| Contenedor comprometido escala privilegios | Usuario **no-root** (UID 10001), `read_only`, `cap_drop: ALL`, `no-new-privileges` | `Dockerfile`, `docker-compose.yml` |
| Exposición de red excesiva | Puertos publicados solo en `127.0.0.1`; las instancias solo se exponen a la red interna de Docker (`expose`, no `ports`) | `docker-compose.yml` |
| App dañando los datos | Volumen de datos **solo lectura** para las apps | `docker-compose.yml` |
| Respaldo corrupto o manipulado | SHA-256 por respaldo, verificado **antes** de restaurar; restauración atómica | `scripts/ops.sh` |
| Pérdida del respaldo junto con los datos | Respaldo en ubicación **separada** (`./respaldos`) | `docker-compose.yml` |
| Datos sensibles | Solo datos **sintéticos**; sin nombres, direcciones, pagos ni documentos | `app/seed/pedidos.json` |
| Imagen con vulnerabilidades | Base oficial `python:3.12-slim` sin dependencias extra; *(mejora)* escaneo con Trivy en CI y fijar versiones por *digest* | `Dockerfile` |
| Panel de estado sin autenticación | Solo accesible desde el propio equipo (`127.0.0.1:8404`) | `docker-compose.yml` |
| Servicio sin TLS/autenticación | Fuera del alcance (solo demo local). *(mejora)* TLS en el balanceador/ingress administrado + identidad corporativa | - |

> Nota: el contenedor `ops` (herramientas de respaldo) corre como root **solo cuando se invoca** manualmente, porque debe escribir en el volumen y en la
> carpeta de respaldos del anfitrión. No forma parte del servicio en ejecución.

## Costos del MVP

- **Costo de ejecución: cero** - corre en el computador del equipo con herramientas gratuitas (Docker Desktop puede tener condiciones de licencia
  para empresas grandes; *Docker Engine* en Linux o alternativas como Podman evitan ese punto).
- GitHub Actions y GHCR: planes gratuitos con límites de uso; revise los de su cuenta.
- Controles ya incluidos: límites de CPU/memoria por instancia, rotación de logs (10 MB × 3), retención de respaldos (10 por defecto).
- Factores de costo en nube: ver [`NUBE_EQUIVALENTE.md`](NUBE_EQUIVALENTE.md).
