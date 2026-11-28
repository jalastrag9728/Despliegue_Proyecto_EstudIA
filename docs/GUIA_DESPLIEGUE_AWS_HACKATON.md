# Guía de Despliegue en AWS para la Hackatón (2 EC2 + RDS PostgreSQL + VPC + NAT Gateway)

Esta guía resume todo lo que necesitan para levantar la arquitectura en **menos de 15 minutos** durante la hackatón, ya sea con **Terraform (IaC)** o con el **script de comandos AWS CLI en CloudShell** como contingencia.

---

## 1. Arquitectura Desplegada

```mermaid
flowchart TB
    Internet(["Usuario / Jurado Hackatón"])
    GitHub(["GitHub & Docker Hub"])

    subgraph VPC["VPC Nodo Ruta (10.0.0.0/16)"]
        IGW["Internet Gateway (IGW)"]

        subgraph PublicSubnet["Subred Pública (10.0.1.0/24)"]
            NAT["NAT Gateway + Elastic IP"]
            subgraph SG_Proxy["SG: nodoruta-proxy-sg (In: 80, 22)"]
                EC2_Proxy["EC2 #1: NGINX Proxy (t3.micro)\nIP Pública\nContenedor: nginx:1.28-alpine (:80)"]
            end
        end

        subgraph PrivateSubnetA["Subred Privada A (10.0.2.0/24)"]
            subgraph SG_App["SG: nodoruta-app-sg (In: 8081-8082 desde SG_Proxy)"]
                EC2_App["EC2 #2: App Server (t3.micro - Sin IP Pública)\ngit clone + docker compose up -d --build\n- app1 (:8081 -> :8080)\n- app2 (:8082 -> :8080)"]
            end
        end

        subgraph PrivateSubnetB["Subredes Privadas A y B (10.0.2.0/24 y 10.0.3.0/24)"]
            subgraph SG_RDS["SG: nodoruta-rds-sg (In: 5432 solo desde SG_App)"]
                RDS[("Amazon RDS PostgreSQL 16\n(db.t3.micro - Privada)\nBD: nodoruta")]
            end
        end
    end

    Internet -->|"1. HTTP :80"| IGW
    IGW -->|"2. Entrada pública"| EC2_Proxy
    EC2_Proxy -->|"3. Round-Robin privado\n(:8081 y :8082)"| EC2_App
    EC2_App -->|"4. SQL :5432 (psycopg)"| RDS
    EC2_App -.->|"5. git clone / docker build"| NAT
    NAT -.-> IGW
    IGW -.-> GitHub
```

---

## 2. Modelo Entidad-Relación en RDS PostgreSQL

La migración desde el sistema antiguo (`pedidos.json`) crea automáticamente tres tablas en RDS PostgreSQL:

```mermaid
erDiagram
    ESTADO_SISTEMA ||--o{ PEDIDO : "controla_version"
    ESTADO_SISTEMA {
        int id PK "1 (Singleton)"
        varchar(50) version "Ej: 'datos-v1'"
        boolean datos_validos "TRUE = 200 OK, FALSE = 503 (Prueba I05)"
        timestamptz actualizado_en
    }

    PEDIDO {
        varchar(20) id PK "PED-001 .. PED-006"
        varchar(50) zona
        varchar(50) estado
        varchar(30) prioridad
        varchar(80) vehiculo
        varchar(50) ventana
        smallint progreso
        text novedad
        int orden
    }

    RESPALDO_SNAPSHOT {
        serial id PK
        varchar(100) nombre_archivo UK
        varchar(50) version
        jsonb contenido
        char(64) sha256
        timestamptz creado_en
    }
```

---

## 3. Credenciales y Requisitos Previos

Antes de empezar a correr los comandos en AWS, asegúrate de tener:

1. **Repositorio en GitHub Público con estos últimos cambios subidos (`git push`)**:
   - Porque la **EC2 #2 (en la Subred Privada)** sale a internet por el **NAT Gateway** y ejecuta:
     `git clone https://github.com/<TU_USUARIO>/<TU_REPO>.git` y luego `docker compose -f compose.aws.yaml up -d --build`.
2. **Sesión abierta en la Consola de AWS (CloudShell)**:
   - En **AWS CloudShell** (el ícono `>_` arriba a la derecha en la consola de AWS) **NO necesitas configurar `aws configure`**, porque CloudShell ya tiene tus credenciales cargadas automáticamente.
   - Si en cambio corres Terraform desde tu PC local, debes exportar:
     ```bash
     export AWS_ACCESS_KEY_ID="TU_ACCESS_KEY"
     export AWS_SECRET_ACCESS_KEY="TU_SECRET_KEY"
     export AWS_SESSION_TOKEN="TU_SESSION_TOKEN" # Solo si usas AWS Academy / cuenta educativa
     ```
3. **Contraseña para RDS PostgreSQL (`DB_PASSWORD`)**:
   - Mínimo 8 caracteres alfanuméricos, por ejemplo: `NodoRuta2026*`.

---

## 4. Opción A (Recomendada): Despliegue con Terraform en AWS CloudShell

Abre **AWS CloudShell** en tu navegador y pega estos bloques:

```bash
# 1. Instalar Terraform en AWS CloudShell (tarda ~10 segundos)
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
sudo yum -y install terraform

# 2. Clonar tu repositorio en CloudShell (rama dev o main)
git clone --branch dev https://github.com/<TU_USUARIO>/<TU_REPO>.git || git clone https://github.com/<TU_USUARIO>/<TU_REPO>.git
cd <TU_REPO>/infra

# 3. Inicializar y aplicar Terraform
terraform init
terraform apply -auto-approve \
  -var="git_repo_url=https://github.com/<TU_USUARIO>/<TU_REPO>.git" \
  -var="git_branch=dev" \
  -var="db_password=NodoRuta2026*"
```

Al terminar (tarda ~7-9 minutos por la creación de RDS y NAT Gateway), Terraform imprimirá:
- `service_url_panel = "http://<IP_PUBLICA_PROXY>/panel"`
- `service_url_pedidos = "http://<IP_PUBLICA_PROXY>/pedidos"`
- `service_url_health = "http://<IP_PUBLICA_PROXY>/health"`

*(Espera ~90 segundos tras terminar `terraform apply` mientras la EC2 privada descarga e instala los contenedores vía NAT Gateway).*

---

## 5. Opción B (Contingencia): Script de Comandos AWS CLI en CloudShell (Sin Terraform)

Si Terraform falla o prefieren ejecutar directamente los comandos de AWS CLI (`aws ec2` y `aws rds`), abre **AWS CloudShell** y ejecuta:

```bash
# 1. Clonar tu repositorio en CloudShell (rama dev o main)
git clone --branch dev https://github.com/<TU_USUARIO>/<TU_REPO>.git || git clone https://github.com/<TU_USUARIO>/<TU_REPO>.git
cd <TU_REPO>

# 2. Definir la URL de tu repositorio y contraseña de RDS
export GIT_REPO_URL="https://github.com/<TU_USUARIO>/<TU_REPO>.git"
export GIT_BRANCH="dev"
export DB_PASSWORD="NodoRuta2026*"

# 3. Ejecutar el despliegue automatizado por comandos de AWS CLI
bash scripts/deploy_cloudshell.sh
```

---

## 6. Limpieza al Terminar la Hackatón (Evitar Costos)

- **Si desplegaste con Terraform**:
  ```bash
  cd infra
  terraform destroy -auto-approve \
    -var="git_repo_url=https://github.com/<TU_USUARIO>/<TU_REPO>.git" \
    -var="db_password=NodoRuta2026*"
  ```
- **Si desplegaste con el script de CloudShell**:
  ```bash
  bash scripts/destroy_cloudshell.sh
  ```
