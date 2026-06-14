import sqlite3
import pandas as pd
from pathlib import Path
import json
import os
from datetime import datetime

# ──────────────────────────────────────────────
# RUTAS
# ──────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parents[2]
DB_PATH    = ROOT_DIR / "backend" / "arbortrust.db"
DATA_DIR   = ROOT_DIR / "data" / "sample"
PROC_DIR   = ROOT_DIR / "data" / "processed"


# ──────────────────────────────────────────────
# DDL: Definición de tablas
# ──────────────────────────────────────────────
DDL_STATEMENTS = [
    # ── M1: Titulares (RUC/DNI, Nombre, Dirección) ──
    """
    CREATE TABLE IF NOT EXISTS titulares (
        ruc_dni             TEXT PRIMARY KEY,
        nombre              TEXT NOT NULL,
        direccion           TEXT,
        created_at          TEXT DEFAULT (datetime('now'))
    )
    """,

    # ── M1: Titulos_Habilitantes (ID_Título, ID_Titular, Nombre_Concesión/Predio, Ubicación_Geográfica) ──
    """
    CREATE TABLE IF NOT EXISTS titulos_habilitantes (
        id_titulo           TEXT PRIMARY KEY,
        id_titular          TEXT NOT NULL,
        nombre_concesion    TEXT,
        ubicacion_geografica TEXT,
        created_at          TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (id_titular) REFERENCES titulares(ruc_dni) ON DELETE CASCADE
    )
    """,

    # ── M1: Planes_Aprovechamiento (ID_Plan, ID_Título, Versión, Fecha_Aprobación, Estado, Documento_PDF_Hash) ──
    """
    CREATE TABLE IF NOT EXISTS planes_aprovechamiento (
        id_plan             TEXT PRIMARY KEY,
        id_titulo           TEXT NOT NULL,
        version             INTEGER NOT NULL,
        fecha_aprobacion    TEXT,
        estado              TEXT DEFAULT 'Aprobado' CHECK(estado IN ('Aprobado','Actualizado','Vencido')),
        documento_pdf_hash  TEXT,
        created_at          TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (id_titulo) REFERENCES titulos_habilitantes(id_titulo) ON DELETE CASCADE
    )
    """,

    # ── M1: Censo_Forestal (ID_Arbol, ID_Plan, ID_Especie, Volumen_Autorizado) ──
    """
    CREATE TABLE IF NOT EXISTS censo_forestal (
        id_arbol            TEXT PRIMARY KEY,
        id_plan             TEXT NOT NULL,
        id_especie          TEXT NOT NULL,
        volumen_autorizado  REAL NOT NULL,
        estado              TEXT DEFAULT 'Autorizado',
        condicion           TEXT DEFAULT 'Aprovechable',
        created_at          TEXT DEFAULT (datetime('now')),
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
        updated_at            TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (titulo_habilitante_id) REFERENCES titulos_habilitantes(id_titulo) ON DELETE CASCADE
    )
    """,

    # ── M1/Punto 2: Aprovechamiento (Tala / Trozado / Despacho) con referencias jerárquicas ──
    """
    CREATE TABLE IF NOT EXISTS operaciones (
        id_operacion    TEXT PRIMARY KEY,
        tipo_operacion  TEXT NOT NULL CHECK(tipo_operacion IN ('Tala','Trozado','Despacho','Transformacion')),
        punto_cadena    INTEGER NOT NULL CHECK(punto_cadena IN (2,3,4)),
        id_arbol        TEXT,
        id_titular      TEXT,
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
        FOREIGN KEY (id_arbol) REFERENCES censo_forestal(id_arbol) ON DELETE SET NULL,
        FOREIGN KEY (id_titular) REFERENCES titulares(ruc_dni) ON DELETE SET NULL,
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
        created_at            TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (titulo_habilitante_id) REFERENCES titulos_habilitantes(id_titulo)
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
    "CREATE INDEX IF NOT EXISTS idx_operaciones_arbol    ON operaciones(id_arbol)",
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
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_arboles_unicidad ON censo_forestal(id_arbol)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_tala_unica ON operaciones(id_arbol) WHERE tipo_operacion = 'Tala'",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_troza_unica ON operaciones(troza_id, tipo_operacion) WHERE troza_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_lote_unica ON operaciones(lote_id, tipo_operacion) WHERE lote_id IS NOT NULL AND troza_id IS NULL AND id_arbol IS NULL",
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
# METODOS AUXILIARES PARA COMPATIBILIDAD DE SEED
# ──────────────────────────────────────────────

def get_ruc_for_titular(nombre: str) -> str:
    """Retorna un RUC determinista de 11 dígitos para un nombre de titular dado."""
    if nombre == "PRODUCTOR DEMO":
        return "20123456789"
    import hashlib
    # Genera un hash determinista a partir de los bytes del nombre y extrae dígitos
    hex_digest = hashlib.md5(nombre.encode('utf-8')).hexdigest()
    digits = ''.join(filter(str.isdigit, hex_digest))
    if len(digits) >= 11:
        return "20" + digits[:9]
    else:
        return "20" + (digits + "123456789")[:9]


# ──────────────────────────────────────────────
# LOGICA DE AGENTE WORKER (PROCESAMIENTO ASÍNCRONO)
# ──────────────────────────────────────────────

ALLOWED_SPECIES = {'Shihuahuaco', 'Cumala', 'Cedro', 'Tornillo', 'Lupuna', 'Caoba'}

def procesar_archivo_background(job_id: str, file_path: str, tipo_archivo: str) -> None:
    """
    Parsea y procesa el archivo subido en segundo plano.
    Utiliza transacciones explícitas, validaciones de negocio e inserciones masivas.
    """
    conn = get_connection()
    try:
        # 1. Cambiar estado a PROCESANDO
        conn.execute("UPDATE registro_cargas SET estado = 'PROCESANDO' WHERE id = ?", (job_id,))
        conn.commit()
        
        # 2. Leer archivo
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no encontrado en la ruta: {file_path}")
            
        df = pd.read_excel(file_path, engine='openpyxl')
        df = df.fillna("")
        records = df.to_dict(orient="records")
        
        # 3. Validar y construir tuplas
        data_to_insert = []
        
        if tipo_archivo == "censo":
            # Puede ser formato antiguo (arboles_sample.xlsx) o nuevo (M2 con metadata de planes)
            for r in records:
                arbol_id = str(r.get("arbol_id") or r.get("id_arbol", "")).strip()
                vol = float(r.get("volumen_censado") or r.get("volumen_autorizado", 0))
                especie = str(r.get("especie") or r.get("id_especie", "")).strip()
                
                if vol < 0:
                    raise ValueError(f"Volumen no puede ser negativo: {vol}")
                if especie not in ALLOWED_SPECIES:
                    raise ValueError(f"Especie '{especie}' no autorizada. Especies permitidas: {list(ALLOWED_SPECIES)}")
                
                # Extraer o deducir jerarquía
                titular_name = str(r.get("titular", "PRODUCTOR DEMO")).strip()
                th_id = str(r.get("titulo_habilitante_id") or r.get("id_titulo", "TH-001")).strip()
                plan_id = str(r.get("plan_id") or r.get("id_plan", f"PLAN-{th_id}")).strip()
                version = int(r.get("version", 1))
                fecha_aprob = str(r.get("fecha_aprobacion", datetime.now().strftime("%Y-%m-%d"))).strip()
                
                # Insertar/Verificar Titular
                ruc_dni = get_ruc_for_titular(titular_name)
                conn.execute("""
                    INSERT OR IGNORE INTO titulares (ruc_dni, nombre)
                    VALUES (?, ?)
                """, (ruc_dni, titular_name))
                
                # Insertar/Verificar Título Habilitante
                conn.execute("""
                    INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica)
                    VALUES (?, ?, ?, ?)
                """, (th_id, ruc_dni, f"Concesión {th_id}", "Loreto"))
                
                # Insertar/Verificar Plan Aprovechamiento
                conn.execute("""
                    INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado)
                    VALUES (?, ?, ?, ?, 'Aprobado')
                """, (plan_id, th_id, version, fecha_aprob))
                
                data_to_insert.append((
                    arbol_id,
                    plan_id,
                    especie,
                    vol,
                    str(r.get("estado", "Autorizado")).strip(),
                    str(r.get("condicion", "Aprovechable")).strip()
                ))
                
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
                
                if vol_aut < 0 or vol_mov < 0:
                    raise ValueError("Los volúmenes de balance no pueden ser negativos")
                if especie not in ALLOWED_SPECIES:
                    raise ValueError(f"Especie '{especie}' no autorizada")
                
                # Asegurar Título Habilitante y Titular existen
                conn.execute("""
                    INSERT OR IGNORE INTO titulares (ruc_dni, nombre)
                    VALUES ('20123456789', 'PRODUCTOR DEMO')
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica)
                    VALUES (?, '20123456789', ?, 'Loreto')
                """, (th_id, f"Concesión {th_id}"))
                
                data_to_insert.append((
                    balance_id, th_id, parcela, especie, vol_aut, vol_mov, saldo, estado_saldo
                ))
                
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
                mensaje = r.get("mensaje", None)
                if pd.notna(mensaje):
                    mensaje = str(mensaje).strip()
                else:
                    mensaje = None
                
                if vol < 0:
                    raise ValueError(f"Volumen de lote no puede ser negativo: {vol}")
                if especie not in ALLOWED_SPECIES:
                    raise ValueError(f"Especie '{especie}' no autorizada")
                
                # Asegurar Título y Titular
                ruc_dni = get_ruc_for_titular(titular)
                conn.execute("""
                    INSERT OR IGNORE INTO titulares (ruc_dni, nombre)
                    VALUES (?, ?)
                """, (ruc_dni, titular))
                conn.execute("""
                    INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica)
                    VALUES (?, ?, ?, 'Loreto')
                """, (th_id, ruc_dni, f"Concesión {th_id}"))
                
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
                exists = conn.execute("SELECT 1 FROM operaciones WHERE id_operacion = ?", (op_id,)).fetchone()
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
                
                # Validar campos de negocio
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
                
                # Determinar RUC Titular
                th_id = None
                id_titular = None
                if arbol_id:
                    res_arb = conn.execute("""
                        SELECT th.id_titulo, th.id_titular
                        FROM censo_forestal cf
                        JOIN planes_aprovechamiento pa ON cf.id_plan = pa.id_plan
                        JOIN titulos_habilitantes th ON pa.id_titulo = th.id_titulo
                        WHERE cf.id_arbol = ?
                    """, (arbol_id,)).fetchone()
                    if res_arb:
                        th_id = res_arb["id_titulo"]
                        id_titular = res_arb["id_titular"]
                if not th_id and lote_id:
                    res_lote = conn.execute("""
                        SELECT th.id_titulo, th.id_titular
                        FROM lotes l
                        JOIN titulos_habilitantes th ON l.titulo_habilitante_id = th.id_titulo
                        WHERE l.lote_id = ?
                    """, (lote_id,)).fetchone()
                    if res_lote:
                        th_id = res_lote["id_titulo"]
                        id_titular = res_lote["id_titular"]
                
                if not id_titular:
                    id_titular = get_ruc_for_titular("PRODUCTOR DEMO")
                if not th_id:
                    th_id = "TH-001"
                
                data_to_insert.append((
                    op_id, tipo_op, punto_cadena, arbol_id, id_titular, troza_id, lote_id, parcela, especie, volumen, num_gtf, actor_id, fecha, obs
                ))
                
                # Descontar volumen del balance
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
                (id_operacion, tipo_operacion, punto_cadena, id_arbol, id_titular, troza_id, lote_id, parcela_corta, especie, volumen, numero_gtf, actor_id, fecha, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)
            
            # Commit atómico antes de validar e integrar eventos, para liberar el bloqueo de escritura
            conn.commit()
            
            # Registrar logs de auditoría
            accion_map = {
                'Tala': Acciones.REGISTRAR_TALA,
                'Trozado': Acciones.REGISTRAR_TROZADO,
                'Despacho': Acciones.REGISTRAR_DESPACHO,
                'Transformacion': Acciones.INGRESO_CTP
            }
            
            for row in data_to_insert:
                op_id, tipo_op, punto_cadena, arbol_id, id_titular, troza_id, lote_id, parcela, especie, volumen, num_gtf, actor_id, fecha, obs = row
                accion = accion_map.get(tipo_op, "OTRA_OPERACION")
                entidad_id = lote_id if lote_id else (arbol_id or "GENERAL")
                payload_dict = {
                    "tipo_operacion": tipo_op,
                    "punto_cadena": punto_cadena,
                    "arbol_id": arbol_id,
                    "id_titular": id_titular,
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
                titular_name = row["titular"]
                ruc_dni = get_ruc_for_titular(titular_name)
                th_id = row["titulo_habilitante_id"]
                plan_id = f"PLAN-{th_id}"
                
                # Cargar Titular
                conn.execute("""
                    INSERT OR IGNORE INTO titulares (ruc_dni, nombre)
                    VALUES (?, ?)
                """, (ruc_dni, titular_name))
                
                # Cargar Título Habilitante
                conn.execute("""
                    INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica)
                    VALUES (?, ?, ?, 'Loreto')
                """, (th_id, ruc_dni, f"Concesión {th_id}"))
                
                # Cargar Plan Aprovechamiento
                conn.execute("""
                    INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado)
                    VALUES (?, ?, 1, '2026-06-14', 'Aprobado')
                """, (plan_id, th_id))
                
                # Cargar Censo Forestal
                conn.execute("""
                    INSERT OR IGNORE INTO censo_forestal
                    (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                    VALUES (?,?,?,?,?,?)
                """, (str(row["arbol_id"]), plan_id, row["especie"],
                      float(row["volumen_censado"]), row["estado"], row["condicion"]))
            print(f"[SEED] censo_forestal (arboles): {len(df)} registros importados.")

        # 2. Balances de extracción
        balances_path = DATA_DIR / "balances_sample.xlsx"
        if balances_path.exists():
            df = pd.read_excel(balances_path, engine='openpyxl')
            df = df.fillna("")
            for _, row in df.iterrows():
                th_id = row["titulo_habilitante_id"]
                # Asegurar Título y Titular existen
                conn.execute("""
                    INSERT OR IGNORE INTO titulares (ruc_dni, nombre)
                    VALUES ('20123456789', 'PRODUCTOR DEMO')
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica)
                    VALUES (?, '20123456789', ?, 'Loreto')
                """, (th_id, f"Concesión {th_id}"))
                
                conn.execute("""
                    INSERT OR IGNORE INTO balances_extraccion
                    (balance_id, titulo_habilitante_id, parcela_corta, especie,
                     volumen_autorizado, volumen_movilizado, saldo_disponible, estado_saldo)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (row["balance_id"], th_id,
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
                titular_name = row.get("titular","PRODUCTOR DEMO")
                ruc_dni = get_ruc_for_titular(titular_name)
                
                # Asegurar Titular y Título
                conn.execute("""
                    INSERT OR IGNORE INTO titulares (ruc_dni, nombre)
                    VALUES (?, ?)
                """, (ruc_dni, titular_name))
                conn.execute("""
                    INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica)
                    VALUES (?, ?, ?, 'Loreto')
                """, (th_id, ruc_dni, f"Concesión {th_id}"))
                
                conn.execute("""
                    INSERT OR IGNORE INTO lotes
                    (lote_id, numero_gtf, titulo_habilitante_id, titular,
                     parcela_corta, especie, volumen_total, estado_validacion)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (row["lote_id"], row["numero_gtf"], th_id,
                      titular_name, row["parcela_corta"],
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
                arbol_id = str(row["arbol_id"])
                
                # Buscar id_titular
                id_titular = None
                if arbol_id != "":
                    res_arb = conn.execute("""
                        SELECT th.id_titular 
                        FROM censo_forestal cf
                        JOIN planes_aprovechamiento pa ON cf.id_plan = pa.id_plan
                        JOIN titulos_habilitantes th ON pa.id_titulo = th.id_titulo
                        WHERE cf.id_arbol = ?
                    """, (arbol_id,)).fetchone()
                    if res_arb:
                        id_titular = res_arb["id_titular"]
                if not id_titular:
                    id_titular = get_ruc_for_titular("PRODUCTOR DEMO")
                    
                conn.execute("""
                    INSERT OR IGNORE INTO operaciones
                    (id_operacion, tipo_operacion, punto_cadena, id_arbol, id_titular, troza_id,
                     parcela_corta, especie, volumen, numero_gtf, actor_id, fecha)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (row["operacion_id"], row["tipo_operacion"], punto,
                      arbol_id if arbol_id != "" else None,
                      id_titular,
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
        # 1. Marcar el árbol como FRAUDE_DETECTADO en censo_forestal
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


if __name__ == "__main__":
    init_db()
    seed_from_excel()
