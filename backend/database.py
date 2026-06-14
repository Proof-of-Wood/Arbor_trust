"""
ArborTrust - database.py
========================
Gestión de la base de datos SQLite y carga inicial de datos CSV.

Crea las tablas relacionales que reemplazan la dispersión de CSVs,
manteniendo los CSVs como fuente de verdad para importación.
"""

import sqlite3
import pandas as pd
from pathlib import Path

# ──────────────────────────────────────────────
# RUTAS
# ──────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parents[1]
DB_PATH    = ROOT_DIR / "backend" / "arbortrust.db"
DATA_DIR   = ROOT_DIR / "data" / "sample"
PROC_DIR   = ROOT_DIR / "data" / "processed"


# ──────────────────────────────────────────────
# DDL: Definición de tablas
# ──────────────────────────────────────────────
DDL_STATEMENTS = [
    # ── Punto 1: Planificación (datos del censo forestal) ──────────────
    """
    CREATE TABLE IF NOT EXISTS arboles (
        arbol_id             TEXT PRIMARY KEY,
        titulo_habilitante_id TEXT NOT NULL,
        titular              TEXT NOT NULL,
        parcela_corta        TEXT NOT NULL,
        especie              TEXT NOT NULL,
        volumen_censado      REAL NOT NULL,
        estado               TEXT DEFAULT 'Autorizado',
        condicion            TEXT DEFAULT 'Aprovechable',
        created_at           TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Punto 1: Balance de extracción por parcela/especie ─────────────
    """
    CREATE TABLE IF NOT EXISTS balances_extraccion (
        balance_id            TEXT PRIMARY KEY,
        titulo_habilitante_id TEXT NOT NULL,
        parcela_corta         TEXT NOT NULL,
        especie               TEXT NOT NULL,
        volumen_autorizado    REAL NOT NULL,
        volumen_movilizado    REAL NOT NULL DEFAULT 0,
        saldo_disponible      REAL NOT NULL,
        estado_saldo          TEXT DEFAULT 'Positivo',
        updated_at            TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Punto 2: Aprovechamiento (Tala / Trozado / Despacho) ───────────
    """
    CREATE TABLE IF NOT EXISTS operaciones (
        operacion_id    TEXT PRIMARY KEY,
        tipo_operacion  TEXT NOT NULL CHECK(tipo_operacion IN ('Tala','Trozado','Despacho','Transformacion')),
        punto_cadena    INTEGER NOT NULL CHECK(punto_cadena IN (2,3,4)),
        arbol_id        TEXT REFERENCES arboles(arbol_id),
        troza_id        TEXT,
        lote_id         TEXT,
        parcela_corta   TEXT NOT NULL,
        especie         TEXT NOT NULL,
        volumen         REAL NOT NULL,
        numero_gtf      TEXT,
        actor_id        TEXT NOT NULL,
        fecha           TEXT NOT NULL,
        observacion     TEXT,
        estado_validacion TEXT DEFAULT 'Pendiente',
        created_at      TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (lote_id) REFERENCES lotes(lote_id)
    )
    """,

    # ── Punto 3: Transporte (lotes comerciales con GTF) ────────────────
    """
    CREATE TABLE IF NOT EXISTS lotes (
        lote_id               TEXT PRIMARY KEY,
        numero_gtf            TEXT NOT NULL,
        titulo_habilitante_id TEXT NOT NULL,
        titular               TEXT NOT NULL,
        parcela_corta         TEXT NOT NULL,
        especie               TEXT NOT NULL,
        volumen_total         REAL NOT NULL,
        punto_origen          TEXT DEFAULT 'Bosque',
        punto_destino         TEXT DEFAULT 'CTP',
        estado_validacion     TEXT DEFAULT 'Pendiente',
        color_semaforo        TEXT DEFAULT 'Amarillo',
        mensaje_validacion    TEXT,
        fecha_creacion        TEXT DEFAULT (datetime('now')),
        created_at            TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Punto 4: Transformación Primaria (Centro de Transformación) ─────
    """
    CREATE TABLE IF NOT EXISTS transformaciones (
        transformacion_id  TEXT PRIMARY KEY,
        lote_id            TEXT NOT NULL REFERENCES lotes(lote_id),
        operador_ctp       TEXT NOT NULL,
        tipo_producto      TEXT NOT NULL,           -- 'madera_aserrada', 'semielaborado'
        volumen_ingreso    REAL NOT NULL,
        volumen_salida     REAL,
        numero_gtf_salida  TEXT,
        fecha_ingreso      TEXT NOT NULL,
        fecha_salida       TEXT,
        estado             TEXT DEFAULT 'En_proceso',
        observacion        TEXT,
        created_at         TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Sistema de Pasaportes Digitales ────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS pasaportes (
        pasaporte_id    TEXT PRIMARY KEY,
        lote_id         TEXT NOT NULL REFERENCES lotes(lote_id),
        numero_gtf      TEXT NOT NULL,
        estado          TEXT DEFAULT 'Activo',
        qr_url          TEXT,
        hash_integridad TEXT NOT NULL,
        fecha_generacion TEXT DEFAULT (datetime('now')),
        created_at      TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── MÓDULO 2: Bitácora de Integridad (reemplaza blockchain) ────────
    """
    CREATE TABLE IF NOT EXISTS logs_auditoria (
        evento_id       TEXT PRIMARY KEY,
        timestamp       TEXT NOT NULL DEFAULT (datetime('now','utc')),
        actor_id        TEXT NOT NULL,
        tipo_actor      TEXT NOT NULL CHECK(tipo_actor IN ('Titular','Regente','ARFFS','SERFOR','OSINFOR','Transportista','Operador_CTP','Sistema','Comprador')),
        accion          TEXT NOT NULL,
        punto_cadena    INTEGER NOT NULL CHECK(punto_cadena IN (1,2,3,4)),
        entidad_tipo    TEXT NOT NULL,   -- 'Operacion', 'Lote', 'Transformacion', 'Pasaporte'
        entidad_id      TEXT NOT NULL,
        hash_anterior   TEXT,            -- NULL solo para el primer evento
        hash_actual     TEXT NOT NULL,   -- SHA-256 del bloque actual
        payload_json    TEXT NOT NULL,   -- Datos del evento serializados
        ip_origen       TEXT,
        es_valido       INTEGER DEFAULT 1  -- 1=OK, 0=cadena rota
    )
    """,

    # ── MÓDULO 3: Resultados de Validación (Semáforo) ──────────────────
    """
    CREATE TABLE IF NOT EXISTS validaciones (
        validacion_id   TEXT PRIMARY KEY,
        lote_id         TEXT NOT NULL REFERENCES lotes(lote_id),
        regla           TEXT NOT NULL,
        resultado       TEXT NOT NULL CHECK(resultado IN ('Aprobado','Rechazado','Advertencia')),
        severidad       TEXT NOT NULL CHECK(severidad IN ('Baja','Media','Alta','Critica')),
        color_semaforo  TEXT NOT NULL CHECK(color_semaforo IN ('Verde','Amarillo','Rojo')),
        mensaje         TEXT NOT NULL,
        detalle_json    TEXT,            -- Datos adicionales de la falla
        fecha_validacion TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Índices para rendimiento ────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_operaciones_lote     ON operaciones(lote_id)",
    "CREATE INDEX IF NOT EXISTS idx_operaciones_arbol    ON operaciones(arbol_id)",
    "CREATE INDEX IF NOT EXISTS idx_logs_entidad         ON logs_auditoria(entidad_id)",
    "CREATE INDEX IF NOT EXISTS idx_logs_timestamp       ON logs_auditoria(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_validaciones_lote    ON validaciones(lote_id)",
    "CREATE INDEX IF NOT EXISTS idx_validaciones_color   ON validaciones(color_semaforo)",
]


# ──────────────────────────────────────────────
# FUNCIONES DE CONEXIÓN
# ──────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión SQLite con row_factory activado."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row          # rows como dict-like objects
    conn.execute("PRAGMA journal_mode=WAL") # Write-Ahead Logging para concurrencia
    conn.execute("PRAGMA foreign_keys=ON")  # Enforza claves foráneas
    return conn


def init_db() -> None:
    """Crea las tablas si no existen."""
    conn = get_connection()
    try:
        for stmt in DDL_STATEMENTS:
            conn.execute(stmt)
        conn.commit()
        print("[DB] Tablas creadas/verificadas correctamente.")
    finally:
        conn.close()


# ──────────────────────────────────────────────
# CARGA INICIAL DE DATOS CSV → SQLite
# ──────────────────────────────────────────────

def seed_from_csv() -> None:
    """
    Importa los datos de los CSVs de muestra a SQLite.
    Es idempotente: usa INSERT OR IGNORE para no duplicar.
    """
    conn = get_connection()
    try:
        # 1. Árboles (censo forestal)
        arboles_path = DATA_DIR / "arboles_sample.csv"
        if arboles_path.exists():
            df = pd.read_csv(arboles_path, encoding="utf-8-sig")
            df["arbol_id"] = df["arbol_id"].astype(str)
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR IGNORE INTO arboles
                    (arbol_id, titulo_habilitante_id, titular, parcela_corta,
                     especie, volumen_censado, estado, condicion)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (str(row["arbol_id"]), row["titulo_habilitante_id"],
                      row["titular"], row["parcela_corta"], row["especie"],
                      float(row["volumen_censado"]), row["estado"], row["condicion"]))
            print(f"[SEED] arboles: {len(df)} registros importados.")

        # 2. Balances de extracción
        balances_path = DATA_DIR / "balances_sample.csv"
        if balances_path.exists():
            df = pd.read_csv(balances_path, encoding="utf-8-sig")
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR IGNORE INTO balances_extraccion
                    (balance_id, titulo_habilitante_id, parcela_corta, especie,
                     volumen_autorizado, volumen_movilizado, saldo_disponible, estado_saldo)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (row["balance_id"], row["titulo_habilitante_id"],
                      row["parcela_corta"], row["especie"],
                      float(row["volumen_autorizado"]), float(row["volumen_movilizado"]),
                      float(row["saldo_disponible"]), row["estado_saldo"]))
            print(f"[SEED] balances_extraccion: {len(df)} registros importados.")

        # 3. Lotes (transporte primario)
        lotes_path = DATA_DIR / "lotes_sample.csv"
        if lotes_path.exists():
            df = pd.read_csv(lotes_path, encoding="utf-8-sig")
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR IGNORE INTO lotes
                    (lote_id, numero_gtf, titulo_habilitante_id, titular,
                     parcela_corta, especie, volumen_total, estado_validacion)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (row["lote_id"], row["numero_gtf"], row.get("titulo_habilitante_id","TH-001"),
                      row.get("titular","PRODUCTOR DEMO"), row["parcela_corta"],
                      row["especie"], float(row["volumen_total"]), row["estado_validacion"]))
            print(f"[SEED] lotes: {len(df)} registros importados.")

        # 4. Operaciones (tala/trozado/despacho)
        ops_path = DATA_DIR / "operaciones_sample.csv"
        if ops_path.exists():
            df = pd.read_csv(ops_path, encoding="utf-8-sig")
            tipo_a_punto = {"Tala": 2, "Trozado": 2, "Despacho": 3, "Transformacion": 4}
            for _, row in df.iterrows():
                punto = tipo_a_punto.get(row["tipo_operacion"], 2)
                conn.execute("""
                    INSERT OR IGNORE INTO operaciones
                    (operacion_id, tipo_operacion, punto_cadena, arbol_id, troza_id,
                     parcela_corta, especie, volumen, numero_gtf, actor_id, fecha)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (row["operacion_id"], row["tipo_operacion"], punto,
                      str(row["arbol_id"]),
                      str(row["troza_id"]) if pd.notna(row["troza_id"]) else None,
                      row["parcela_corta"], row["especie"], float(row["volumen"]),
                      str(row["numero_gtf"]) if pd.notna(row["numero_gtf"]) else None,
                      "ACTOR-SEED", row["fecha"]))
            print(f"[SEED] operaciones: {len(df)} registros importados.")

        conn.commit()
        print("[SEED] Carga inicial completada.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    seed_from_csv()
