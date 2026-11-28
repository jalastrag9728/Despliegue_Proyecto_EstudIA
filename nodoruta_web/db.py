"""Capa de persistencia en Amazon RDS PostgreSQL con migración automática desde pedidos.json."""
import datetime
import hashlib
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_PATH = BASE_DIR / "pedidos.json"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS estado_sistema (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version VARCHAR(50) NOT NULL,
    datos_validos BOOLEAN NOT NULL DEFAULT TRUE,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pedido (
    id VARCHAR(20) PRIMARY KEY,
    zona VARCHAR(50) NOT NULL,
    estado VARCHAR(50) NOT NULL,
    prioridad VARCHAR(30) NOT NULL,
    vehiculo VARCHAR(80) NOT NULL,
    ventana VARCHAR(50) NOT NULL,
    progreso SMALLINT NOT NULL,
    novedad TEXT NOT NULL,
    orden INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS respaldo_snapshot (
    id SERIAL PRIMARY KEY,
    nombre_archivo VARCHAR(100) UNIQUE NOT NULL,
    version VARCHAR(50) NOT NULL,
    contenido JSONB NOT NULL,
    sha256 CHAR(64) NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def usar_postgres() -> bool:
    """Devuelve True si la aplicación está configurada para conectarse a RDS PostgreSQL."""
    return bool(os.environ.get("DB_HOST", "").strip() or os.environ.get("DATABASE_URL", "").strip())


def _obtener_conexion():
    """Abre una conexión a PostgreSQL usando DATABASE_URL o variables DB_*."""
    import psycopg

    db_url = os.environ.get("DATABASE_URL", "").strip()
    timeout = int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))
    if db_url:
        return psycopg.connect(db_url, connect_timeout=timeout)

    host = os.environ.get("DB_HOST", "").strip()
    port = int(os.environ.get("DB_PORT", "5432"))
    dbname = os.environ.get("DB_NAME", "nodoruta").strip()
    user = os.environ.get("DB_USER", "nodoruta_admin").strip()
    password = os.environ.get("DB_PASSWORD", "").strip()
    sslmode = os.environ.get("DB_SSLMODE", "prefer").strip()

    return psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
        sslmode=sslmode,
        connect_timeout=timeout,
    )


def _leer_semilla(ruta_semilla: Path | None = None) -> dict:
    ruta = ruta_semilla or Path(os.environ.get("SEED_PATH", str(SEED_PATH)))
    data = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("pedidos"), list) or not data.get("version"):
        raise ValueError("El archivo semilla pedidos.json no tiene el formato esperado")
    return data


def inicializar_y_migrar_semilla(ruta_semilla: Path | None = None, forzar: bool = False) -> dict:
    """Crea las tablas en RDS PostgreSQL y migra pedidos.json si la base de datos está vacía."""
    semilla = _leer_semilla(ruta_semilla)
    with _obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute("SELECT COUNT(*) FROM pedido;")
            total_pedidos = cur.fetchone()[0]

            if total_pedidos == 0 or forzar:
                cur.execute("DELETE FROM pedido;")
                cur.execute(
                    """
                    INSERT INTO estado_sistema (id, version, datos_validos, actualizado_en)
                    VALUES (1, %s, TRUE, NOW())
                    ON CONFLICT (id) DO UPDATE
                    SET version = EXCLUDED.version,
                        datos_validos = TRUE,
                        actualizado_en = NOW();
                    """,
                    (semilla["version"],),
                )
                for indice, ped in enumerate(semilla["pedidos"]):
                    cur.execute(
                        """
                        INSERT INTO pedido (id, zona, estado, prioridad, vehiculo, ventana, progreso, novedad, orden)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            ped["id"],
                            ped["zona"],
                            ped["estado"],
                            ped["prioridad"],
                            ped["vehiculo"],
                            ped["ventana"],
                            int(ped["progreso"]),
                            ped["novedad"],
                            indice,
                        ),
                    )
        conn.commit()
    return {"migrado": total_pedidos == 0 or forzar, "version": semilla["version"], "pedidos": len(semilla["pedidos"])}


def cargar_datos_postgres() -> dict:
    """Lee la versión y la lista de pedidos desde RDS PostgreSQL.

    Si las tablas aún no existen, ejecuta automáticamente la migración inicial desde pedidos.json.
    Si datos_validos es FALSE (prueba I05 de datos corruptos) o no hay registros, lanza ValueError
    para que las vistas devuelvan HTTP 503 {"estado": "error_datos"}.
    """
    with _obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'estado_sistema');"
            )
            existe_tabla = cur.fetchone()[0]

    if not existe_tabla:
        inicializar_y_migrar_semilla()

    with _obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version, datos_validos FROM estado_sistema WHERE id = 1;")
            fila_estado = cur.fetchone()
            if not fila_estado:
                raise ValueError("No existe registro de estado_sistema en RDS PostgreSQL")

            version, datos_validos = fila_estado
            if not datos_validos or not version:
                raise ValueError("Los datos en RDS PostgreSQL están marcados como inválidos/corruptos")

            cur.execute(
                """
                SELECT id, zona, estado, prioridad, vehiculo, ventana, progreso, novedad
                FROM pedido
                ORDER BY orden ASC, id ASC;
                """
            )
            filas = cur.fetchall()
            if not filas:
                raise ValueError("La tabla de pedidos en RDS PostgreSQL está vacía")

            pedidos = [
                {
                    "id": r[0],
                    "zona": r[1],
                    "estado": r[2],
                    "prioridad": r[3],
                    "vehiculo": r[4],
                    "ventana": r[5],
                    "progreso": int(r[6]),
                    "novedad": r[7],
                }
                for r in filas
            ]

            return {"version": version, "pedidos": pedidos}


def respaldar_postgres() -> dict:
    """Crea un snapshot en la tabla respaldo_snapshot (y devuelve nombre, versión y hash SHA-256)."""
    datos = cargar_datos_postgres()
    contenido_bytes = json.dumps(datos, ensure_ascii=False, sort_keys=True).encode("utf-8")
    huella = hashlib.sha256(contenido_bytes).hexdigest()
    marca = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    nombre = f"rds_{marca}.json"

    with _obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO respaldo_snapshot (nombre_archivo, version, contenido, sha256)
                VALUES (%s, %s, %s::jsonb, %s);
                """,
                (nombre, datos["version"], json.dumps(datos, ensure_ascii=False), huella),
            )
        conn.commit()

    return {"respaldo": nombre, "version": datos["version"], "sha256": huella}


def simular_error_postgres() -> None:
    """Simula corrupción de datos en RDS PostgreSQL (datos_validos = FALSE) para que /health devuelva 503."""
    with _obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute(
                """
                UPDATE estado_sistema
                SET datos_validos = FALSE,
                    version = 'CORRUPTO-503',
                    actualizado_en = NOW()
                WHERE id = 1;
                """
            )
        conn.commit()


def restaurar_postgres(nombre_archivo: str | None = None) -> dict:
    """Verifica la huella SHA-256 del respaldo en RDS y restaura estado_sistema y pedido."""
    with _obtener_conexion() as conn:
        with conn.cursor() as cur:
            if nombre_archivo:
                cur.execute(
                    """
                    SELECT nombre_archivo, version, contenido, sha256
                    FROM respaldo_snapshot
                    WHERE nombre_archivo = %s;
                    """,
                    (nombre_archivo,),
                )
            else:
                cur.execute(
                    """
                    SELECT nombre_archivo, version, contenido, sha256
                    FROM respaldo_snapshot
                    ORDER BY creado_en DESC, id DESC
                    LIMIT 1;
                    """
                )
            fila = cur.fetchone()
            if not fila:
                raise ValueError("No se encontró el respaldo solicitado en RDS PostgreSQL")

            nombre, version, contenido, sha256_esperado = fila
            if isinstance(contenido, str):
                datos = json.loads(contenido)
            else:
                datos = contenido

            calculado = hashlib.sha256(
                json.dumps(datos, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ).hexdigest()
            if calculado != sha256_esperado.strip():
                raise ValueError("El respaldo en RDS no coincide con su huella SHA-256 de integridad")

            cur.execute("DELETE FROM pedido;")
            cur.execute(
                """
                INSERT INTO estado_sistema (id, version, datos_validos, actualizado_en)
                VALUES (1, %s, TRUE, NOW())
                ON CONFLICT (id) DO UPDATE
                SET version = EXCLUDED.version,
                    datos_validos = TRUE,
                    actualizado_en = NOW();
                """,
                (datos["version"],),
            )
            for indice, ped in enumerate(datos["pedidos"]):
                cur.execute(
                    """
                    INSERT INTO pedido (id, zona, estado, prioridad, vehiculo, ventana, progreso, novedad, orden)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        ped["id"],
                        ped["zona"],
                        ped["estado"],
                        ped["prioridad"],
                        ped["vehiculo"],
                        ped["ventana"],
                        int(ped["progreso"]),
                        ped["novedad"],
                        indice,
                    ),
                )
        conn.commit()

    return {"restaurado_desde": nombre, "version": version, "sha256": sha256_esperado.strip()}
