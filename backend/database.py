import sqlite3
import pandas as pd
from pathlib import Path
import re
from contextvars import ContextVar
from typing import Optional

pide_rol_var: ContextVar[Optional[str]] = ContextVar("pide_rol", default=None)
pide_ruc_var: ContextVar[Optional[str]] = ContextVar("pide_ruc", default=None)
pide_serfor_var: ContextVar[Optional[str]] = ContextVar("pide_serfor", default=None)
pide_dni_var: ContextVar[Optional[str]] = ContextVar("pide_dni", default=None)
pide_placa_var: ContextVar[Optional[str]] = ContextVar("pide_placa", default=None)


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
    # ── Punto 1: Planificación (datos del censo forestal normalized) ──────────────
    """
    CREATE TABLE IF NOT EXISTS titulares (
        ruc_dni TEXT PRIMARY KEY,
        nombre TEXT NOT NULL,
        direccion TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS titulos_habilitantes (
        id_titulo TEXT PRIMARY KEY,
        id_titular TEXT NOT NULL,
        nombre_concesion TEXT NOT NULL,
        ubicacion_geografica TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (id_titular) REFERENCES titulares(ruc_dni) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS planes_aprovechamiento (
        id_plan TEXT PRIMARY KEY,
        id_titulo TEXT NOT NULL,
        version INTEGER NOT NULL,
        fecha_aprobacion TEXT NOT NULL,
        estado TEXT NOT NULL CHECK(estado IN ('Aprobado', 'Actualizado', 'Vencido')),
        documento_pdf_hash TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (id_titulo) REFERENCES titulos_habilitantes(id_titulo) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS censo_forestal (
        id_arbol TEXT PRIMARY KEY,
        id_plan TEXT NOT NULL,
        id_especie TEXT NOT NULL,
        volumen_autorizado REAL NOT NULL,
        estado TEXT DEFAULT 'Autorizado',
        condicion TEXT DEFAULT 'Aprovechable',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (id_plan) REFERENCES planes_aprovechamiento(id_plan) ON DELETE CASCADE
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
        id_arbol        TEXT,
        troza_id        TEXT,
        lote_id         TEXT,
        parcela_corta   TEXT NOT NULL,
        especie         TEXT NOT NULL,
        volumen         REAL NOT NULL,
        numero_gtf      TEXT,
        actor_id        TEXT,
        ruc_institucion TEXT,
        registro_serfor TEXT,
        dni_chofer      TEXT,
        placa_vehiculo  TEXT,
        id_titular      TEXT,
        fecha           TEXT NOT NULL,
        observacion     TEXT,
        estado_validacion TEXT DEFAULT 'Pendiente',
        created_at      TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (id_arbol) REFERENCES censo_forestal(id_arbol) ON DELETE SET NULL,
        FOREIGN KEY (lote_id) REFERENCES lotes(lote_id) ON DELETE SET NULL,
        FOREIGN KEY (id_titular) REFERENCES titulares(ruc_dni) ON DELETE SET NULL
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
        tipo_producto      TEXT NOT NULL,
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
        entidad_tipo    TEXT NOT NULL,
        entidad_id      TEXT NOT NULL,
        hash_anterior   TEXT,
        hash_actual     TEXT NOT NULL,
        payload_json    TEXT NOT NULL,
        ip_origen       TEXT,
        es_valido       INTEGER DEFAULT 1
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
        detalle_json    TEXT,
        fecha_validacion TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── Índices para rendimiento ────────────────────────────────────────
    "CREATE INDEX IF NOT EXISTS idx_operaciones_lote     ON operaciones(lote_id)",
    "CREATE INDEX IF NOT EXISTS idx_operaciones_arbol    ON operaciones(id_arbol)",
    "CREATE INDEX IF NOT EXISTS idx_logs_entidad         ON logs_auditoria(entidad_id)",
    "CREATE INDEX IF NOT EXISTS idx_logs_timestamp       ON logs_auditoria(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_validaciones_lote    ON validaciones(lote_id)",
    "CREATE INDEX IF NOT EXISTS idx_validaciones_color   ON validaciones(color_semaforo)",

    # ── Tabla de Control de Carga de Archivos ──
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
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_censo_unicidad ON censo_forestal(id_arbol)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_tala_unica ON operaciones(id_arbol) WHERE tipo_operacion = 'Tala'",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_troza_unica ON operaciones(troza_id, tipo_operacion) WHERE troza_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_lote_unica ON operaciones(lote_id, tipo_operacion) WHERE lote_id IS NOT NULL AND troza_id IS NULL AND id_arbol IS NULL",
]


# ──────────────────────────────────────────────
# FUNCIONES DE CONEXIÓN
# ──────────────────────────────────────────────

class RBACCursor(sqlite3.Cursor):
    def execute(self, sql: str, parameters=None):
        modified_sql = self.connection._apply_rbac(sql)
        if parameters is not None:
            return super().execute(modified_sql, parameters)
        return super().execute(modified_sql)

    def executemany(self, sql: str, seq_of_parameters):
        modified_sql = self.connection._apply_rbac(sql)
        return super().executemany(modified_sql, seq_of_parameters)

class RBACConnection(sqlite3.Connection):
    def cursor(self, cursorClass=None):
        if cursorClass is None:
            cursorClass = RBACCursor
        return super().cursor(cursorClass)

    def execute(self, sql: str, parameters=None):
        modified_sql = self._apply_rbac(sql)
        if parameters is not None:
            return super().execute(modified_sql, parameters)
        return super().execute(modified_sql)

    def executemany(self, sql: str, seq_of_parameters):
        modified_sql = self._apply_rbac(sql)
        return super().executemany(modified_sql, seq_of_parameters)

    def _apply_rbac(self, sql: str) -> str:
        sql_upper = sql.upper()
        if "RUC_TITULAR = X-PIDE-RUC" in sql_upper:
            rol = pide_rol_var.get()
            ruc = pide_ruc_var.get()
            if rol == "Titular" and ruc:
                sql_lower = sql.lower()
                if "titulares" in sql_lower:
                    col_filter = f"ruc_dni = '{ruc}'"
                elif "titulos_habilitantes" in sql_lower:
                    col_filter = f"id_titular = '{ruc}'"
                elif "operaciones" in sql_lower:
                    col_filter = f"id_titular = '{ruc}'"
                elif "lotes" in sql_lower:
                    col_filter = f"titulo_habilitante_id IN (SELECT id_titulo FROM titulos_habilitantes WHERE id_titular = '{ruc}')"
                elif "censo_forestal" in sql_lower:
                    col_filter = f"id_plan IN (SELECT id_plan FROM planes_aprovechamiento WHERE id_titulo IN (SELECT id_titulo FROM titulos_habilitantes WHERE id_titular = '{ruc}'))"
                elif "balances_extraccion" in sql_lower:
                    col_filter = f"titulo_habilitante_id IN (SELECT id_titulo FROM titulos_habilitantes WHERE id_titular = '{ruc}')"
                else:
                    col_filter = f"1=1"
                sql = re.sub(r"ruc_titular\s*=\s*X-PIDE-RUC", col_filter, sql, flags=re.IGNORECASE)
            else:
                sql = re.sub(r"ruc_titular\s*=\s*X-PIDE-RUC", "1=1", sql, flags=re.IGNORECASE)
        return sql

def get_connection() -> sqlite3.Connection:
    """Devuelve una conexión SQLite con row_factory y WAL activado."""
    conn = sqlite3.connect(str(DB_PATH), factory=RBACConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ──────────────────────────────────────────────
# LOGICA DE AGENTE WORKER (PROCESAMIENTO ASÍNCRONO)
# ──────────────────────────────────────────────

def resolver_ruc(nombre_titular: str) -> str:
    """Resuelve un nombre de titular a un RUC determinista de 11 dígitos."""
    predefined = {
        "PRODUCTOR DEMO": "20123456789",
        "ACTOR-LOAD": "20987654321",
        "ACTOR-SEED": "20987654321"
    }
    nombre_clean = str(nombre_titular).strip()
    if nombre_clean in predefined:
        return predefined[nombre_clean]
    
    import hashlib
    h_int = int(hashlib.md5(nombre_clean.encode('utf-8')).hexdigest(), 16)
    h = str(h_int)[:9].ljust(9, '0')
    return f"20{h}"

ALLOWED_SPECIES = {'Shihuahuaco', 'Cumala', 'Cedro', 'Tornillo', 'Lupuna', 'Caoba'}

def procesar_archivo_background(job_id: str, file_path: str, tipo_archivo: str, rol_solicitante: str = None, ruc_solicitante: str = None) -> None:
    """
    Lee y valida un archivo Excel, insertando su contenido en SQLite.
    """
    import json
    import os
    from datetime import datetime
    
    conn = get_connection()
    try:
        conn.execute("UPDATE registro_cargas SET estado = 'PROCESANDO' WHERE id = ?", (job_id,))
        conn.commit()
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
            
        df = pd.read_excel(file_path, engine='openpyxl')
        df = df.fillna("")
        records = df.to_dict(orient="records")
        data_to_insert = []
        
        if tipo_archivo == "censo":
            for r in records:
                arbol_id = str(r["arbol_id"]).strip()
                vol = float(r["volumen_censado"])
                especie = str(r["especie"]).strip()
                th_id = str(r["titulo_habilitante_id"]).strip()
                plan_id = str(r.get("plan_id", f"PLAN-{th_id}")).strip()
                version = int(r.get("version", 1))
                fecha_aprobacion = str(r.get("fecha_aprobacion", "2026-06-14")).strip()
                
                if vol < 0:
                    raise ValueError(f"Volumen no puede ser negativo: {vol}")
                if especie not in ALLOWED_SPECIES:
                    raise ValueError(f"Especie '{especie}' no autorizada.")
                
                res_title = conn.execute("SELECT id_titular FROM titulos_habilitantes WHERE id_titulo = ?", (th_id,)).fetchone()
                if res_title:
                    id_titular = res_title["id_titular"]
                else:
                    titular_name = str(r.get("titular", "PRODUCTOR DEMO")).strip()
                    id_titular = resolver_ruc(titular_name)
                    conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, ?)", (id_titular, titular_name, "Direccion Demo"))
                    conn.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES (?, ?, ?, ?)",
                                 (th_id, id_titular, f"Concesion {th_id}", "Loreto, Peru"))
                
                conn.execute("""
                    INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado, documento_pdf_hash)
                    VALUES (?, ?, ?, ?, 'Aprobado', 'UPLOAD_HASH')
                """, (plan_id, th_id, version, fecha_aprobacion))
                    
                data_to_insert.append((arbol_id, plan_id, especie, vol, str(r.get("estado", "Autorizado")).strip(), str(r.get("condicion", "Aprovechable")).strip()))
                
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO censo_forestal
                (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id_arbol) DO UPDATE SET
                    volumen_autorizado = excluded.volumen_autorizado,
                    estado = excluded.estado,
                    condicion = excluded.condicion
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
                data_to_insert.append((balance_id, th_id, parcela, especie, vol_aut, vol_mov, saldo, estado_saldo))
                
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO balances_extraccion
                (balance_id, titulo_habilitante_id, parcela_corta, especie, volumen_autorizado, volumen_movilizado, saldo_disponible, estado_saldo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(balance_id) DO UPDATE SET
                    volumen_autorizado = excluded.volumen_autorizado,
                    saldo_disponible = excluded.volumen_autorizado - volumen_movilizado,
                    estado_saldo = CASE WHEN (excluded.volumen_autorizado - volumen_movilizado) < 0 THEN 'Negativo' ELSE 'Positivo' END
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
                mensaje = str(r.get("mensaje", "")).strip()
                
                if vol < 0:
                    raise ValueError(f"Volumen de lote no puede ser negativo: {vol}")
                
                ruc = resolver_ruc(titular)
                conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, 'Direccion Demo')", (ruc, titular))
                conn.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES (?, ?, ?, 'Loreto, Peru')", (th_id, ruc, f"Concesion {th_id}"))

                data_to_insert.append((lote_id, num_gtf, th_id, titular, parcela, especie, vol, estado_val, mensaje))
                
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
            new_records = [r for r in records if not conn.execute("SELECT 1 FROM operaciones WHERE operacion_id = ?", (str(r["operacion_id"]).strip(),)).fetchone()]
            
            for r in new_records:
                op_id = str(r["operacion_id"]).strip()
                tipo_op = str(r["tipo_operacion"]).strip()
                
                # Check role constraints on operation types
                if rol_solicitante == "Titular" and tipo_op == "Transformacion":
                    raise ValueError("El rol Titular no tiene permisos para cargar operaciones de transformación en planta.")
                if rol_solicitante == "Operador_CTP" and tipo_op != "Transformacion":
                    raise ValueError("El rol Operador CTP solo puede cargar operaciones de tipo transformación.")
                
                arbol_id = str(r.get("arbol_id", "")).strip() or None
                troza_id = str(r.get("troza_id", "")).strip() or None
                lote_id = str(r.get("lote_id", "")).strip() or None
                if lote_id: lotes_a_validar.add(lote_id)
                parcela = str(r["parcela_corta"]).strip()
                especie = str(r["especie"]).strip()
                volumen = float(r["volumen"])
                if volumen < 0:
                    raise ValueError(f"Volumen de operación no puede ser negativo: {volumen}")
                num_gtf = str(r.get("numero_gtf", "")).strip() or None
                actor_id = str(r.get("actor_id", "ACTOR-LOAD")).strip()
                fecha = str(r["fecha"]).strip()
                obs = str(r.get("observacion", "")).strip()
                
                # New fields from excel
                ruc_inst = str(r.get("ruc_institucion", "")).strip() or None
                reg_serfor = str(r.get("registro_serfor", "")).strip() or None
                dni_ch = str(r.get("dni_chofer", "")).strip() or None
                placa_veh = str(r.get("placa_vehiculo", "")).strip() or None
                
                # Validate using regex based on role
                import re
                role_to_check = rol_solicitante or ("Operador_CTP" if tipo_op == "Transformacion" else "Titular")
                
                if role_to_check in ("Titular", "Operador_CTP"):
                    val_ruc = ruc_inst or ruc_solicitante or resolver_ruc(actor_id)
                    if val_ruc and not re.match(r"^(10|20)\d{9}$", val_ruc):
                        raise ValueError(f"Fila con RUC inválido: {val_ruc}")
                    ruc_inst = val_ruc
                elif role_to_check == "Regente":
                    if reg_serfor and not re.match(r"^REG-SER-20\d{2}-\d{4}$", reg_serfor):
                        raise ValueError(f"Fila con Registro SERFOR inválido: {reg_serfor}")
                elif role_to_check == "Transportista":
                    if dni_ch and not re.match(r"^\d{8}$", dni_ch):
                        raise ValueError(f"Fila con DNI inválido: {dni_ch}")
                    if placa_veh and not re.match(r"^[A-Z0-9]{3}-[A-Z0-9]{3}$", placa_veh):
                        raise ValueError(f"Fila con Placa inválida: {placa_veh}")
                
                punto_cadena = 2
                if tipo_op == "Despacho": punto_cadena = 3
                elif tipo_op == "Transformacion": punto_cadena = 4
                
                id_titular = ruc_inst or resolver_ruc(actor_id)
                
                # Find th_id to validate ownership
                th_id = None
                if arbol_id:
                    res_arb = conn.execute("SELECT p.id_titulo FROM censo_forestal c JOIN planes_aprovechamiento p ON c.id_plan = p.id_plan WHERE c.id_arbol = ?", (arbol_id,)).fetchone()
                    if res_arb: th_id = res_arb["id_titulo"]
                if not th_id and lote_id:
                     res_lote = conn.execute("SELECT titulo_habilitante_id FROM lotes WHERE lote_id = ?", (lote_id,)).fetchone()
                     if res_lote: th_id = res_lote["titulo_habilitante_id"]
                target_th_id = th_id
                
                # Check ownership relation actor-title
                if rol_solicitante == "Titular" and ruc_solicitante and target_th_id:
                    res_title = conn.execute("SELECT id_titular FROM titulos_habilitantes WHERE id_titulo = ?", (target_th_id,)).fetchone()
                    if res_title and res_title["id_titular"] != ruc_solicitante:
                        raise ValueError(f"Acceso denegado: El Titulo Habilitante {target_th_id} no pertenece al Titular autenticado ({ruc_solicitante}).")
                
                if target_th_id:
                    conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, 'Direccion Demo')", (id_titular, actor_id))
                    conn.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES (?, ?, ?, 'Loreto, Peru')", (target_th_id, id_titular, f"Concesion {target_th_id}"))
                
                # Check plan integrity for the Title
                plan_aprobado = None
                if target_th_id:
                    plan_aprobado = conn.execute("SELECT 1 FROM planes_aprovechamiento WHERE id_titulo = ? AND estado = 'Aprobado'", (target_th_id,)).fetchone()
                if not plan_aprobado:
                    raise ValueError(f"No existe un Plan de Aprovechamiento aprobado asociado a este título ({target_th_id}).")
                
                data_to_insert.append((op_id, tipo_op, punto_cadena, arbol_id, troza_id, lote_id, parcela, especie, volumen, num_gtf, actor_id, ruc_inst, reg_serfor, dni_ch, placa_veh, id_titular, fecha, obs))
                
                conn.execute("""
                    UPDATE balances_extraccion
                    SET volumen_movilizado = volumen_movilizado + ?,
                        saldo_disponible = saldo_disponible - ?,
                        estado_saldo = CASE WHEN (saldo_disponible - ?) < 0 THEN 'Negativo' ELSE 'Positivo' END
                    WHERE titulo_habilitante_id = ? AND parcela_corta = ? AND especie = ?
                """, (volumen, volumen, volumen, target_th_id, parcela, especie))
                
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO operaciones
                (operacion_id, tipo_operacion, punto_cadena, id_arbol, troza_id, lote_id, parcela_corta, especie, volumen, numero_gtf, actor_id, ruc_institucion, registro_serfor, dni_chofer, placa_vehiculo, id_titular, fecha, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)
            conn.commit()
            
            accion_map = {'Tala': Acciones.REGISTRAR_TALA, 'Trozado': Acciones.REGISTRAR_TROZADO, 'Despacho': Acciones.REGISTRAR_DESPACHO, 'Transformacion': Acciones.INGRESO_CTP}
            for row in data_to_insert:
                op_id, tipo_op, punto_cadena, arbol_id, troza_id, lote_id, parcela, especie, volumen, num_gtf, actor_id, ruc_inst, reg_serfor, dni_ch, placa_veh, id_titular, fecha, obs = row
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



def procesar_plan_xlsx(file_path: str) -> dict:
    """
    Procesa un archivo Excel de Plan de Aprovechamiento (.xlsx) de manera transaccional.
    Inserta el plan con versión incremental, marca las versiones anteriores de ese título como 'Vencido'
    e ingresa los árboles al censo forestal.
    """
    import pandas as pd
    import os
    import json
    
    df = pd.read_excel(file_path, engine='openpyxl')
    df = df.fillna("")
    records = df.to_dict(orient="records")
    if not records:
        raise ValueError("El archivo de plan está vacío")
    
    first = records[0]
    th_id = str(first["titulo_habilitante_id"]).strip()
    plan_base_id = str(first["plan_id"]).strip()
    fecha_aprob = str(first.get("fecha_aprobacion", "2026-06-14")).strip()
    
    conn = get_connection()
    try:
        # Asegurar que existan titulares y títulos habilitantes
        res_title = conn.execute("SELECT id_titular FROM titulos_habilitantes WHERE id_titulo = ?", (th_id,)).fetchone()
        if res_title:
            id_titular = res_title["id_titular"]
        else:
            id_titular = resolver_ruc("PRODUCTOR DEMO")
            conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, 'Direccion Demo')", (id_titular, "PRODUCTOR DEMO"))
            conn.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES (?, ?, ?, 'Loreto, Peru')",
                         (th_id, id_titular, f"Concesion {th_id}"))
        
        # Consultar la versión máxima existente para este título
        row_v = conn.execute("SELECT MAX(version) as max_v FROM planes_aprovechamiento WHERE id_titulo = ?", (th_id,)).fetchone()
        max_v = row_v["max_v"] if row_v and row_v["max_v"] is not None else 0
        new_version = max_v + 1
        new_plan_id = f"{plan_base_id}-V{new_version}"
        
        # Marcar los planes anteriores como 'Vencido'
        conn.execute("UPDATE planes_aprovechamiento SET estado = 'Vencido' WHERE id_titulo = ?", (th_id,))
        
        # Insertar el nuevo plan aprobado
        conn.execute("""
            INSERT INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado, documento_pdf_hash)
            VALUES (?, ?, ?, ?, 'Aprobado', 'PDF_HASH_AUTO')
        """, (new_plan_id, th_id, new_version, fecha_aprob))
        
        # Insertar los árboles individuales en el censo
        census_data = []
        for r in records:
            arbol_id = str(r["arbol_id"]).strip()
            especie = str(r["especie"]).strip()
            vol = float(r["volumen_censado"])
            census_data.append((arbol_id, new_plan_id, especie, vol, 'Autorizado', 'Aprovechable'))
        
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id_arbol) DO UPDATE SET
                id_plan = excluded.id_plan,
                volumen_autorizado = excluded.volumen_autorizado,
                estado = excluded.estado,
                condicion = excluded.condicion
        """, census_data)
        
        conn.commit()
        return {
            "mensaje": "Plan de Aprovechamiento cargado y versionado con éxito",
            "plan_id": new_plan_id,
            "titulo_habilitante_id": th_id,
            "version": new_version,
            "registros_procesados": len(records)
        }
    except Exception as e:
        conn.rollback()
        raise e
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

def seed_from_excel() -> None:
    """
    Importa los datos de los archivos Excel de muestra a SQLite.
    Es idempotente: usa INSERT OR IGNORE para no duplicar.
    """
    conn = get_connection()
    try:
        # 1. Árboles (censo forestal)
        arboles_path = DATA_DIR / "arboles_sample.xlsx"
        if arboles_path.exists():
            df = pd.read_excel(arboles_path, engine='openpyxl')
            df = df.fillna("")
            df["arbol_id"] = df["arbol_id"].astype(str)
            for _, row in df.iterrows():
                arbol_id = str(row["arbol_id"])
                th_id = str(row["titulo_habilitante_id"])
                titular = str(row["titular"])
                especie = str(row["especie"])
                vol = float(row["volumen_censado"])
                estado = str(row.get("estado", "Autorizado"))
                condicion = str(row.get("condicion", "Aprovechable"))
                
                # Resolve RUC
                ruc = resolver_ruc(titular)
                
                # Seed parent structures
                conn.execute("""
                    INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion)
                    VALUES (?, ?, 'Direccion Demo')
                """, (ruc, titular))
                
                conn.execute("""
                    INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica)
                    VALUES (?, ?, ?, 'Loreto, Peru')
                """, (th_id, ruc, f"Concesion {th_id}"))
                
                plan_id = f"PLAN-{th_id}"
                conn.execute("""
                    INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado, documento_pdf_hash)
                    VALUES (?, ?, 1, '2026-06-14', 'Aprobado', 'SEED_HASH_123')
                """, (plan_id, th_id))
                
                # Seed censo forestal
                conn.execute("""
                    INSERT OR IGNORE INTO censo_forestal
                    (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                    VALUES (?,?,?,?,?,?)
                """, (arbol_id, plan_id, especie, vol, estado, condicion))
            print(f"[SEED] censo_forestal: {len(df)} registros importados.")

        # 2. Balances de extracción
        balances_path = DATA_DIR / "balances_sample.xlsx"
        if balances_path.exists():
            df = pd.read_excel(balances_path, engine='openpyxl')
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
        lotes_path = DATA_DIR / "lotes_sample.xlsx"
        if lotes_path.exists():
            df = pd.read_excel(lotes_path, engine='openpyxl')
            df = df.fillna("")
            for _, row in df.iterrows():
                th_id = row.get("titulo_habilitante_id","TH-001")
                titular = row.get("titular","PRODUCTOR DEMO")
                ruc = resolver_ruc(titular)
                
                # Ensure parent entities exist
                conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, 'Direccion Demo')", (ruc, titular))
                conn.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES (?, ?, ?, 'Loreto, Peru')", (th_id, ruc, f"Concesion {th_id}"))

                conn.execute("""
                    INSERT OR IGNORE INTO lotes
                    (lote_id, numero_gtf, titulo_habilitante_id, titular,
                     parcela_corta, especie, volumen_total, estado_validacion)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (row["lote_id"], row["numero_gtf"], th_id,
                      titular, row["parcela_corta"],
                      row["especie"], float(row["volumen_total"]), row["estado_validacion"]))
            print(f"[SEED] lotes: {len(df)} registros importados.")

        # 4. Operaciones (tala/trozado/despacho)
        ops_path = DATA_DIR / "operaciones_sample.xlsx"
        if ops_path.exists():
            df = pd.read_excel(ops_path, engine='openpyxl')
            df = df.fillna("")
            tipo_a_punto = {"Tala": 2, "Trozado": 2, "Despacho": 3, "Transformacion": 4}
            for _, row in df.iterrows():
                punto = tipo_a_punto.get(row["tipo_operacion"], 2)
                arbol_id = str(row["arbol_id"]) if str(row["arbol_id"]) != "" else None
                
                id_titular = None
                if arbol_id:
                    cursor = conn.execute("""
                        SELECT t.id_titular
                        FROM censo_forestal c
                        JOIN planes_aprovechamiento p ON c.id_plan = p.id_plan
                        JOIN titulos_habilitantes t ON p.id_titulo = t.id_titulo
                        WHERE c.id_arbol = ?
                    """, (arbol_id,)).fetchone()
                    if cursor:
                        id_titular = cursor["id_titular"]
                if not id_titular:
                    id_titular = resolver_ruc("ACTOR-SEED")

                conn.execute("""
                    INSERT OR IGNORE INTO operaciones
                    (operacion_id, tipo_operacion, punto_cadena, id_arbol, troza_id,
                     parcela_corta, especie, volumen, numero_gtf, actor_id, id_titular, fecha)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (row["operacion_id"], row["tipo_operacion"], punto,
                      arbol_id,
                      str(row["troza_id"]) if (row["troza_id"] != "") else None,
                      row["parcela_corta"], row["especie"], float(row["volumen"]),
                      str(row["numero_gtf"]) if (row["numero_gtf"] != "") else None,
                      "ACTOR-SEED", id_titular, row["fecha"]))
            print(f"[SEED] operaciones: {len(df)} registros importados.")

        conn.commit()
        print("[SEED] Carga inicial completada.")
    except Exception as e:
        print(f"[SEED] Error al sembrar base de datos: {e}")
    finally:
        conn.close()

def penalizar_arbol_retroactivo(arbol_id: str, motivo: str) -> dict:
    """
    Penaliza recursivamente un árbol declarado falso por OSINFOR.
    Marca el árbol como 'FRAUDE_DETECTADO', identifica todos los lotes comerciales
    que se derivaron directa o indirectamente de ese árbol, cambia su semáforo a 'Rojo',
    antepone la alerta retroactiva de OSINFOR al mensaje de validación, registra el fallo
    en validaciones, y guarda el evento en logs_auditoria.
    """
    import json
    import uuid
    from engine.hashing import registrar_evento
    
    conn = get_connection()
    lotes_afectados = set()
    try:
        # 1. Marcar el árbol como FRAUDE_DETECTADO
        conn.execute("UPDATE censo_forestal SET estado = 'FRAUDE_DETECTADO' WHERE id_arbol = ?", (arbol_id,))
        
        # 2. Rastrear operaciones de Tala, Trozado y Despacho
        ops = conn.execute("SELECT DISTINCT lote_id, troza_id FROM operaciones WHERE id_arbol = ?", (arbol_id,)).fetchall()
        
        trozas_afectadas = set()
        for r in ops:
            if r["lote_id"]:
                lotes_afectados.add(r["lote_id"])
            if r["troza_id"]:
                trozas_afectadas.add(r["troza_id"])
                
        # Buscar operaciones que referencien estas trozas
        if trozas_afectadas:
            placeholders = ",".join("?" for _ in trozas_afectadas)
            ops_trozas = conn.execute(f"SELECT DISTINCT lote_id FROM operaciones WHERE troza_id IN ({placeholders})", list(trozas_afectadas)).fetchall()
            for r in ops_trozas:
                if r["lote_id"]:
                    lotes_afectados.add(r["lote_id"])
                    
        # 3. Penalizar cada lote en cascada
        alerta_msg = "[ALERTA RETROACTIVA OSINFOR]: El árbol origen de este recurso fue declarado FALSO tras supervisión ex-post en bosque. Infracción D.L. 1085."
        
        for lid in lotes_afectados:
            lote_row = conn.execute("SELECT mensaje_validacion FROM lotes WHERE lote_id = ?", (lid,)).fetchone()
            curr_msg = lote_row["mensaje_validacion"] if lote_row and lote_row["mensaje_validacion"] else ""
            new_msg = f"{alerta_msg} | {curr_msg}" if curr_msg else alerta_msg
            
            # Actualizar lote
            conn.execute("""
                UPDATE lotes
                SET color_semaforo = 'Rojo',
                    mensaje_validacion = ?,
                    estado_validacion = 'Validado'
                WHERE lote_id = ?
            """, (new_msg, lid))
            
            # Guardar validación ex-post
            val_id = f"VAL-{uuid.uuid4().hex[:8].upper()}"
            conn.execute("""
                INSERT INTO validaciones
                (validacion_id, lote_id, regla, resultado, severidad, color_semaforo, mensaje, detalle_json)
                VALUES (?, ?, 'supervision_expost', 'Rechazado', 'Critica', 'Rojo', ?, ?)
            """, (val_id, lid, motivo, json.dumps({"arbol_id": arbol_id, "motivo": motivo})))
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    # 4. Registrar eventos en logs_auditoria (fuera de la transacción principal para evitar deadlocks)
    try:
        registrar_evento(
            actor_id="OSINFOR-SUPERVISOR",
            tipo_actor="OSINFOR",
            accion="BLOQUEAR_LOTE",
            punto_cadena=1,
            entidad_tipo="Operacion",
            entidad_id=arbol_id,
            payload={"arbol_id": arbol_id, "motivo": motivo, "estado": "FRAUDE_DETECTADO"}
        )
        
        alerta_msg = "[ALERTA RETROACTIVA OSINFOR]: El árbol origen de este recurso fue declarado FALSO tras supervisión ex-post en bosque. Infracción D.L. 1085."
        for lid in lotes_afectados:
            registrar_evento(
                actor_id="OSINFOR-SUPERVISOR",
                tipo_actor="OSINFOR",
                accion="BLOQUEAR_LOTE",
                punto_cadena=3,
                entidad_tipo="Lote",
                entidad_id=lid,
                payload={"arbol_id": arbol_id, "motivo": motivo, "alerta": alerta_msg}
            )
    except Exception as e:
        print(f"[ERROR] No se pudo escribir log de auditoría retroactiva: {e}")

    return {
        "mensaje": "Penalización retroactiva aplicada con éxito",
        "arbol_id": arbol_id,
        "lotes_afectados": list(lotes_afectados)
    }
def buscar_trazabilidad_semantica(criterio: str, valor: str, ruc_filtro: str = None) -> dict:
    """
    Realiza una consulta polimórfica e inteligente en la base de datos aplicando
    scoping de titularidad si ruc_filtro está presente.
    """
    conn = get_connection()
    try:
        if criterio == "arbol_id":
            # 1. Buscar árbol y sus relaciones
            tree = conn.execute("""
                SELECT c.id_arbol, c.id_especie, c.volumen_autorizado, c.estado as censo_estado, c.condicion,
                       p.id_plan, p.version, p.fecha_aprobacion, p.estado as plan_estado, p.id_titulo,
                       t.id_titular, t.nombre_concesion, t.ubicacion_geografica
                FROM censo_forestal c
                JOIN planes_aprovechamiento p ON c.id_plan = p.id_plan
                JOIN titulos_habilitantes t ON p.id_titulo = t.id_titulo
                WHERE c.id_arbol = ?
            """, (valor,)).fetchone()
            
            if not tree:
                return None
                
            # Validar pertenencia del RUC
            if ruc_filtro and tree["id_titular"] != ruc_filtro:
                raise PermissionError("Acceso denegado: El árbol consultado no pertenece a sus títulos habilitantes autorizados.")
                
            # Obtener operaciones
            # Tala
            talas = conn.execute("SELECT * FROM operaciones WHERE id_arbol = ? AND tipo_operacion = 'Tala'", (valor,)).fetchall()
            # Trozado
            trozados = conn.execute("SELECT * FROM operaciones WHERE id_arbol = ? AND tipo_operacion = 'Trozado'", (valor,)).fetchall()
            # Despacho
            despachos = conn.execute("""
                SELECT * FROM operaciones 
                WHERE troza_id IN (SELECT troza_id FROM operaciones WHERE id_arbol = ? AND troza_id IS NOT NULL AND troza_id != '')
                AND tipo_operacion = 'Despacho'
            """, (valor,)).fetchall()
            # Transformacion (operaciones)
            transformaciones_ops = conn.execute("""
                SELECT * FROM operaciones 
                WHERE lote_id IN (
                    SELECT lote_id FROM operaciones 
                    WHERE troza_id IN (SELECT troza_id FROM operaciones WHERE id_arbol = ? AND troza_id IS NOT NULL AND troza_id != '')
                    AND lote_id IS NOT NULL AND lote_id != ''
                )
                AND tipo_operacion = 'Transformacion'
            """, (valor,)).fetchall()
            # Transformación CTP (tabla transformaciones)
            ctp_trans = conn.execute("""
                SELECT * FROM transformaciones 
                WHERE lote_id IN (
                    SELECT lote_id FROM operaciones 
                    WHERE troza_id IN (SELECT troza_id FROM operaciones WHERE id_arbol = ? AND troza_id IS NOT NULL AND troza_id != '')
                    AND lote_id IS NOT NULL AND lote_id != ''
                )
            """, (valor,)).fetchall()
            
            return {
                "tipo": "arbol",
                "id": tree["id_arbol"],
                "arbol": dict(tree),
                "operaciones": {
                    "tala": [dict(o) for o in talas],
                    "trozado": [dict(o) for o in trozados],
                    "despacho": [dict(o) for o in despachos],
                    "transformacion": [dict(o) for o in transformaciones_ops]
                },
                "transformaciones_ctp": [dict(t) for t in ctp_trans]
            }
            
        elif criterio == "gtf":
            # 2. Buscar lote/operaciones por GTF
            # Intentar primero buscar en tabla lotes
            lote = conn.execute("""
                SELECT l.*, t.id_titular
                FROM lotes l
                JOIN titulos_habilitantes t ON l.titulo_habilitante_id = t.id_titulo
                WHERE l.numero_gtf = ? OR l.lote_id = ?
            """, (valor, valor)).fetchone()
            
            if not lote:
                # Si no está en lotes, buscar si hay operaciones con ese numero_gtf
                op_gtf = conn.execute("""
                    SELECT o.lote_id, o.numero_gtf, o.id_titular, o.fecha
                    FROM operaciones o
                    WHERE o.numero_gtf = ? AND o.lote_id IS NOT NULL AND o.lote_id != '' LIMIT 1
                """, (valor,)).fetchone()
                
                if op_gtf:
                    lote_id = op_gtf["lote_id"]
                    # Intentar buscar el lote correspondiente en lotes
                    lote = conn.execute("""
                        SELECT l.*, t.id_titular
                        FROM lotes l
                        JOIN titulos_habilitantes t ON l.titulo_habilitante_id = t.id_titulo
                        WHERE l.lote_id = ?
                    """, (lote_id,)).fetchone()
                    
                    if not lote:
                        # Si no hay lote en lotes pero hay ops, crear un lote ficticio para retornar datos coherentes
                        lote = {
                            "lote_id": lote_id,
                            "numero_gtf": op_gtf["numero_gtf"],
                            "titulo_habilitante_id": "TH-DESCONOCIDO",
                            "titular": "DESCONOCIDO",
                            "parcela_corta": "PC-DESCONOCIDA",
                            "especie": "DESCONOCIDA",
                            "volumen_total": 0.0,
                            "estado_validacion": "Pendiente",
                            "color_semaforo": "Amarillo",
                            "mensaje_validacion": "Lote no consolidado en la tabla de lotes.",
                            "id_titular": op_gtf["id_titular"]
                        }
                
            if not lote:
                return None
                
            # Validar pertenencia del RUC
            if ruc_filtro and lote["id_titular"] != ruc_filtro:
                raise PermissionError("Acceso denegado: La guía o lote consultado no pertenece a sus títulos habilitantes autorizados.")
                
            # Resolver árboles de censo origen
            lote_id = lote["lote_id"]
            origin_trees = conn.execute("""
                SELECT c.*, p.id_titulo, t.nombre_concesion
                FROM censo_forestal c
                JOIN planes_aprovechamiento p ON c.id_plan = p.id_plan
                JOIN titulos_habilitantes t ON p.id_titulo = t.id_titulo
                WHERE c.id_arbol IN (
                    SELECT DISTINCT id_arbol 
                    FROM operaciones 
                    WHERE troza_id IN (
                        SELECT DISTINCT troza_id 
                        FROM operaciones 
                        WHERE lote_id = ? AND troza_id IS NOT NULL AND troza_id != ''
                    ) 
                    AND id_arbol IS NOT NULL AND id_arbol != ''
                )
            """, (lote_id,)).fetchall()
            
            # Validaciones
            validaciones = conn.execute("SELECT * FROM validaciones WHERE lote_id = ?", (lote_id,)).fetchall()
            
            return {
                "tipo": "gtf",
                "lote_id": lote_id,
                "numero_gtf": lote["numero_gtf"],
                "lote": dict(lote) if hasattr(lote, 'keys') else lote,
                "arboles_origen": [dict(a) for a in origin_trees],
                "validaciones": [dict(v) for v in validaciones]
            }
            
        elif criterio == "titulo_habilitante":
            # 3. Buscar Título Habilitante y su plan
            titulo = conn.execute("""
                SELECT t.id_titulo, t.id_titular, t.nombre_concesion, t.ubicacion_geografica,
                       ti.nombre as nombre_titular
                FROM titulos_habilitantes t
                JOIN titulares ti ON t.id_titular = ti.ruc_dni
                WHERE t.id_titulo = ?
            """, (valor,)).fetchone()
            
            if not titulo:
                return None
                
            # Validar pertenencia del RUC
            if ruc_filtro and titulo["id_titular"] != ruc_filtro:
                raise PermissionError("Acceso denegado: El Título Habilitante consultado no le pertenece.")
                
            # Plan aprobado activo
            plan = conn.execute("""
                SELECT * FROM planes_aprovechamiento 
                WHERE id_titulo = ? AND estado = 'Aprobado'
                ORDER BY version DESC LIMIT 1
            """, (valor,)).fetchone()
            
            resumen = None
            if plan:
                resumen = conn.execute("""
                    SELECT COUNT(*) as total_arboles, SUM(volumen_autorizado) as volumen_total 
                    FROM censo_forestal 
                    WHERE id_plan = ?
                """, (plan["id_plan"],)).fetchone()
                
            return {
                "tipo": "titulo",
                "id_titulo": titulo["id_titulo"],
                "titulo": dict(titulo),
                "plan": dict(plan) if plan else None,
                "resumen_censo": dict(resumen) if resumen else None
            }
            
        else:
            raise ValueError(f"Criterio de búsqueda '{criterio}' no soportado.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    seed_from_excel()

