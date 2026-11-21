# Diseño equivalente en la nube (documentado, NO desplegado)

> Cumple la condición del reto: *"sin cuenta habilitada sin cobros, se admite demostración local y un diseño documentado equivalente en nube"*.
> **No se contrató ningún recurso.** Esta sección es diseño; lo que sí se probó es la demostración local.

## Equivalencias pieza por pieza

| Pieza local | Qué hace | Equivalente en Azure | Equivalente en AWS | Equivalente en Google Cloud |
|---|---|---|---|---|
| Imagen `nodoruta-app` | Empaqueta la app | Azure Container Registry (o GHCR) | Amazon ECR (o GHCR) | Artifact Registry (o GHCR) |
| 2+ instancias `app` | Réplicas del servicio | Azure Container Apps (mín. 2 réplicas) | ECS Fargate (2 tareas) | Cloud Run (mín. 2 instancias) |
| HAProxy | Punto de acceso + balanceo + salud | Ingress de Container Apps / Application Gateway | Application Load Balancer + *target group* con health check | Cloud Load Balancing |
| `GET /health` | Salud | *Health probes* (liveness/readiness) | Health check del *target group* | Health checks / startup probes |
| Volumen `datos` | Datos fuera del contenedor | Azure Files (o base de datos administrada) | Amazon EFS (o RDS/DynamoDB) | Filestore o Cloud Storage (o Cloud SQL) |
| `respaldos/` + `ops.sh` | Copias separadas verificables | Blob Storage (otra cuenta/región) con retención | S3 (otra cuenta/región) con versionado y ciclo de vida | Cloud Storage con versionado y retención |
| `docker compose logs` | Registros | Log Analytics / Azure Monitor | CloudWatch Logs | Cloud Logging |
| Panel `/stats` | Estado | Azure Monitor métricas | CloudWatch métricas / alarmas | Cloud Monitoring |
| GitHub Actions | Construir y desplegar | GitHub Actions + OIDC (sin claves guardadas) | GitHub Actions + OIDC | GitHub Actions + Workload Identity |
| `.env` / secretos | Configuración sensible | Key Vault | Secrets Manager | Secret Manager |

## Cómo se obtendría alta disponibilidad real (mejora, no probada aquí)

1. Réplicas repartidas en **al menos 2 zonas de disponibilidad**.
2. Datos en almacenamiento **replicado entre zonas** (o base de datos administrada con réplica).
3. Respaldos en una **cuenta y región distintas**, con versionado y pruebas periódicas de restauración.
4. Alertas sobre salud, errores 5xx y fallos de respaldo.
5. Despliegue gradual (*rolling update*) con *rollback* automático si falla la salud.

## Factores de consumo que generarían costo

(No se incluyen precios: dependen del proveedor, región y vigencia de la cuenta educativa.)

| Factor | Qué lo hace crecer | Cómo controlarlo |
|---|---|---|
| Cómputo (vCPU/memoria × horas × réplicas) | Más réplicas, más tamaño, más horas encendido | Mínimo de réplicas, límites de recursos, apagar fuera de la demo |
| Balanceador (horas + volumen procesado) | Siempre activo y con mucho tráfico | Un solo balanceador compartido; retirar tras la prueba |
| Almacenamiento de datos (GB-mes + operaciones) | Tamaño del archivo/base | Datos pequeños; clase de almacenamiento mínima |
| Respaldos (GB-mes + operaciones + transferencia) | Frecuencia × retención × tamaño | Retención (`BACKUP_RETENTION`), ciclo de vida a clase fría |
| Registros (ingesta + retención) | Logs verbosos, retención larga | Nivel `info`, retención corta, muestreo |
| Transferencia de salida (*egress*) | Consultas desde fuera de la nube, copias entre regiones | Misma región, respuestas pequeñas |
| Registro de imágenes | Número y tamaño de imágenes | Imagen mínima, borrar versiones viejas |

## Limpieza al usar cuentas educativas

Revise los límites de la cuenta, etiquete todos los recursos como `proyecto=nodoruta-hackaton` y elimínelos al terminar (un único grupo de
recursos / *stack* facilita borrarlos de una vez).
