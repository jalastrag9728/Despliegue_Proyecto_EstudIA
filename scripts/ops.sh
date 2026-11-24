#!/bin/sh
# Operaciones de datos: respaldar, alterar (solo para pruebas), restaurar y verificar.
# Se ejecuta DENTRO de un contenedor (servicio "ops" de compose.yaml):
#   docker compose run --rm ops backup | tamper | restore [archivo] | status | list | auto
# Salida legible por personas y por el script de pruebas (líneas CLAVE=valor).
set -eu

DATA_DIR="${DATA_DIR:-/data}"
BACKUP_DIR="${BACKUP_DIR:-/respaldos}"
ARCHIVO="${DATA_DIR}/pedidos.json"
RETENCION="${BACKUP_RETENTION:-10}"

version_de() { grep -o '"version": *"[^"]*"' "$1" | head -n1 | sed 's/.*: *"\(.*\)"/\1/'; }
hash_de()    { sha256sum "$1" | cut -d' ' -f1; }

cmd_status() {
  [ -f "$ARCHIVO" ] || { echo "ERROR=no existe $ARCHIVO"; exit 1; }
  echo "VERSION=$(version_de "$ARCHIVO")"
  echo "SHA256=$(hash_de "$ARCHIVO")"
}

cmd_backup() {
  [ -f "$ARCHIVO" ] || { echo "ERROR=no existe $ARCHIVO"; exit 1; }
  mkdir -p "$BACKUP_DIR"
  marca="$(date -u +%Y%m%dT%H%M%SZ)"
  destino="$BACKUP_DIR/pedidos_${marca}.json"
  cp "$ARCHIVO" "$destino"
  h="$(hash_de "$destino")"
  echo "$h  pedidos_${marca}.json" > "$destino.sha256"
  # Retención: conserva solo los N respaldos más recientes (control de costo de almacenamiento)
  ls -1 "$BACKUP_DIR"/pedidos_*.json 2>/dev/null | sort | head -n -"$RETENCION" 2>/dev/null | while read -r viejo; do
    rm -f "$viejo" "$viejo.sha256"
  done
  echo "BACKUP_FILE=$(basename "$destino")"
  echo "VERSION=$(version_de "$destino")"
  echo "SHA256=$h"
}

cmd_tamper() {
  # SOLO PARA PRUEBAS: simula una pérdida/modificación de la copia de trabajo.
  [ -f "$ARCHIVO" ] || { echo "ERROR=no existe $ARCHIVO"; exit 1; }
  # El archivo de datos se monta SOLO (no su carpeta), asi que no se puede crear un
  # temporal junto a el: se edita en /tmp (escribible) y se copia el contenido de vuelta.
  tmp="$(mktemp)"
  sed 's/"version": *"[^"]*"/"version": "ALTERADO"/; s/"Entregado"/"PERDIDO"/' "$ARCHIVO" > "$tmp"
  cat "$tmp" > "$ARCHIVO"
  rm -f "$tmp"
  echo "ALTERADO=si"
  echo "VERSION=$(version_de "$ARCHIVO")"
  echo "SHA256=$(hash_de "$ARCHIVO")"
}

cmd_restore() {
  if [ "${1:-}" ]; then
    origen="$BACKUP_DIR/$1"
  else
    origen="$(ls -1 "$BACKUP_DIR"/pedidos_*.json 2>/dev/null | sort | tail -n1 || true)"
  fi
  [ -n "${origen:-}" ] && [ -f "$origen" ] || { echo "ERROR=no hay respaldo disponible en $BACKUP_DIR"; exit 1; }
  # 1) Verificar la integridad del respaldo ANTES de usarlo
  if [ -f "$origen.sha256" ]; then
    esperado="$(cut -d' ' -f1 "$origen.sha256")"
    real="$(hash_de "$origen")"
    [ "$esperado" = "$real" ] || { echo "ERROR=el respaldo está corrupto (hash distinto)"; exit 1; }
  else
    echo "AVISO=el respaldo no tiene archivo .sha256; no se pudo verificar integridad"
  fi
  # 2) El archivo de datos se monta SOLO (no su carpeta), asi que no se puede renombrar
  #    un temporal encima. Se valida en /tmp y se vuelca el contenido sobre el archivo
  #    montado de una sola escritura (cat), que es lo mas atomico posible en este montaje.
  tmp="$(mktemp)"
  cp "$origen" "$tmp"
  cat "$tmp" > "$ARCHIVO"
  rm -f "$tmp"
  echo "RESTORED_FROM=$(basename "$origen")"
  echo "VERSION=$(version_de "$ARCHIVO")"
  echo "SHA256=$(hash_de "$ARCHIVO")"
}

cmd_list() { ls -1 "$BACKUP_DIR"/pedidos_*.json 2>/dev/null | sort || echo "(sin respaldos)"; }

cmd_auto() {
  intervalo="${BACKUP_INTERVAL_SECONDS:-300}"
  echo "Respaldo automático cada ${intervalo}s (conserva ${RETENCION})."
  while true; do cmd_backup || echo "AVISO=falló el respaldo, se reintenta"; sleep "$intervalo"; done
}

case "${1:-}" in
  status)  cmd_status ;;
  backup)  cmd_backup ;;
  tamper)  cmd_tamper ;;
  restore) shift; cmd_restore "${1:-}" ;;
  list)    cmd_list ;;
  auto)    cmd_auto ;;
  *) echo "Uso: ops.sh {status|backup|tamper|restore [archivo]|list|auto}"; exit 2 ;;
esac
