# Diseño equivalente en la nube (documentado, NO desplegado)

> La guía indica que, si no hay cuenta habilitada por el entorno educativo, se documenta la demostración local y el **diseño pendiente**.
> **No se contrató ningún recurso ni se inventaron precios.** Lo probado es la demostración local; esto es diseño.

## Equivalencias pieza por pieza

| Pieza local | Azure | AWS | Google Cloud |
|---|---|---|---|
| Imagen `nodo-ruta-app` | Azure Container Registry | Amazon ECR | Artifact Registry |
| `app1`, `app2` | Azure Container Apps (mín. 2 réplicas) | ECS Fargate (2 tareas) | Cloud Run (mín. 2 instancias) |
| Proxy NGINX + reintentos | Ingress / Application Gateway | Application Load Balancer | Cloud Load Balancing |
| `/health` | Health probes | Health check del *target group* | Health checks |
| `data/pedidos.json` | Azure Files, o BD administrada | Amazon EFS, o RDS/DynamoDB | Filestore, o Cloud SQL |
| `respaldos/` + `datos.py` | Blob Storage (otra cuenta/región, con retención) | S3 con versionado | Cloud Storage con versionado |
| `docker compose logs` | Azure Monitor / Log Analytics | CloudWatch Logs | Cloud Logging |
| Permisos del equipo | Roles (RBAC) con mínimo privilegio | IAM con mínimo privilegio | IAM con mínimo privilegio |
| HTTPS | Certificado administrado en el ingress | ACM en el ALB | Certificado administrado |
| Secretos (si aparecieran) | Key Vault | Secrets Manager | Secret Manager |

## Cómo se eliminarían los puntos únicos de fallo (mejora, no probada)

| Hoy (local) | En nube |
|---|---|
| Un solo computador | Réplicas en **≥ 2 zonas de disponibilidad** |
| Un solo proxy | Balanceador administrado y redundante |
| Un solo archivo compartido | Almacenamiento replicado entre zonas o base de datos administrada |
| Respaldos en el mismo equipo | Respaldos en otra cuenta/región, versionados, con prueba de restauración periódica |
| Detección pasiva | Health checks **activos** del balanceador + alertas |

## Permisos y HTTPS

Una identidad por componente con permisos mínimos (la app solo lee datos; el proceso de respaldo solo escribe en el almacenamiento de respaldos);
acceso humano por roles, con autenticación multifactor; HTTPS terminado en el balanceador con certificado administrado; nada de claves en el repositorio.

## Factores de consumo que podrían generar costo (sin precios)

| Factor | Qué lo hace crecer | Cómo controlarlo |
|---|---|---|
| Cómputo (vCPU/memoria × horas × réplicas) | Más réplicas, más tamaño, más horas encendido | Mínimo de réplicas, límites, apagar tras la prueba |
| Balanceador (horas + tráfico procesado) | Siempre activo | Uno solo, retirarlo al terminar |
| Almacenamiento de datos | Tamaño y operaciones | Datos pequeños, clase mínima |
| Respaldos (GB-mes, operaciones, transferencia) | Frecuencia × retención × tamaño | Retención limitada, ciclo de vida |
| Registros (ingesta + retención) | Logs verbosos, retención larga | Nivel adecuado, retención corta |
| Transferencia de salida | Consultas desde fuera, copias entre regiones | Misma región |
| Registro de imágenes | Número y tamaño de imágenes | Imagen mínima, borrar versiones viejas |

Etiquete todo lo creado como `proyecto=nodoruta` y elimínelo al terminar. Revise los límites de la cuenta educativa antes de crear nada.
