#!/usr/bin/env bash
# =============================================================================
# Script para eliminar todos los recursos creados por deploy_cloudshell.sh
# =============================================================================
set -euo pipefail

STATE_FILE="${1:-cloudshell_resources.env}"
if [ ! -f "$STATE_FILE" ]; then
  echo "No se encontro el archivo $STATE_FILE."
  exit 1
fi

# shellcheck disable=SC1090
source "$STATE_FILE"

echo "Eliminando instancias EC2 ($EC2_PROXY_ID, $EC2_APP_ID)..."
aws ec2 terminate-instances --region "$AWS_REGION" --instance-ids "$EC2_PROXY_ID" "$EC2_APP_ID" >/dev/null || true
aws ec2 wait instance-terminated --region "$AWS_REGION" --instance-ids "$EC2_PROXY_ID" "$EC2_APP_ID" || true

echo "Eliminando instancia RDS PostgreSQL ($RDS_ID)..."
aws rds delete-db-instance --region "$AWS_REGION" --db-instance-identifier "$RDS_ID" --skip-final-snapshot --delete-automated-backups >/dev/null || true
aws rds wait db-instance-deleted --region "$AWS_REGION" --db-instance-identifier "$RDS_ID" || true

echo "Eliminando DB Subnet Group ($DB_SUBNET_GROUP)..."
aws rds delete-db-subnet-group --region "$AWS_REGION" --db-subnet-group-name "$DB_SUBNET_GROUP" >/dev/null || true

echo "Eliminando NAT Gateway ($NAT_GW_ID) y liberando Elastic IP ($EIP_ALLOC_ID)..."
aws ec2 delete-nat-gateway --region "$AWS_REGION" --nat-gateway-id "$NAT_GW_ID" >/dev/null || true
aws ec2 wait nat-gateway-deleted --region "$AWS_REGION" --nat-gateway-ids "$NAT_GW_ID" || true
aws ec2 release-address --region "$AWS_REGION" --allocation-id "$EIP_ALLOC_ID" >/dev/null || true

echo "Eliminando Security Groups..."
aws ec2 delete-security-group --region "$AWS_REGION" --group-id "$SG_RDS" >/dev/null || true
aws ec2 delete-security-group --region "$AWS_REGION" --group-id "$SG_APP" >/dev/null || true
aws ec2 delete-security-group --region "$AWS_REGION" --group-id "$SG_PROXY" >/dev/null || true

echo "Eliminando Subredes y Tablas de Ruteo..."
aws ec2 delete-subnet --region "$AWS_REGION" --subnet-id "$SUBNET_PUBLIC" >/dev/null || true
aws ec2 delete-subnet --region "$AWS_REGION" --subnet-id "$SUBNET_PRIVATE_A" >/dev/null || true
aws ec2 delete-subnet --region "$AWS_REGION" --subnet-id "$SUBNET_PRIVATE_B" >/dev/null || true
aws ec2 delete-route-table --region "$AWS_REGION" --route-table-id "$RT_PUBLIC" >/dev/null || true
aws ec2 delete-route-table --region "$AWS_REGION" --route-table-id "$RT_PRIVATE" >/dev/null || true

echo "Desadjuntando y eliminando Internet Gateway ($IGW_ID) y VPC ($VPC_ID)..."
aws ec2 detach-internet-gateway --region "$AWS_REGION" --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID" >/dev/null || true
aws ec2 delete-internet-gateway --region "$AWS_REGION" --internet-gateway-id "$IGW_ID" >/dev/null || true
aws ec2 delete-vpc --region "$AWS_REGION" --vpc-id "$VPC_ID" >/dev/null || true

rm -f "$STATE_FILE"
echo "[OK] Todos los recursos de AWS fueron eliminados sin dejar costos activos."
