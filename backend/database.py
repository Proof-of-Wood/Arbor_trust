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

    # ── Tabla de Control de Carga de Archivos (Idempotencia y Concurrencia) ──
    """
    CREATE TABLE IF NOT EXISTS registro_cargas (
        id TEXT PRIMARY KEY,
        file_hash TEXT UNIQUE,
        tipo_archivo TEXT NOT NULL,
        estado TEXT NOT NULL CHECK(estado IN ('EN_COLA', 'PROCESANDO', 'COMPLETADO', 'FALLIDO')),
        resultado TEXT,
        fecha_creacion TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Índices Únicos para Evitar Duplicidades de Negocio Concurrentes ──
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_arboles_unicidad ON arboles(arbol_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_tala_unica ON operaciones(arbol_id) WHERE tipo_operacion = 'Tala'",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_troza_unica ON operaciones(troza_id, tipo_operacion) WHERE troza_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_lote_unica ON operaciones(lote_id, tipo_operacion) WHERE lote_id IS NOT NULL AND troza_id IS NULL AND arbol_id IS NULL",
]


# ──────────────────────────────────────────────
# FUNCIONES DE CONEXIÓN
# ──────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión SQLite con row_factory y WAL activado."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row          # rows como dict-like objects
    conn.execute("PRAGMA journal_mode=WAL;") # Write-Ahead Logging para concurrencia
    conn.execute("PRAGMA busy_timeout = 30000;") # Configura el timeout de bloqueo a 30s
    conn.execute("PRAGMA foreign_keys=ON;")  # Enforza claves foráneas
    return conn


# ──────────────────────────────────────────────
# LOGICA DE AGENTE WORKER (PROCESAMIENTO ASÍNCRONO)
# ──────────────────────────────────────────────

ALLOWED_SPECIES = {'Shihuahuaco', 'Cumala', 'Cedro', 'Tornillo', 'Lupuna', 'Caoba'}

def procesar_archivo_background(job_id: str, file_path: str, tipo_archivo: str) -> None:
    """
    Parsea y procesa el archivo subido en segundo plano.
    Utiliza transacciones explícitas, validaciones de negocio e inserciones masivas.
    """
    import json
    import os
    from datetime import datetime
    
    conn = get_connection()
    try:
        # 1. Cambiar estado a PROCESANDO
        conn.execute("UPDATE registro_cargas SET estado = 'PROCESANDO' WHERE id = ?", (job_id,))
        conn.commit()
        
        # 2. Leer archivo
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado en la ruta: {file_path}")
            
        df = pd.read_csv(file_path, encoding="utf-8-sig")
        df = df.fillna("")
        records = df.to_dict(orient="records")
        
        # 3. Validar y construir tuplas
        data_to_insert = []
        
        if tipo_archivo == "censo":
            for r in records:
                arbol_id = str(r["arbol_id"]).strip()
                vol = float(r["volumen_censado"])
                especie = str(r["especie"]).strip()
                
                if vol < 0:
                    raise ValueError(f"Volumen no puede ser negativo: {vol}")
                if especie not in ALLOWED_SPECIES:
                    raise ValueError(f"Especie '{especie}' no autorizada. Especies permitidas: {list(ALLOWED_SPECIES)}")
                    
                data_to_insert.append((
                    arbol_id,
                    str(r["titulo_habilitante_id"]).strip(),
                    str(r["titular"]).strip(),
                    str(r["parcela_corta"]).strip(),
                    especie,
                    vol,
                    str(r.get("estado", "Autorizado")).strip(),
                    str(r.get("condicion", "Aprovechable")).strip()
                ))
                
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO arboles
                (arbol_id, titulo_habilitante_id, titular, parcela_corta, especie, volumen_censado, estado, condicion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)
            
        elif tipo_archivo == "balances":
            for r in records:
                balance_id = str(r["balance_id"]).strip()
                th_id = str(r["titulo_habilitante_id"]).strip()
                parcela = str(r["parcela_corta"]).strip()
                especie = str(r["especie"]).strip()
                vol_aut = float(r["volumen_autorizado"])
                vol_mov = float(r.get("volumen_movilizado", 0.0))
                saldo = float(r.get("saldo_disponible", vol_aut - vol_mov))
                estado_saldo = str(r.get("estado_saldo", "Positivo")).strip()
                
                if vol_aut < 0 or vol_mov < 0:
                    raise ValueError("Los volúmenes de balance no pueden ser negativos")
                if especie not in ALLOWED_SPECIES:
                    raise ValueError(f"Especie '{especie}' no autorizada")
                    
                data_to_insert.append((
                    balance_id, th_id, parcela, especie, vol_aut, vol_mov, saldo, estado_saldo
                ))
                
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO balances_extraccion
                (balance_id, titulo_habilitante_id, parcela_corta, especie, volumen_autorizado, volumen_movilizado, saldo_disponible, estado_saldo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)
            
        elif tipo_archivo == "lotes":
            for r in records:
                lote_id = str(r["lote_id"]).strip()
                num_gtf = str(r["numero_gtf"]).strip()
                th_id = str(r["titulo_habilitante_id"]).strip()
                titular = str(r.get("titular", "PRODUCTOR DEMO")).strip()
                parcela = str(r["parcela_corta"]).strip()
                especie = str(r["especie"]).strip()
                vol = float(r["volumen_total"])
                estado_val = str(r.get("estado_validacion", "Pendiente")).strip()
                mensaje = r.get("mensaje", None)
                if pd.notna(mensaje):
                    mensaje = str(mensaje).strip()
                else:
                    mensaje = None
                
                if vol < 0:
                    raise ValueError(f"Volumen de lote no puede ser negativo: {vol}")
                if especie not in ALLOWED_SPECIES:
                    raise ValueError(f"Especie '{especie}' no autorizada")
                    
                data_to_insert.append((
                    lote_id, num_gtf, th_id, titular, parcela, especie, vol, estado_val, mensaje
                ))
                
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO lotes
                (lote_id, numero_gtf, titulo_habilitante_id, titular, parcela_corta, especie, volumen_total, estado_validacion, mensaje_validacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)
            
        elif tipo_archivo == "operaciones":
            from engine.hashing import registrar_evento, Acciones
            from engine.validation import validar_lote
            
            lotes_a_validar = set()
            
            new_records = []
            for r in records:
                op_id = str(r["operacion_id"]).strip()
                exists = conn.execute("SELECT 1 FROM operaciones WHERE operacion_id = ?", (op_id,)).fetchone()
                if not exists:
                    new_records.append(r)
                    
            if not new_records:
                resultado_json = json.dumps({"registros_procesados": 0, "mensaje": "Todos los registros ya existían en la base de datos.", "fecha_finalizacion": datetime.now().isoformat()})
                conn.execute("UPDATE registro_cargas SET estado = 'COMPLETADO', resultado = ? WHERE id = ?", (resultado_json, job_id))
                conn.commit()
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                return
                
            for r in new_records:
                op_id = str(r["operacion_id"]).strip()
                tipo_op = str(r["tipo_operacion"]).strip()
                arbol_id = r.get("arbol_id")
                if pd.notna(arbol_id) and arbol_id != "":
                    arbol_id = str(arbol_id).strip()
                else:
                    arbol_id = None
                
                troza_id = r.get("troza_id")
                if pd.notna(troza_id) and troza_id != "":
                    troza_id = str(troza_id).strip()
                else:
                    troza_id = None
                    
                lote_id = r.get("lote_id")
                if pd.notna(lote_id) and lote_id != "":
                    lote_id = str(lote_id).strip()
                    lotes_a_validar.add(lote_id)
                else:
                    lote_id = None
                    
                parcela = str(r["parcela_corta"]).strip()
                especie = str(r["especie"]).strip()
                volumen = float(r["volumen"])
                
                num_gtf = r.get("numero_gtf")
                if pd.notna(num_gtf) and num_gtf != "":
                    num_gtf = str(num_gtf).strip()
                else:
                    num_gtf = None
                    
                actor_id = str(r.get("actor_id", "ACTOR-LOAD")).strip()
                fecha = str(r["fecha"]).strip()
                obs = r.get("observacion")
                if pd.notna(obs):
                    obs = str(obs).strip()
                else:
                    obs = None
                
                # Validar
                if volumen < 0:
                    raise ValueError(f"Volumen de operación no puede ser negativo: {volumen}")
                if especie not in ALLOWED_SPECIES:
                    raise ValueError(f"Especie '{especie}' no autorizada")
                if tipo_op not in {'Tala', 'Trozado', 'Despacho', 'Transformacion'}:
                    raise ValueError(f"Tipo de operación inválido: {tipo_op}")
                
                punto_cadena = 2
                if tipo_op == "Despacho":
                    punto_cadena = 3
                elif tipo_op == "Transformacion":
                    punto_cadena = 4
                
                data_to_insert.append((
                    op_id, tipo_op, punto_cadena, arbol_id, troza_id, lote_id, parcela, especie, volumen, num_gtf, actor_id, fecha, obs
                ))
                
                # Actualización atómica de saldos (balances_extraccion)
                th_id = None
                if arbol_id:
                    res_arb = conn.execute("SELECT titulo_habilitante_id FROM arboles WHERE arbol_id = ?", (arbol_id,)).fetchone()
                    if res_arb:
                        th_id = res_arb["titulo_habilitante_id"]
                if not th_id and lote_id:
                    res_lote = conn.execute("SELECT titulo_habilitante_id FROM lotes WHERE lote_id = ?", (lote_id,)).fetchone()
                    if res_lote:
                        th_id = res_lote["titulo_habilitante_id"]
                if not th_id:
                    th_id = "TH-001"
                
                # Descontar volumen del balance de la especie/parcela
                conn.execute("""
                    UPDATE balances_extraccion
                    SET volumen_movilizado = volumen_movilizado + ?,
                        saldo_disponible = saldo_disponible - ?,
                        estado_saldo = CASE WHEN (saldo_disponible - ?) < 0 THEN 'Negativo' ELSE 'Positivo' END
                    WHERE titulo_habilitante_id = ? AND parcela_corta = ? AND especie = ?
                """, (volumen, volumen, volumen, th_id, parcela, especie))
                
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO operaciones
                (operacion_id, tipo_operacion, punto_cadena, arbol_id, troza_id, lote_id, parcela_corta, especie, volumen, numero_gtf, actor_id, fecha, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)
            
            # Commit atómico antes de validar e integrar eventos, para liberar el bloqueo de escritura
            conn.commit()
            
            # Registrar logs de auditoría para cada operación
            accion_map = {
                'Tala': Acciones.REGISTRAR_TALA,
                'Trozado': Acciones.REGISTRAR_TROZADO,
                'Despacho': Acciones.REGISTRAR_DESPACHO,
                'Transformacion': Acciones.INGRESO_CTP
            }
            
            for row in data_to_insert:
                op_id, tipo_op, punto_cadena, arbol_id, troza_id, lote_id, parcela, especie, volumen, num_gtf, actor_id, fecha, obs = row
                accion = accion_map.get(tipo_op, "OTRA_OPERACION")
                entidad_id = lote_id if lote_id else (arbol_id or "GENERAL")
                payload_dict = {
                    "tipo_operacion": tipo_op,
                    "punto_cadena": punto_cadena,
                    "arbol_id": arbol_id,
                    "troza_id": troza_id,
                    "lote_id": lote_id,
                    "parcela_corta": parcela,
                    "especie": especie,
                    "volumen": volumen,
                    "numero_gtf": num_gtf,
                    "actor_id": actor_id,
                    "fecha": fecha,
                    "observacion": obs
                }
                registrar_evento(
                    actor_id=actor_id,
                    tipo_actor="Titular" if tipo_op in ("Tala", "Trozado") else ("Transportista" if tipo_op == "Despacho" else "Operador_CTP"),
                    accion=accion,
                    punto_cadena=punto_cadena,
                    entidad_tipo="Operacion",
                    entidad_id=entidad_id,
                    payload=payload_dict
                )
            
            # Disparar validación de semáforo de riesgo para cada lote
            for lid in lotes_a_validar:
                validar_lote(lid)
                
        else:
            raise ValueError(f"Tipo de archivo desconocido: {tipo_archivo}")
            
        # Si no fue de operaciones, confirmamos aquí
        if tipo_archivo != "operaciones":
            conn.commit()
        
        # 4. Éxito: Guardar cambios, registrar COMPLETADO y borrar archivo temporal
        resultado_json = json.dumps({"registros_procesados": len(records), "fecha_finalizacion": datetime.now().isoformat()})
        conn.execute("UPDATE registro_cargas SET estado = 'COMPLETADO', resultado = ? WHERE id = ?", (resultado_json, job_id))
        conn.commit()
        
        # Eliminar archivo temporal si existe
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
                
    except Exception as e:
        # 5. Error: Rollback y marcar FALLIDO
        try:
            conn.rollback()
        except Exception:
            pass
            
        resultado_json = json.dumps({"error": str(e), "fecha_finalizacion": datetime.now().isoformat()})
        try:
            conn.execute("UPDATE registro_cargas SET estado = 'FALLIDO', resultado = ? WHERE id = ?", (resultado_json, job_id))
            conn.commit()
        except Exception:
            pass
            
        # Eliminar archivo temporal si existe
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    finally:
        conn.close()



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
            df = df.fillna("")
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
            df = df.fillna("")
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
            df = df.fillna("")
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
            df = df.fillna("")
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
                      str(row["troza_id"]) if (row["troza_id"] != "") else None,
                      row["parcela_corta"], row["especie"], float(row["volumen"]),
                      str(row["numero_gtf"]) if (row["numero_gtf"] != "") else None,
                      "ACTOR-SEED", row["fecha"]))
            print(f"[SEED] operaciones: {len(df)} registros importados.")

        conn.commit()
        print("[SEED] Carga inicial completada.")
    except Exception as e:
        print(f"[SEED] Error al sembrar base de datos: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    seed_from_csv()

