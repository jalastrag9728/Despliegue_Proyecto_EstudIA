"""CLI para migrar, respaldar, simular error (503) y restaurar datos en Amazon RDS PostgreSQL."""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nodoruta_web import db  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Migrar pedidos.json a RDS PostgreSQL y operar respaldos/recuperación (Prueba I05 en nube)."
    )
    parser.add_argument(
        "accion",
        choices=["preparar", "respaldar", "simular-error", "restaurar", "estado"],
        help="Acción a ejecutar contra RDS PostgreSQL",
    )
    parser.add_argument(
        "--respaldo",
        help="Nombre del respaldo en la tabla respaldo_snapshot (opcional; por defecto usa el más reciente)",
    )
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="En 'preparar', sobrescribe las tablas con la semilla pedidos.json aunque ya tengan datos",
    )
    parser.add_argument(
        "--reintentos",
        type=int,
        default=15,
        help="Número de reintentos al conectar con RDS PostgreSQL durante el arranque (por defecto 15)",
    )
    args = parser.parse_args()

    try:
        if not db.usar_postgres():
            raise ValueError(
                "No se detectó configuración de RDS PostgreSQL. Defina DB_HOST (o DATABASE_URL) antes de ejecutar."
            )

        if args.accion == "preparar":
            ultimo_error = None
            for intento in range(1, max(1, args.reintentos) + 1):
                try:
                    res = db.inicializar_y_migrar_semilla(ROOT / "pedidos.json", forzar=args.forzar)
                    print(
                        f"RDS PostgreSQL inicializada correctamente "
                        f"(version={res['version']}, pedidos={res['pedidos']})."
                    )
                    return
                except Exception as exc:
                    ultimo_error = exc
                    if intento < args.reintentos:
                        print(
                            f"[Intento {intento}/{args.reintentos}] Esperando disponibilidad de RDS PostgreSQL: {exc}",
                            flush=True,
                        )
                        time.sleep(3)
            raise RuntimeError(f"No se pudo conectar a RDS tras {args.reintentos} intentos: {ultimo_error}")
        elif args.accion == "estado":
            datos = db.cargar_datos_postgres()
            print(f"RDS PostgreSQL OK | version={datos['version']} | pedidos={len(datos['pedidos'])}")
        elif args.accion == "respaldar":
            res = db.respaldar_postgres()
            print(f"Respaldo en RDS creado: {res['respaldo']} | version={res['version']} | sha256={res['sha256']}")
        elif args.accion == "simular-error":
            db.simular_error_postgres()
            print("Datos marcados como corruptos en RDS PostgreSQL. /health y /pedidos devolverán HTTP 503.")
        elif args.accion == "restaurar":
            res = db.restaurar_postgres(args.respaldo)
            print(
                f"Datos restaurados en RDS desde {res['restaurado_desde']} "
                f"(version={res['version']}, sha256={res['sha256']})."
            )
    except Exception as exc:
        parser.exit(1, f"No se realizó la operación en RDS PostgreSQL: {exc}\n")


if __name__ == "__main__":
    main()
