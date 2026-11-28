#!/usr/bin/env bash
# =============================================================================
# Script de Despliegue Automatizado con AWS CLI para AWS CloudShell (Sin Terraform)
# =============================================================================
# Aprovisiona desde cero la arquitectura completa de Nodo Ruta:
#   1. VPC (10.0.0.0/16) + Internet Gateway (IGW)
#   2. Subred Publica (10.0.1.0/24) + Subredes Privadas (10.0.2.0/24 y 10.0.3.0/24)
#   3. Elastic IP + NAT Gateway en la Subred Publica + Tablas de Ruteo Publica y Privada
#   4. 3 Security Groups encadenados: Proxy SG (:80) -> App SG (:8081-8082) -> RDS SG (:5432)
#   5. Amazon RDS PostgreSQL 16 (db.t3.micro) en las Subredes Privadas
#   6. EC2 #2 (App Server) en Subred Privada: sale por NAT Gateway, hace git clone y docker compose up -d --build
#   7. EC2 #1 (NGINX Proxy) en Subred Publica: balancea hacia la IP privada de EC2 #2 (:8081 y :8082)
#
# Uso en AWS CloudShell:
#   export GIT_REPO_URL="https://github.com/TU_USUARIO/TU_REPO.git"
#   export DB_PASSWORD="NodoRuta2026*"
#   bash scripts/deploy_cloudshell.sh

set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT="${PROJECT_NAME:-nodoruta}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.micro}"
GIT_REPO_URL="${GIT_REPO_URL:-https://github.com/jalastrag9728/Despliegue_Proyecto_EstudIA.git}"
GIT_BRANCH="${GIT_BRANCH:-dev}"
DB_NAME="${DB_NAME:-nodoruta}"
DB_USER="${DB_USER:-nodoruta_admin}"
DB_PASSWORD="${DB_PASSWORD:-NodoRuta2026*}"
KEY_NAME="${KEY_NAME:-}"
STATE_FILE="cloudshell_resources.env"

echo "=================================================================="
echo " Iniciando Despliegue de Nodo Ruta en AWS ($AWS_REGION)"
echo " Repositorio Git: $GIT_REPO_URL (rama: $GIT_BRANCH)"
echo "=================================================================="

# 0. Obtener Zonas de Disponibilidad y AMI de Amazon Linux 2023
AZ_A=$(aws ec2 describe-availability-zones --region "$AWS_REGION" --query "AvailabilityZones[0].ZoneName" --output text)
AZ_B=$(aws ec2 describe-availability-zones --region "$AWS_REGION" --query "AvailabilityZones[1].ZoneName" --output text)
AMI_ID=$(aws ssm get-parameter --region "$AWS_REGION" --name "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64" --query "Parameter.Value" --output text)
echo "[OK] AZs: $AZ_A, $AZ_B | AMI AL2023: $AMI_ID"

# 1. Crear VPC y habilitar DNS
VPC_ID=$(aws ec2 create-vpc --region "$AWS_REGION" --cidr-block 10.0.0.0/16 \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=${PROJECT}-vpc},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "Vpc.VpcId" --output text)
aws ec2 modify-vpc-attribute --region "$AWS_REGION" --vpc-id "$VPC_ID" --enable-dns-support "{\"Value\":true}"
aws ec2 modify-vpc-attribute --region "$AWS_REGION" --vpc-id "$VPC_ID" --enable-dns-hostnames "{\"Value\":true}"
echo "[OK] VPC creada: $VPC_ID"

# 2. Crear Internet Gateway y adjuntarlo a la VPC
IGW_ID=$(aws ec2 create-internet-gateway --region "$AWS_REGION" \
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=${PROJECT}-igw},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "InternetGateway.InternetGatewayId" --output text)
aws ec2 attach-internet-gateway --region "$AWS_REGION" --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID"
echo "[OK] Internet Gateway adjuntado: $IGW_ID"

# 3. Crear Subred Publica y 2 Subredes Privadas (Multi-AZ requerido por RDS)
SUBNET_PUBLIC=$(aws ec2 create-subnet --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --cidr-block 10.0.1.0/24 --availability-zone "$AZ_A" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT}-public-subnet},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "Subnet.SubnetId" --output text)
aws ec2 modify-subnet-attribute --region "$AWS_REGION" --subnet-id "$SUBNET_PUBLIC" --map-public-ip-on-launch

SUBNET_PRIVATE_A=$(aws ec2 create-subnet --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --cidr-block 10.0.2.0/24 --availability-zone "$AZ_A" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT}-private-subnet-a},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "Subnet.SubnetId" --output text)

SUBNET_PRIVATE_B=$(aws ec2 create-subnet --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --cidr-block 10.0.3.0/24 --availability-zone "$AZ_B" \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=${PROJECT}-private-subnet-b},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "Subnet.SubnetId" --output text)
echo "[OK] Subredes creadas: Publica=$SUBNET_PUBLIC | PrivadaA=$SUBNET_PRIVATE_A | PrivadaB=$SUBNET_PRIVATE_B"

# 4. Crear Elastic IP y NAT Gateway en la Subred Publica
EIP_ALLOC_ID=$(aws ec2 allocate-address --region "$AWS_REGION" --domain vpc \
  --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=${PROJECT}-nat-eip},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "AllocationId" --output text)

NAT_GW_ID=$(aws ec2 create-nat-gateway --region "$AWS_REGION" \
  --subnet-id "$SUBNET_PUBLIC" --allocation-id "$EIP_ALLOC_ID" \
  --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=${PROJECT}-nat-gw},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "NatGateway.NatGatewayId" --output text)
echo "[...] Esperando a que el NAT Gateway ($NAT_GW_ID) este disponible (aprox 1-2 min)..."
aws ec2 wait nat-gateway-available --region "$AWS_REGION" --nat-gateway-ids "$NAT_GW_ID"
echo "[OK] NAT Gateway activo: $NAT_GW_ID"

# 5. Configurar Tablas de Ruteo Publica (IGW) y Privada (NAT Gateway)
RT_PUBLIC=$(aws ec2 create-route-table --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${PROJECT}-public-rt},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-route --region "$AWS_REGION" --route-table-id "$RT_PUBLIC" --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW_ID" >/dev/null
aws ec2 associate-route-table --region "$AWS_REGION" --subnet-id "$SUBNET_PUBLIC" --route-table-id "$RT_PUBLIC" >/dev/null

RT_PRIVATE=$(aws ec2 create-route-table --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=${PROJECT}-private-rt},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-route --region "$AWS_REGION" --route-table-id "$RT_PRIVATE" --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$NAT_GW_ID" >/dev/null
aws ec2 associate-route-table --region "$AWS_REGION" --subnet-id "$SUBNET_PRIVATE_A" --route-table-id "$RT_PRIVATE" >/dev/null
aws ec2 associate-route-table --region "$AWS_REGION" --subnet-id "$SUBNET_PRIVATE_B" --route-table-id "$RT_PRIVATE" >/dev/null
echo "[OK] Tablas de ruteo configuradas (Publica -> IGW | Privadas -> NAT Gateway)"

# 6. Crear los 3 Security Groups encadenados
SG_PROXY=$(aws ec2 create-security-group --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --group-name "${PROJECT}-proxy-sg" --description "HTTP publico (80) y SSH (22) hacia Proxy NGINX" \
  --query "GroupId" --output text)
aws ec2 authorize-security-group-ingress --region "$AWS_REGION" --group-id "$SG_PROXY" --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null
aws ec2 authorize-security-group-ingress --region "$AWS_REGION" --group-id "$SG_PROXY" --protocol tcp --port 22 --cidr 0.0.0.0/0 >/dev/null

SG_APP=$(aws ec2 create-security-group --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --group-name "${PROJECT}-app-sg" --description "Trafico 8081-8082 SOLO desde Proxy NGINX" \
  --query "GroupId" --output text)
aws ec2 authorize-security-group-ingress --region "$AWS_REGION" --group-id "$SG_APP" --protocol tcp --port 8081-8082 --source-group "$SG_PROXY" >/dev/null
aws ec2 authorize-security-group-ingress --region "$AWS_REGION" --group-id "$SG_APP" --protocol tcp --port 22 --source-group "$SG_PROXY" >/dev/null

SG_RDS=$(aws ec2 create-security-group --region "$AWS_REGION" --vpc-id "$VPC_ID" \
  --group-name "${PROJECT}-rds-sg" --description "PostgreSQL 5432 SOLO desde EC2 App" \
  --query "GroupId" --output text)
aws ec2 authorize-security-group-ingress --region "$AWS_REGION" --group-id "$SG_RDS" --protocol tcp --port 5432 --source-group "$SG_APP" >/dev/null
echo "[OK] Security Groups creados: Proxy=$SG_PROXY | App=$SG_APP | RDS=$SG_RDS"

# 7. Crear DB Subnet Group y lanzar instancia Amazon RDS PostgreSQL 16
DB_SUBNET_GROUP="${PROJECT}-rds-subnet-group"
aws rds create-db-subnet-group --region "$AWS_REGION" \
  --db-subnet-group-name "$DB_SUBNET_GROUP" \
  --db-subnet-group-description "Subredes privadas para RDS PostgreSQL de Nodo Ruta" \
  --subnet-ids "$SUBNET_PRIVATE_A" "$SUBNET_PRIVATE_B" >/dev/null

RDS_ID="${PROJECT}-rds-postgres"
aws rds create-db-instance --region "$AWS_REGION" \
  --db-instance-identifier "$RDS_ID" \
  --engine postgres \
  --engine-version "16" \
  --db-instance-class db.t3.micro \
  --allocated-storage 20 \
  --storage-type gp2 \
  --db-name "$DB_NAME" \
  --master-username "$DB_USER" \
  --master-user-password "$DB_PASSWORD" \
  --db-subnet-group-name "$DB_SUBNET_GROUP" \
  --vpc-security-group-ids "$SG_RDS" \
  --no-publicly-accessible \
  --no-multi-az \
  --backup-retention-period 0 >/dev/null

echo "[...] Esperando a que Amazon RDS PostgreSQL ($RDS_ID) este disponible (aprox 5-7 min)..."
aws rds wait db-instance-available --region "$AWS_REGION" --db-instance-identifier "$RDS_ID"

RDS_ENDPOINT=$(aws rds describe-db-instances --region "$AWS_REGION" \
  --db-instance-identifier "$RDS_ID" \
  --query "DBInstances[0].Endpoint.Address" --output text)
echo "[OK] RDS PostgreSQL lista en endpoint privado: $RDS_ENDPOINT"

# 8. Lanzar EC2 #2 (Subred Privada): Contenedores de la App (git clone + docker compose)
KEY_ARGS=()
if [ -n "$KEY_NAME" ]; then
  KEY_ARGS=(--key-name "$KEY_NAME")
fi

APP_USER_DATA=$(cat <<EOF
#!/bin/bash
set -euxo pipefail
export HOME=/root

dnf install -y docker git
systemctl enable --now docker
usermod -aG docker ec2-user

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

rm -rf /home/ec2-user/nodoruta
git clone --branch "${GIT_BRANCH}" "${GIT_REPO_URL}" /home/ec2-user/nodoruta || \
  git clone --branch dev "${GIT_REPO_URL}" /home/ec2-user/nodoruta || \
  git clone "${GIT_REPO_URL}" /home/ec2-user/nodoruta
cd /home/ec2-user/nodoruta

cat > /home/ec2-user/nodoruta/.env <<ENVEOF
DB_HOST=${RDS_ENDPOINT}
DB_PORT=5432
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_SSLMODE=prefer
DJANGO_ALLOWED_HOSTS=*
DATA_PATH=/app/pedidos.json
ENVEOF

chown -R ec2-user:ec2-user /home/ec2-user/nodoruta

DOCKER_BUILDKIT=0 docker build -t nodo-ruta-app:aws .

docker run --rm --env-file /home/ec2-user/nodoruta/.env nodo-ruta-app:aws \
  python scripts/datos_rds.py preparar || true

/usr/local/bin/docker-compose -f compose.aws.yaml up -d --no-build || \
  docker compose -f compose.aws.yaml up -d --no-build || true

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
)

EC2_APP_ID=$(aws ec2 run-instances --region "$AWS_REGION" \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --subnet-id "$SUBNET_PRIVATE_A" \
  --security-group-ids "$SG_APP" \
  --no-associate-public-ip-address \
  "${KEY_ARGS[@]}" \
  --user-data "$APP_USER_DATA" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${PROJECT}-app-ec2},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "Instances[0].InstanceId" --output text)

aws ec2 wait instance-running --region "$AWS_REGION" --instance-ids "$EC2_APP_ID"
APP_PRIVATE_IP=$(aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$EC2_APP_ID" \
  --query "Reservations[0].Instances[0].PrivateIpAddress" --output text)
echo "[OK] EC2 #2 (App en Subred Privada) en ejecucion: ID=$EC2_APP_ID | IP Privada=$APP_PRIVATE_IP"

# 9. Lanzar EC2 #1 (Subred Publica): Proxy NGINX apuntando a la IP privada de EC2 #2
PROXY_USER_DATA=$(cat <<EOF
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
    log_format proxylog '\$time_iso8601 cliente=\$remote_addr "\$request" '
                        'http=\$status upstream=\$upstream_addr upstream_http=\$upstream_status '
                        'tiempo_upstream_s=\$upstream_response_time';
    access_log /dev/stdout proxylog;

    upstream nodoruta {
        zone nodoruta 64k;
        server ${APP_PRIVATE_IP}:8081 max_fails=1 fail_timeout=5s;
        server ${APP_PRIVATE_IP}:8082 max_fails=1 fail_timeout=5s;
    }

    server {
        listen 80;
        server_tokens off;

        location / {
            proxy_pass http://nodoruta;
            proxy_http_version 1.1;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;

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
)

EC2_PROXY_ID=$(aws ec2 run-instances --region "$AWS_REGION" \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --subnet-id "$SUBNET_PUBLIC" \
  --security-group-ids "$SG_PROXY" \
  --associate-public-ip-address \
  "${KEY_ARGS[@]}" \
  --user-data "$PROXY_USER_DATA" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${PROJECT}-proxy-ec2},{Key=Proyecto,Value=${PROJECT}}]" \
  --query "Instances[0].InstanceId" --output text)

aws ec2 wait instance-running --region "$AWS_REGION" --instance-ids "$EC2_PROXY_ID"
PROXY_PUBLIC_IP=$(aws ec2 describe-instances --region "$AWS_REGION" --instance-ids "$EC2_PROXY_ID" \
  --query "Reservations[0].Instances[0].PublicIpAddress" --output text)

# Guardar todos los IDs para limpieza facil con scripts/destroy_cloudshell.sh
cat > "$STATE_FILE" <<EOF
AWS_REGION=${AWS_REGION}
VPC_ID=${VPC_ID}
IGW_ID=${IGW_ID}
SUBNET_PUBLIC=${SUBNET_PUBLIC}
SUBNET_PRIVATE_A=${SUBNET_PRIVATE_A}
SUBNET_PRIVATE_B=${SUBNET_PRIVATE_B}
EIP_ALLOC_ID=${EIP_ALLOC_ID}
NAT_GW_ID=${NAT_GW_ID}
RT_PUBLIC=${RT_PUBLIC}
RT_PRIVATE=${RT_PRIVATE}
SG_PROXY=${SG_PROXY}
SG_APP=${SG_APP}
SG_RDS=${SG_RDS}
DB_SUBNET_GROUP=${DB_SUBNET_GROUP}
RDS_ID=${RDS_ID}
EC2_APP_ID=${EC2_APP_ID}
EC2_PROXY_ID=${EC2_PROXY_ID}
PROXY_PUBLIC_IP=${PROXY_PUBLIC_IP}
APP_PRIVATE_IP=${APP_PRIVATE_IP}
RDS_ENDPOINT=${RDS_ENDPOINT}
EOF

echo "=================================================================="
echo " DESPLIEGUE COMPLETADO CON EXITO"
echo "=================================================================="
echo " IP Publica Proxy NGINX : $PROXY_PUBLIC_IP"
echo " IP Privada App Server  : $APP_PRIVATE_IP"
echo " Endpoint RDS Postgres  : $RDS_ENDPOINT"
echo "------------------------------------------------------------------"
echo " Nota: Espere ~90 segundos mientras la EC2 privada termina el"
echo "       'git clone' y 'docker compose up -d --build' via NAT Gateway."
echo " URLs de demostracion:"
echo "   - Health  : http://${PROXY_PUBLIC_IP}/health"
echo "   - Pedidos : http://${PROXY_PUBLIC_IP}/pedidos"
echo "   - Panel   : http://${PROXY_PUBLIC_IP}/panel"
echo "=================================================================="
