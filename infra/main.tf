# =============================================================================
# Infraestructura como Codigo (Terraform) para Nodo Ruta en AWS - Hackaton
# =============================================================================
# Arquitectura Cloud de Produccion:
# 1. VPC dedicada (10.0.0.0/16) con Internet Gateway (IGW).
# 2. Subred Publica (10.0.1.0/24):
#    - EC2 #1 (Proxy NGINX): unico punto de entrada publico en puerto 80.
#    - NAT Gateway + Elastic IP: brinda salida a internet segura a la subred privada.
# 3. Subredes Privadas (10.0.2.0/24 y 10.0.3.0/24 en 2 Zonas de Disponibilidad):
#    - EC2 #2 (Contenedores App1 y App2): sin IP publica; sale por el NAT Gateway
#      para hacer "git clone" y "docker compose -f compose.aws.yaml up -d --build".
#    - Amazon RDS PostgreSQL 16 (db.t3.micro): base de datos relacional privada.
# 4. Security Groups encadenados (Minimo Privilegio):
#    - Internet -> Proxy SG (:80) -> App SG (:8081, :8082) -> RDS SG (:5432).
#
# Uso en AWS CloudShell o terminal local:
#   cd infra
#   terraform init
#   terraform apply -auto-approve \
#     -var="git_repo_url=https://github.com/TU_USUARIO/TU_REPO.git" \
#     -var="db_password=NodoRuta2026*"

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
variable "aws_region" {
  description = "Region de AWS donde se desplegara Nodo Ruta"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefijo para etiquetar todos los recursos del proyecto"
  type        = string
  default     = "nodoruta"
}

variable "instance_type" {
  description = "Tipo de instancia EC2 (t3.micro o t2.micro para Free Tier)"
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Nombre del Key Pair existente en AWS EC2 para acceso SSH (opcional)"
  type        = string
  default     = ""
}

variable "git_repo_url" {
  description = "URL HTTPS del repositorio Git que clonara la EC2 privada para construir la imagen con Docker Compose"
  type        = string
  default     = "https://github.com/jalastrag9728/Despliegue_Proyecto_EstudIA.git"
}

variable "git_branch" {
  description = "Rama del repositorio Git a desplegar (por defecto dev; hace fallback automatico a main)"
  type        = string
  default     = "dev"
}

variable "db_name" {
  description = "Nombre de la base de datos en RDS PostgreSQL"
  type        = string
  default     = "nodoruta"
}

variable "db_username" {
  description = "Usuario maestro de RDS PostgreSQL"
  type        = string
  default     = "nodoruta_admin"
}

variable "db_password" {
  description = "Contrasena maestra de RDS PostgreSQL (minimo 8 caracteres)"
  type        = string
  sensitive   = true
  default     = "NodoRuta2026*"
}

# -----------------------------------------------------------------------------
# Datos de Zonas de Disponibilidad y AMI Amazon Linux 2023
# -----------------------------------------------------------------------------
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

# -----------------------------------------------------------------------------
# 1. Red: VPC, Subred Publica, Subredes Privadas, IGW y NAT Gateway
# -----------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name     = "${var.project_name}-vpc"
    Proyecto = var.project_name
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name     = "${var.project_name}-igw"
    Proyecto = var.project_name
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name     = "${var.project_name}-public-subnet"
    Proyecto = var.project_name
  }
}

resource "aws_subnet" "private_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = false

  tags = {
    Name     = "${var.project_name}-private-subnet-a"
    Proyecto = var.project_name
  }
}

resource "aws_subnet" "private_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.3.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = false

  tags = {
    Name     = "${var.project_name}-private-subnet-b"
    Proyecto = var.project_name
  }
}

resource "aws_eip" "nat_eip" {
  domain = "vpc"

  tags = {
    Name     = "${var.project_name}-nat-eip"
    Proyecto = var.project_name
  }
}

resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public.id

  depends_on = [aws_internet_gateway.igw]

  tags = {
    Name     = "${var.project_name}-nat-gw"
    Proyecto = var.project_name
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name     = "${var.project_name}-public-rt"
    Proyecto = var.project_name
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }

  tags = {
    Name     = "${var.project_name}-private-rt"
    Proyecto = var.project_name
  }
}

resource "aws_route_table_association" "private_a_assoc" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "private_b_assoc" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private_rt.id
}

# -----------------------------------------------------------------------------
# 2. Security Groups encadenados (Proxy -> App -> RDS PostgreSQL)
# -----------------------------------------------------------------------------
resource "aws_security_group" "proxy_sg" {
  name        = "${var.project_name}-proxy-sg"
  description = "Permite HTTP (80) publico al proxy NGINX y SSH (22)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP publico hacia proxy NGINX"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH para administracion"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Salida hacia EC2 App e Internet"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name     = "${var.project_name}-proxy-sg"
    Proyecto = var.project_name
  }
}

resource "aws_security_group" "app_sg" {
  name        = "${var.project_name}-app-sg"
  description = "Permite trafico a contenedores app1 (8081) y app2 (8082) SOLO desde el Proxy NGINX"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP interno desde EC2 Proxy NGINX hacia app1 (8081) y app2 (8082)"
    from_port       = 8081
    to_port         = 8082
    protocol        = "tcp"
    security_groups = [aws_security_group.proxy_sg.id]
  }

  ingress {
    description     = "SSH desde EC2 Proxy (Bastion)"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.proxy_sg.id]
  }

  egress {
    description = "Salida hacia RDS PostgreSQL y NAT Gateway (git clone / docker build)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name     = "${var.project_name}-app-sg"
    Proyecto = var.project_name
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Permite conexiones PostgreSQL (5432) UNICAMENTE desde la EC2 de Contenedores App"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL desde EC2 App"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name     = "${var.project_name}-rds-sg"
    Proyecto = var.project_name
  }
}

# -----------------------------------------------------------------------------
# 3. Base de Datos: Amazon RDS PostgreSQL 16 (Subredes Privadas)
# -----------------------------------------------------------------------------
resource "aws_db_subnet_group" "rds_subnets" {
  name       = "${var.project_name}-rds-subnet-group"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = {
    Name     = "${var.project_name}-rds-subnet-group"
    Proyecto = var.project_name
  }
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.project_name}-rds-postgres"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds_subnets.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false

  tags = {
    Name     = "${var.project_name}-rds-postgres"
    Proyecto = var.project_name
  }
}

# -----------------------------------------------------------------------------
# 4. EC2 #2 (Subred Privada): Contenedores de la App (git clone + docker compose)
# -----------------------------------------------------------------------------
resource "aws_instance" "app_ec2" {
  ami                         = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.private_a.id
  vpc_security_group_ids      = [aws_security_group.app_sg.id]
  associate_public_ip_address = false
  user_data_replace_on_change = true
  key_name                    = var.key_name != "" ? var.key_name : null

  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail
    export HOME=/root

    dnf install -y docker git
    systemctl enable --now docker
    usermod -aG docker ec2-user

    # Instalar plugins Docker Buildx y Docker Compose v2 en todas las rutas estandar de AL2023
    mkdir -p /usr/local/lib/docker/cli-plugins /usr/libexec/docker/cli-plugins /root/.docker/cli-plugins
    curl -fSL "https://github.com/docker/buildx/releases/download/v0.20.1/buildx-v0.20.1.linux-amd64" \
      -o /usr/local/lib/docker/cli-plugins/docker-buildx || true
    if [ -f /usr/local/lib/docker/cli-plugins/docker-buildx ]; then
      chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
      cp /usr/local/lib/docker/cli-plugins/docker-buildx /usr/libexec/docker/cli-plugins/docker-buildx
      cp /usr/local/lib/docker/cli-plugins/docker-buildx /root/.docker/cli-plugins/docker-buildx
    fi

    curl -fSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
      -o /usr/local/lib/docker/cli-plugins/docker-compose || true
    if [ -f /usr/local/lib/docker/cli-plugins/docker-compose ]; then
      chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
      cp /usr/local/lib/docker/cli-plugins/docker-compose /usr/libexec/docker/cli-plugins/docker-compose
      cp /usr/local/lib/docker/cli-plugins/docker-compose /root/.docker/cli-plugins/docker-compose
      ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose
    fi

    # Clonar el repositorio usando la salida por NAT Gateway (soporta rama dev o main con fallback)
    rm -rf /home/ec2-user/nodoruta
    git clone --branch "${var.git_branch}" "${var.git_repo_url}" /home/ec2-user/nodoruta || \
      git clone --branch dev "${var.git_repo_url}" /home/ec2-user/nodoruta || \
      git clone "${var.git_repo_url}" /home/ec2-user/nodoruta
    cd /home/ec2-user/nodoruta

    # Configurar variables de entorno apuntando a Amazon RDS PostgreSQL
    cat > /home/ec2-user/nodoruta/.env <<ENVEOF
    DB_HOST=${aws_db_instance.postgres.address}
    DB_PORT=${aws_db_instance.postgres.port}
    DB_NAME=${var.db_name}
    DB_USER=${var.db_username}
    DB_PASSWORD=${var.db_password}
    DB_SSLMODE=prefer
    DJANGO_ALLOWED_HOSTS=*
    DATA_PATH=/app/pedidos.json
    ENVEOF

    chown -R ec2-user:ec2-user /home/ec2-user/nodoruta

    # 1. Construir la imagen una sola vez con el motor nativo de Docker (sin depender de buildx)
    DOCKER_BUILDKIT=0 docker build -t nodo-ruta-app:aws .

    # 2. Migrar semilla pedidos.json hacia Amazon RDS PostgreSQL
    docker run --rm --env-file /home/ec2-user/nodoruta/.env nodo-ruta-app:aws \
      python scripts/datos_rds.py preparar || true

    # 3. Levantar app1 (:8081) y app2 (:8082) con Docker Compose (--no-build)
    /usr/local/bin/docker-compose -f compose.aws.yaml up -d --no-build || \
      docker compose -f compose.aws.yaml up -d --no-build || true

    # 4. Fallback garantizado: si 8081 o 8082 no estan escuchando, levantarlos con docker run directo
    if ! docker ps | grep -q '8081->8080'; then
      docker rm -f nodoruta-app1 nodoruta-app2 || true
      docker run -d \
        --name nodoruta-app1 \
        --restart unless-stopped \
        --env-file /home/ec2-user/nodoruta/.env \
        -e INSTANCE_ID=app1 \
        -p 8081:8080 \
        nodo-ruta-app:aws
      docker run -d \
        --name nodoruta-app2 \
        --restart unless-stopped \
        --env-file /home/ec2-user/nodoruta/.env \
        -e INSTANCE_ID=app2 \
        -p 8082:8080 \
        nodo-ruta-app:aws
    fi
  EOF

  depends_on = [
    aws_nat_gateway.nat,
    aws_route_table_association.private_a_assoc,
    aws_db_instance.postgres
  ]

  tags = {
    Name     = "${var.project_name}-app-ec2"
    Proyecto = var.project_name
  }
}

# -----------------------------------------------------------------------------
# 5. EC2 #1 (Subred Publica): Proxy Inverso NGINX
# -----------------------------------------------------------------------------
resource "aws_instance" "proxy_ec2" {
  ami                         = data.aws_ssm_parameter.al2023_ami.value
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.proxy_sg.id]
  associate_public_ip_address = true
  user_data_replace_on_change = true
  key_name                    = var.key_name != "" ? var.key_name : null

  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail

    dnf install -y docker
    systemctl enable --now docker
    usermod -aG docker ec2-user

    mkdir -p /etc/nodoruta-nginx
    cat > /etc/nodoruta-nginx/nginx.conf <<'NGINXEOF'
    worker_processes auto;
    error_log /dev/stderr warn;
    pid /tmp/nginx.pid;

    events {
        worker_connections 256;
    }

    http {
        log_format proxylog '$time_iso8601 cliente=$remote_addr "$request" '
                            'http=$status upstream=$upstream_addr upstream_http=$upstream_status '
                            'tiempo_upstream_s=$upstream_response_time';
        access_log /dev/stdout proxylog;

        upstream nodoruta {
            zone nodoruta 64k;
            server ${aws_instance.app_ec2.private_ip}:8081 max_fails=1 fail_timeout=5s;
            server ${aws_instance.app_ec2.private_ip}:8082 max_fails=1 fail_timeout=5s;
        }

        server {
            listen 80;
            server_tokens off;

            location / {
                proxy_pass http://nodoruta;
                proxy_http_version 1.1;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;

                proxy_connect_timeout 3s;
                proxy_read_timeout 10s;

                proxy_next_upstream error timeout;
                proxy_next_upstream_tries 2;
                proxy_next_upstream_timeout 10s;
            }
        }
    }
    NGINXEOF

    docker run -d \
      --name nodoruta-proxy \
      --restart unless-stopped \
      -p 80:80 \
      -v /etc/nodoruta-nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
      nginx:1.28-alpine
  EOF

  depends_on = [aws_instance.app_ec2]

  tags = {
    Name     = "${var.project_name}-proxy-ec2"
    Proyecto = var.project_name
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "proxy_public_ip" {
  description = "IP publica de la EC2 #1 (Proxy NGINX en subred publica)"
  value       = aws_instance.proxy_ec2.public_ip
}

output "app_private_ip" {
  description = "IP privada de la EC2 #2 (Contenedores App1 y App2 en subred privada)"
  value       = aws_instance.app_ec2.private_ip
}

output "rds_endpoint" {
  description = "Endpoint DNS de la instancia Amazon RDS PostgreSQL en subred privada"
  value       = aws_db_instance.postgres.address
}

output "service_url_pedidos" {
  description = "URL publica del endpoint /pedidos"
  value       = "http://${aws_instance.proxy_ec2.public_ip}/pedidos"
}

output "service_url_health" {
  description = "URL publica del endpoint /health"
  value       = "http://${aws_instance.proxy_ec2.public_ip}/health"
}

output "service_url_panel" {
  description = "URL publica del panel visual de Nodo Ruta"
  value       = "http://${aws_instance.proxy_ec2.public_ip}/panel"
}
