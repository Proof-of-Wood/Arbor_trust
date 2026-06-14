import os
import sqlite3
import pandas as pd
import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(
    title="ArborTrust Mock API",
    description="High-fidelity simulation server for ArborTrust Forest Management E2E testing",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = Path(__file__).resolve().parent / "arbortrust_mock.db"
ALLOWED_SPECIES = {'Shihuahuaco', 'Cumala', 'Cedro', 'Tornillo', 'Lupuna', 'Caoba'}

# ──────────────────────────────────────────────
# DATABASE HELPER
# ──────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_connection()
    try:
        # 1. Titulares
        conn.execute("""
            CREATE TABLE IF NOT EXISTS titulares (
                ruc_dni TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                direccion TEXT
            )
        """)
        # 2. Titulos Habilitantes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS titulos_habilitantes (
                titulo_id TEXT PRIMARY KEY,
                titular_id TEXT NOT NULL,
                concesion_predio TEXT NOT NULL,
                ubicacion TEXT,
                FOREIGN KEY (titular_id) REFERENCES titulares(ruc_dni)
            )
        """)
        # 3. Planes Aprovechamiento
        conn.execute("""
            CREATE TABLE IF NOT EXISTS planes_aprovechamiento (
                plan_id TEXT PRIMARY KEY,
                titulo_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                fecha_aprobacion TEXT NOT NULL,
                estado TEXT NOT NULL CHECK(estado IN ('Aprobado', 'Actualizado', 'Vencido')),
                documento_pdf_hash TEXT,
                FOREIGN KEY (titulo_id) REFERENCES titulos_habilitantes(titulo_id)
            )
        """)
        # 4. Censo Forestal
        conn.execute("""
            CREATE TABLE IF NOT EXISTS censo_forestal (
                arbol_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                especie TEXT NOT NULL,
                volumen_autorizado REAL NOT NULL,
                volumen_movilizado REAL DEFAULT 0.0,
                estado TEXT DEFAULT 'Autorizado', -- 'Autorizado', 'FRAUDE_DETECTADO'
                FOREIGN KEY (plan_id) REFERENCES planes_aprovechamiento(plan_id)
            )
        """)
        # 5. Lotes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lotes (
                lote_id TEXT PRIMARY KEY,
                numero_gtf TEXT NOT NULL,
                titulo_id TEXT NOT NULL,
                titular_id TEXT NOT NULL,
                parcela_corta TEXT NOT NULL,
                especie TEXT NOT NULL,
                volumen_total REAL NOT NULL,
                estado_validacion TEXT DEFAULT 'Pendiente',
                color_semaforo TEXT DEFAULT 'Amarillo',
                mensaje_validacion TEXT,
                fecha_creacion TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (titulo_id) REFERENCES titulos_habilitantes(titulo_id),
                FOREIGN KEY (titular_id) REFERENCES titulares(ruc_dni)
            )
        """)
        # 6. Operaciones
        conn.execute("""
            CREATE TABLE IF NOT EXISTS operaciones (
                operacion_id TEXT PRIMARY KEY,
                tipo_operacion TEXT NOT NULL CHECK(tipo_operacion IN ('Tala', 'Trozado', 'Despacho', 'Transformacion')),
                punto_cadena INTEGER NOT NULL CHECK(punto_cadena IN (2, 3, 4)),
                arbol_id TEXT,
                troza_id TEXT,
                lote_id TEXT,
                parcela_corta TEXT NOT NULL,
                especie TEXT NOT NULL,
                volumen REAL NOT NULL,
                numero_gtf TEXT,
                actor_id TEXT NOT NULL,
                fecha TEXT NOT NULL,
                observacion TEXT,
                estado_validacion TEXT DEFAULT 'Pendiente',
                FOREIGN KEY (arbol_id) REFERENCES censo_forestal(arbol_id),
                FOREIGN KEY (lote_id) REFERENCES lotes(lote_id)
            )
        """)
        # 7. Validaciones
        conn.execute("""
            CREATE TABLE IF NOT EXISTS validaciones (
                validacion_id TEXT PRIMARY KEY,
                lote_id TEXT NOT NULL,
                regla TEXT NOT NULL,
                resultado TEXT NOT NULL CHECK(resultado IN ('Aprobado', 'Rechazado', 'Advertencia')),
                severidad TEXT NOT NULL CHECK(severidad IN ('Baja', 'Media', 'Alta', 'Critica')),
                color_semaforo TEXT NOT NULL CHECK(color_semaforo IN ('Verde', 'Amarillo', 'Rojo')),
                mensaje TEXT NOT NULL,
                detalle_json TEXT,
                fecha_validacion TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (lote_id) REFERENCES lotes(lote_id)
            )
        """)
        # 8. Logs Auditoria
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs_auditoria (
                evento_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                tipo_actor TEXT NOT NULL,
                accion TEXT NOT NULL,
                punto_cadena INTEGER NOT NULL,
                entidad_tipo TEXT NOT NULL,
                entidad_id TEXT NOT NULL,
                hash_anterior TEXT,
                hash_actual TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                ip_origen TEXT,
                es_valido INTEGER DEFAULT 1
            )
        """)
        # 9. Registro Cargas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registro_cargas (
                id TEXT PRIMARY KEY,
                file_hash TEXT UNIQUE,
                tipo_archivo TEXT NOT NULL,
                estado TEXT NOT NULL CHECK(estado IN ('EN_COLA', 'PROCESANDO', 'COMPLETADO', 'FALLIDO')),
                resultado TEXT,
                fecha_creacion TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    finally:
        conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

# ──────────────────────────────────────────────
# CRYPTOGRAPHIC CHAIN LOGIC
# ──────────────────────────────────────────────

def compute_hash(payload: dict, timestamp: str, actor_id: str, hash_anterior: Optional[str]) -> str:
    payload_str = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    raw = "|".join([
        hash_anterior or "GENESIS",
        actor_id,
        timestamp,
        payload_str
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def get_last_hash(entidad_id: str) -> Optional[str]:
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT hash_actual FROM logs_auditoria
            WHERE entidad_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (entidad_id,)).fetchone()
        return row["hash_actual"] if row else None
    finally:
        conn.close()

def registrar_evento(
    actor_id: str,
    tipo_actor: str,
    accion: str,
    punto_cadena: int,
    entidad_tipo: str,
    entidad_id: str,
    payload: dict
) -> dict:
    evento_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()
    hash_anterior = get_last_hash(entidad_id)
    hash_actual = compute_hash(payload, timestamp, actor_id, hash_anterior)

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO logs_auditoria
            (evento_id, timestamp, actor_id, tipo_actor, accion,
             punto_cadena, entidad_tipo, entidad_id, hash_anterior, hash_actual, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            evento_id, timestamp, actor_id, tipo_actor, accion,
            punto_cadena, entidad_tipo, entidad_id, hash_anterior, hash_actual,
            json.dumps(payload, ensure_ascii=False)
        ))
        conn.commit()
    finally:
        conn.close()

    return {
        "evento_id": evento_id,
        "timestamp": timestamp,
        "hash_anterior": hash_anterior,
        "hash_actual": hash_actual
    }

# ──────────────────────────────────────────────
# PIDE HEADER EXTRACTOR
# ──────────────────────────────────────────────

def get_pide_headers(
    x_pide_rol: Optional[str] = Header(None, alias="X-PIDE-Rol"),
    x_pide_ruc: Optional[str] = Header(None, alias="X-PIDE-RUC"),
    x_pide_dni: Optional[str] = Header(None, alias="X-PIDE-DNI"),
    x_pide_placa: Optional[str] = Header(None, alias="X-PIDE-Placa"),
    x_pide_serfor: Optional[str] = Header(None, alias="X-PIDE-Serfor")
):
    if not x_pide_rol:
        raise HTTPException(status_code=400, detail="X-PIDE-Rol header is required")
    allowed_roles = {'Regente', 'Titular', 'OSINFOR', 'Transportista', 'Operador_CTP'}
    if x_pide_rol not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Invalid role: {x_pide_rol}")
    return {
        "rol": x_pide_rol,
        "ruc": x_pide_ruc,
        "dni": x_pide_dni,
        "placa": x_pide_placa,
        "serfor": x_pide_serfor
    }

# ──────────────────────────────────────────────
# TEST & RESET ENDPOINTS
# ──────────────────────────────────────────────

@app.post("/api/v1/test/reset")
def reset_db():
    if DB_PATH.exists():
        try:
            os.remove(DB_PATH)
        except Exception as e:
            pass
    init_db()
    
    # Seed Titulares & Titulos Habilitantes
    conn = get_connection()
    try:
        conn.execute("INSERT INTO titulares (ruc_dni, nombre, direccion) VALUES ('RUC-12345678901', 'Productor Bosque SAC', 'Madre de Dios')")
        conn.execute("INSERT INTO titulares (ruc_dni, nombre, direccion) VALUES ('RUC-09876543210', 'ArborCorp Peru', 'Loreto')")
        
        conn.execute("INSERT INTO titulos_habilitantes (titulo_id, titular_id, concesion_predio, ubicacion) VALUES ('TH-001', 'RUC-12345678901', 'Concesion Shihuahuaco 1', 'Madre de Dios')")
        conn.execute("INSERT INTO titulos_habilitantes (titulo_id, titular_id, concesion_predio, ubicacion) VALUES ('TH-002', 'RUC-09876543210', 'Concesion Cumala 2', 'Loreto')")
        conn.commit()
    finally:
        conn.close()
    return {"mensaje": "Database reset and seeded successfully"}

# ──────────────────────────────────────────────
# REGENTE FLOW: PLAN UPLOAD
# ──────────────────────────────────────────────

@app.post("/api/v1/planes/subir")
def subir_plan(file: UploadFile = File(...), pide: dict = Header(None)):
    # Handled via raw request headers manually to support test frameworks easily
    pass

@app.post("/api/v1/planes/subir_endpoint")
async def subir_plan_endpoint(
    file: UploadFile = File(...),
    x_pide_rol: Optional[str] = Header(None, alias="X-PIDE-Rol"),
    x_pide_dni: Optional[str] = Header(None, alias="X-PIDE-DNI")
):
    if not x_pide_rol:
        raise HTTPException(status_code=400, detail="X-PIDE-Rol is required")
    if x_pide_rol != 'Regente':
        raise HTTPException(status_code=403, detail="Only Regente can upload forest management plans")
    if not x_pide_dni:
        raise HTTPException(status_code=400, detail="X-PIDE-DNI is required for Regente role")

    # Save temp file
    content = await file.read()
    temp_path = Path(f"temp_plan_{uuid.uuid4().hex[:8]}.xlsx")
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        df = pd.read_excel(temp_path, engine='openpyxl')
        required_cols = {'titulo_habilitante_id', 'plan_id', 'version', 'fecha_aprobacion', 'arbol_id', 'especie', 'volumen_censado'}
        if not required_cols.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Missing columns. Expected: {list(required_cols)}")

        # Validate rows
        records = df.to_dict(orient="records")
        for r in records:
            vol = float(r["volumen_censado"])
            esp = str(r["especie"]).strip()
            if vol < 0:
                raise HTTPException(status_code=400, detail="Volume cannot be negative")
            if esp not in ALLOWED_SPECIES:
                raise HTTPException(status_code=400, detail=f"Unsupported species: {esp}")

        # Check title exists
        title_id = str(records[0]["titulo_habilitante_id"]).strip()
        plan_id = str(records[0]["plan_id"]).strip()
        new_version = int(records[0]["version"])
        fecha_aprobacion = str(records[0]["fecha_aprobacion"])

        conn = get_connection()
        try:
            title_exists = conn.execute("SELECT 1 FROM titulos_habilitantes WHERE titulo_id = ?", (title_id,)).fetchone()
            if not title_exists:
                raise HTTPException(status_code=400, detail=f"Title ID {title_id} does not exist")

            # Check existing versions
            existing_plans = conn.execute("""
                SELECT version, estado FROM planes_aprovechamiento
                WHERE titulo_id = ? ORDER BY version DESC
            """, (title_id,)).fetchall()

            if existing_plans:
                max_ver = existing_plans[0]["version"]
                if new_version <= max_ver:
                    raise HTTPException(status_code=400, detail=f"Uploaded plan version ({new_version}) must be higher than current version ({max_ver})")

                # Deactivate older plans
                conn.execute("""
                    UPDATE planes_aprovechamiento
                    SET estado = 'Actualizado'
                    WHERE titulo_id = ?
                """, (title_id,))

            # Insert new plan
            conn.execute("""
                INSERT INTO planes_aprovechamiento (plan_id, titulo_id, version, fecha_aprobacion, estado, documento_pdf_hash)
                VALUES (?, ?, ?, ?, 'Aprobado', ?)
            """, (plan_id, title_id, new_version, fecha_aprobacion, hashlib.sha256(content).hexdigest()[:16]))

            # Insert trees
            for r in records:
                arbol_id = str(r["arbol_id"]).strip()
                vol = float(r["volumen_censado"])
                esp = str(r["especie"]).strip()

                conn.execute("""
                    INSERT OR REPLACE INTO censo_forestal (arbol_id, plan_id, especie, volumen_autorizado, volumen_movilizado)
                    VALUES (?, ?, ?, ?, 0.0)
                """, (arbol_id, plan_id, esp, vol))

            conn.commit()
        finally:
            conn.close()

        # Log audit
        registrar_evento(
            actor_id=x_pide_dni,
            tipo_actor="Regente",
            accion="INGESTAR_PLAN",
            punto_cadena=1,
            entidad_tipo="Plan",
            entidad_id=plan_id,
            payload={"plan_id": plan_id, "titulo_id": title_id, "version": new_version}
        )

        return {"mensaje": "Plan subido con éxito", "plan_id": plan_id, "version": new_version}

    finally:
        if temp_path.exists():
            os.remove(temp_path)

# Alternate route path for ease
@app.post("/api/v1/planes/subir")
async def subir_plan_legacy(
    file: UploadFile = File(...),
    x_pide_rol: Optional[str] = Header(None, alias="X-PIDE-Rol"),
    x_pide_dni: Optional[str] = Header(None, alias="X-PIDE-DNI")
):
    return await subir_plan_endpoint(file, x_pide_rol, x_pide_dni)


# ──────────────────────────────────────────────
# OPERATIONS REGISTRATION
# ──────────────────────────────────────────────

class OperacionRequest(BaseModel):
    tipo_operacion: str
    punto_cadena: int
    arbol_id: Optional[str] = None
    troza_id: Optional[str] = None
    lote_id: Optional[str] = None
    parcela_corta: str
    especie: str
    volumen: float
    numero_gtf: Optional[str] = None
    actor_id: str
    fecha: str
    observacion: Optional[str] = None

@app.post("/api/v1/operaciones/registrar", status_code=201)
def registrar_operacion(
    payload: OperacionRequest,
    x_pide_rol: Optional[str] = Header(None, alias="X-PIDE-Rol"),
    x_pide_ruc: Optional[str] = Header(None, alias="X-PIDE-RUC"),
    x_pide_dni: Optional[str] = Header(None, alias="X-PIDE-DNI"),
    x_pide_placa: Optional[str] = Header(None, alias="X-PIDE-Placa")
):
    if not x_pide_rol:
        raise HTTPException(status_code=400, detail="X-PIDE-Rol is required")

    # Determine Title ID and Titular ID of target resource
    title_id = None
    titular_id = None

    conn = get_connection()
    try:
        if payload.arbol_id:
            # Derived from tree censo
            tree_row = conn.execute("""
                SELECT c.plan_id, c.volumen_autorizado, c.volumen_movilizado, c.estado, p.titulo_id, t.titular_id
                FROM censo_forestal c
                JOIN planes_aprovechamiento p ON c.plan_id = p.plan_id
                JOIN titulos_habilitantes t ON p.titulo_id = t.titulo_id
                WHERE c.arbol_id = ? AND p.estado = 'Aprobado'
            """, (payload.arbol_id,)).fetchone()
            if tree_row:
                title_id = tree_row["titulo_id"]
                titular_id = tree_row["titular_id"]
        elif payload.lote_id:
            # Derived from Lote
            lote_row = conn.execute("""
                SELECT titulo_id, titular_id FROM lotes WHERE lote_id = ?
            """, (payload.lote_id,)).fetchone()
            if lote_row:
                title_id = lote_row["titulo_id"]
                titular_id = lote_row["titular_id"]
    finally:
        conn.close()

    # Ownership validation
    if x_pide_rol == 'Titular':
        if not x_pide_ruc:
            raise HTTPException(status_code=400, detail="X-PIDE-RUC header is required for Titular")
        if titular_id and titular_id != x_pide_ruc:
            raise HTTPException(status_code=403, detail="Forbbiden: Logged-in Titular does not own the target forest Title")

    # Perform active plan verification
    if not title_id:
        # Check if the operations is logged without approved plan
        raise HTTPException(status_code=400, detail="No active approved forest management plan found for this operation")

    # Volume and balance validation
    color_semaforo = "Verde"
    mensaje_val = "Operación aprobada"
    resultado_val = "Aprobado"
    severidad_val = "Baja"

    conn = get_connection()
    try:
        if payload.arbol_id:
            tree = conn.execute("SELECT * FROM censo_forestal WHERE arbol_id = ?", (payload.arbol_id,)).fetchone()
            if not tree:
                color_semaforo = "Rojo"
                mensaje_val = f"Árbol ID {payload.arbol_id} no registrado en el censo."
                resultado_val = "Rechazado"
                severidad_val = "Critica"
            elif tree["estado"] == "FRAUDE_DETECTADO":
                color_semaforo = "Rojo"
                mensaje_val = f"Bloqueo: Árbol origen {payload.arbol_id} suspendido por fraude."
                resultado_val = "Rechazado"
                severidad_val = "Critica"
            else:
                rem = tree["volumen_autorizado"] - tree["volumen_movilizado"]
                if payload.volumen < 0:
                    raise HTTPException(status_code=400, detail="Volume cannot be negative")
                elif payload.volumen <= rem:
                    # Update mobilized volume
                    conn.execute("""
                        UPDATE censo_forestal
                        SET volumen_movilizado = volumen_movilizado + ?
                        WHERE arbol_id = ?
                    """, (payload.volumen, payload.arbol_id))
                    conn.commit()
                else:
                    excess = payload.volumen - rem
                    tolerance = rem * 0.05
                    if excess <= tolerance:
                        # Allowed with warning (Amarillo)
                        conn.execute("""
                            UPDATE censo_forestal
                            SET volumen_movilizado = volumen_movilizado + ?
                            WHERE arbol_id = ?
                        """, (payload.volumen, payload.arbol_id))
                        conn.commit()
                        color_semaforo = "Amarillo"
                        mensaje_val = f"Exceso menor de volumen ({excess:.2f} m3) dentro de la tolerancia de 5%."
                        resultado_val = "Advertencia"
                        severidad_val = "Media"
                    else:
                        color_semaforo = "Rojo"
                        mensaje_val = f"Sobreexplotación crítica de volumen: {payload.volumen:.2f} m3 excede el balance restante ({rem:.2f} m3)."
                        resultado_val = "Rechazado"
                        severidad_val = "Alta"
    finally:
        conn.close()

    # CTP Rendement Check
    if payload.tipo_operacion == 'Transformacion' and payload.lote_id:
        conn = get_connection()
        try:
            lote = conn.execute("SELECT volumen_total FROM lotes WHERE lote_id = ?", (payload.lote_id,)).fetchone()
            if lote:
                # Sum already logged transformations
                prev_trans = conn.execute("""
                    SELECT SUM(volumen) as total FROM operaciones
                    WHERE lote_id = ? AND tipo_operacion = 'Transformacion'
                """, (payload.lote_id,)).fetchone()
                prev_total = prev_trans["total"] or 0.0
                curr_total = prev_total + payload.volumen
                rendement = (curr_total / lote["volumen_total"]) * 100.0
                
                if rendement > 60.0:
                    color_semaforo = "Rojo"
                    mensaje_val = f"Alerta de Blanqueo: Rendimiento de aserrío físicamente imposible ({rendement:.2f}%). Supera el máximo biológico (60%)"
                    resultado_val = "Rechazado"
                    severidad_val = "Alta"
                elif rendement > 55.0:
                    color_semaforo = "Amarillo"
                    mensaje_val = f"Rendimiento inusualmente alto ({rendement:.2f}%). Requiere auditoría ocular en CTP"
                    resultado_val = "Advertencia"
                    severidad_val = "Media"
        finally:
            conn.close()

    # If Lote is target, update validation and Lote tables
    target_lote_id = payload.lote_id or f"LOT-{uuid.uuid4().hex[:6].upper()}"
    
    # Save operation
    op_id = f"OP-{uuid.uuid4().hex[:8].upper()}"
    conn = get_connection()
    try:
        # Ensure Lote exists for audit/linkage (or auto-create for simple flows)
        if payload.lote_id:
            lote_exists = conn.execute("SELECT 1 FROM lotes WHERE lote_id = ?", (payload.lote_id,)).fetchone()
            if not lote_exists:
                conn.execute("""
                    INSERT INTO lotes (lote_id, numero_gtf, titulo_id, titular_id, parcela_corta, especie, volumen_total, color_semaforo, mensaje_validacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (payload.lote_id, payload.numero_gtf or "GTF-MOCK", title_id or "TH-001", titular_id or "RUC-12345678901", payload.parcela_corta, payload.especie, payload.volumen, color_semaforo, mensaje_val))

        conn.execute("""
            INSERT INTO operaciones
            (operacion_id, tipo_operacion, punto_cadena, arbol_id, troza_id, lote_id,
             parcela_corta, especie, volumen, numero_gtf, actor_id, fecha, observacion, estado_validacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            op_id, payload.tipo_operacion, payload.punto_cadena, payload.arbol_id, payload.troza_id,
            payload.lote_id, payload.parcela_corta, payload.especie, payload.volumen, payload.numero_gtf,
            payload.actor_id, payload.fecha, payload.observacion, resultado_val
        ))

        # Insert validation record
        val_id = f"VAL-{uuid.uuid4().hex[:8].upper()}"
        conn.execute("""
            INSERT INTO validaciones (validacion_id, lote_id, regla, resultado, severidad, color_semaforo, mensaje)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (val_id, target_lote_id, "balance_volumen" if payload.arbol_id else "rendimiento_ctp", resultado_val, severidad_val, color_semaforo, mensaje_val))

        # Update Lote status
        conn.execute("""
            UPDATE lotes
            SET color_semaforo = ?, mensaje_validacion = ?, estado_validacion = 'Validado'
            WHERE lote_id = ?
        """, (color_semaforo, mensaje_val, target_lote_id))

        conn.commit()
    finally:
        conn.close()

    # Cryptographic log
    registrar_evento(
        actor_id=payload.actor_id,
        tipo_actor=x_pide_rol,
        accion=f"REGISTRAR_{payload.tipo_operacion.upper()}",
        punto_cadena=payload.punto_cadena,
        entidad_tipo="Lote" if payload.lote_id else "Operacion",
        entidad_id=target_lote_id,
        payload=payload.model_dump()
    )

    return {
        "mensaje": "Operación registrada con éxito",
        "operacion_id": op_id,
        "validacion": {
            "resultado": resultado_val,
            "color_semaforo": color_semaforo,
            "mensaje": mensaje_val
        }
    }


# ──────────────────────────────────────────────
# ASYNCHRONOUS LOAD ARCHIVO
# ──────────────────────────────────────────────

def procesar_cargas_background(job_id: str, temp_file_path: str, tipo_archivo: str):
    conn = get_connection()
    try:
        conn.execute("UPDATE registro_cargas SET estado = 'PROCESANDO' WHERE id = ?", (job_id,))
        conn.commit()

        df = pd.read_excel(temp_file_path, engine='openpyxl')
        df = df.fillna("")
        records = df.to_dict(orient="records")

        if tipo_archivo == "operaciones":
            for r in records:
                vol = float(r["volumen"])
                if vol < 0:
                    raise ValueError(f"Volumen no puede ser negativo: {vol}")
                esp = str(r["especie"]).strip()
                if esp not in ALLOWED_SPECIES:
                    raise ValueError(f"Unsupported species: {esp}")

                # Save operations in DB
                op_id = str(r["operacion_id"]).strip()
                tipo_op = str(r["tipo_operacion"]).strip()
                arbol_id = str(r.get("arbol_id", "")).strip() or None
                troza_id = str(r.get("troza_id", "")).strip() or None
                lote_id = str(r.get("lote_id", "")).strip() or None
                parcela = str(r["parcela_corta"]).strip()
                fecha = str(r["fecha"]).strip()
                num_gtf = str(r.get("numero_gtf", "")).strip() or None

                # Substract balance
                title_id = "TH-001"
                titular_id = "RUC-12345678901"
                
                # Check plan active and update balance if arbol is present
                if arbol_id:
                    tree_row = conn.execute("""
                        SELECT c.volumen_autorizado, c.volumen_movilizado
                        FROM censo_forestal c
                        JOIN planes_aprovechamiento p ON c.plan_id = p.plan_id
                        WHERE c.arbol_id = ? AND p.estado = 'Aprobado'
                    """, (arbol_id,)).fetchone()
                    if tree_row:
                        conn.execute("""
                            UPDATE censo_forestal
                            SET volumen_movilizado = volumen_movilizado + ?
                            WHERE arbol_id = ?
                        """, (vol, arbol_id))

                # Insert operations record
                conn.execute("""
                    INSERT INTO operaciones (operacion_id, tipo_operacion, punto_cadena, arbol_id, troza_id, lote_id, parcela_corta, especie, volumen, numero_gtf, actor_id, fecha)
                    VALUES (?, ?, 2, ?, ?, ?, ?, ?, ?, ?, 'ACTOR-LOAD', ?)
                """, (op_id, tipo_op, arbol_id, troza_id, lote_id, parcela, esp, vol, num_gtf, fecha))

        elif tipo_archivo == "balances":
            for r in records:
                # Mock handling for balance load
                pass
        elif tipo_archivo == "lotes":
            for r in records:
                lote_id = str(r["lote_id"]).strip()
                num_gtf = str(r["numero_gtf"]).strip()
                th_id = str(r.get("titulo_habilitante_id", "TH-001")).strip()
                titular = str(r.get("titular", "RUC-12345678901")).strip()
                parcela = str(r["parcela_corta"]).strip()
                especie = str(r["especie"]).strip()
                vol = float(r["volumen_total"])
                
                conn.execute("""
                    INSERT OR IGNORE INTO lotes (lote_id, numero_gtf, titulo_id, titular_id, parcela_corta, especie, volumen_total, color_semaforo, mensaje_validacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Verde', 'Lote pre-cargado asíncronamente.')
                """, (lote_id, num_gtf, th_id, titular, parcela, especie, vol))

        conn.commit()
        conn.execute("UPDATE registro_cargas SET estado = 'COMPLETADO', resultado = ? WHERE id = ?", (json.dumps({"registros": len(records)}), job_id))
        conn.commit()

    except Exception as e:
        conn.rollback()
        conn.execute("UPDATE registro_cargas SET estado = 'FALLIDO', resultado = ? WHERE id = ?", (json.dumps({"error": str(e)}), job_id))
        conn.commit()
    finally:
        conn.close()
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/api/v1/trazabilidad/cargar-archivo", status_code=202)
async def cargar_archivo(
    background_tasks: BackgroundTasks,
    tipo_archivo: str,
    file: UploadFile = File(...)
):
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    conn = get_connection()
    try:
        # Idempotencia
        carga = conn.execute("SELECT * FROM registro_cargas WHERE file_hash = ? AND estado != 'FALLIDO'", (file_hash,)).fetchone()
        if carga:
            return {
                "mensaje": "Archivo ya procesado o en cola (Idempotencia)",
                "job_id": carga["id"],
                "estado": carga["estado"],
                "resultado": json.loads(carga["resultado"]) if carga["resultado"] else None
            }

        job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        conn.execute("""
            INSERT INTO registro_cargas (id, file_hash, tipo_archivo, estado)
            VALUES (?, ?, ?, 'EN_COLA')
        """, (job_id, file_hash, tipo_archivo))
        conn.commit()
    finally:
        conn.close()

    temp_file_path = f"temp_load_{job_id}.xlsx"
    with open(temp_file_path, "wb") as f:
        f.write(content)

    background_tasks.add_task(procesar_cargas_background, job_id, temp_file_path, tipo_archivo)

    return {
        "mensaje": "Archivo recibido y en cola para procesamiento",
        "job_id": job_id,
        "estado": "EN_COLA"
    }

@app.get("/api/v1/trazabilidad/estado/{job_id}")
def obtener_estado_carga(job_id: str):
    conn = get_connection()
    try:
        carga = conn.execute("SELECT * FROM registro_cargas WHERE id = ?", (job_id,)).fetchone()
        if not carga:
            raise HTTPException(status_code=404, detail="Carga no encontrada")
        return {
            "job_id": carga["id"],
            "tipo_archivo": carga["tipo_archivo"],
            "estado": carga["estado"],
            "resultado": json.loads(carga["resultado"]) if carga["resultado"] else None,
            "fecha_creacion": carga["fecha_creacion"]
        }
    finally:
        conn.close()

# ──────────────────────────────────────────────
# TIMELINE TIMELINE
# ──────────────────────────────────────────────

@app.get("/api/v1/trazabilidad/timeline/{id_lote}")
def obtener_timeline(id_lote: str):
    conn = get_connection()
    try:
        lote = conn.execute("SELECT * FROM lotes WHERE lote_id = ?", (id_lote,)).fetchone()
        if not lote:
            raise HTTPException(status_code=404, detail="Lote no encontrado")

        ops = conn.execute("""
            SELECT * FROM operaciones WHERE lote_id = ? OR numero_gtf = ?
        """, (id_lote, lote["numero_gtf"])).fetchall()

        timeline = []
        for op in ops:
            timeline.append({
                "punto": op["punto_cadena"],
                "tipo": op["tipo_operacion"],
                "entidad_id": op["operacion_id"],
                "fecha": op["fecha"],
                "actor_id": op["actor_id"],
                "detalle": f"Especie: {op['especie']}, Vol: {op['volumen']}m3"
            })

        # Get last hash
        last_hash = get_last_hash(id_lote)

        return {
            "lote_id": lote["lote_id"],
            "estado_actual": lote["estado_validacion"],
            "color_semaforo": lote["color_semaforo"],
            "mensaje": lote["mensaje_validacion"] or "Sin mensaje",
            "hash_ultimo_evento": last_hash,
            "timeline": timeline
        }
    finally:
        conn.close()

# ──────────────────────────────────────────────
# REPORTES DE FALLAS
# ──────────────────────────────────────────────

@app.get("/api/v1/reportes/fallas")
def obtener_fallas():
    conn = get_connection()
    try:
        alertas = conn.execute("""
            SELECT v.*, l.numero_gtf, l.titular_id as titular
            FROM validaciones v
            JOIN lotes l ON v.lote_id = l.lote_id
            WHERE v.color_semaforo IN ('Rojo', 'Amarillo')
        """).fetchall()
        
        resultado = [dict(a) for a in alertas]
        return {
            "total_alertas": len(resultado),
            "reportes": resultado
        }
    finally:
        conn.close()

# ──────────────────────────────────────────────
# SUPERVISION: OSINFOR CASCADA RETROACTIVA
# ──────────────────────────────────────────────

class PenalizacionRequest(BaseModel):
    arbol_id: str
    motivo: str

@app.post("/api/v1/supervision/penalizar-origen")
def penalizar_origen(
    payload: PenalizacionRequest,
    x_pide_rol: Optional[str] = Header(None, alias="X-PIDE-Rol")
):
    if not x_pide_rol or x_pide_rol != 'OSINFOR':
        raise HTTPException(status_code=403, detail="Forbidden: OSINFOR role required")

    conn = get_connection()
    lotes_afectados = set()
    try:
        # Update tree
        conn.execute("UPDATE censo_forestal SET estado = 'FRAUDE_DETECTADO' WHERE arbol_id = ?", (payload.arbol_id,))
        
        # Track ops
        ops = conn.execute("SELECT DISTINCT lote_id FROM operaciones WHERE arbol_id = ?", (payload.arbol_id,)).fetchall()
        for op in ops:
            if op["lote_id"]:
                lotes_afectados.add(op["lote_id"])

        alerta_msg = "[ALERTA RETROACTIVA OSINFOR]: El árbol origen de este recurso fue declarado FALSO tras supervisión ex-post en bosque. Infracción D.L. 1085."

        for lid in lotes_afectados:
            lote_row = conn.execute("SELECT mensaje_validacion FROM lotes WHERE lote_id = ?", (lid,)).fetchone()
            curr_msg = lote_row["mensaje_validacion"] if lote_row else ""
            new_msg = f"{alerta_msg} | {curr_msg}" if curr_msg else alerta_msg

            conn.execute("""
                UPDATE lotes
                SET color_semaforo = 'Rojo',
                    mensaje_validacion = ?,
                    estado_validacion = 'Validado'
                WHERE lote_id = ?
            """, (new_msg, lid))

            val_id = f"VAL-{uuid.uuid4().hex[:8].upper()}"
            conn.execute("""
                INSERT INTO validaciones (validacion_id, lote_id, regla, resultado, severidad, color_semaforo, mensaje)
                VALUES (?, ?, 'supervision_expost', 'Rechazado', 'Critica', 'Rojo', ?)
            """, (val_id, lid, payload.motivo))

        conn.commit()
    finally:
        conn.close()

    # Log events
    registrar_evento(
        actor_id="OSINFOR-SUPERVISOR",
        tipo_actor="OSINFOR",
        accion="BLOQUEAR_LOTE",
        punto_cadena=1,
        entidad_tipo="Operacion",
        entidad_id=payload.arbol_id,
        payload={"arbol_id": payload.arbol_id, "motivo": payload.motivo}
    )

    for lid in lotes_afectados:
        registrar_evento(
            actor_id="OSINFOR-SUPERVISOR",
            tipo_actor="OSINFOR",
            accion="BLOQUEAR_LOTE",
            punto_cadena=3,
            entidad_tipo="Lote",
            entidad_id=lid,
            payload={"arbol_id": payload.arbol_id, "motivo": payload.motivo}
        )

    return {
        "mensaje": "Penalización retroactiva aplicada con éxito",
        "arbol_id": payload.arbol_id,
        "lotes_afectados": list(lotes_afectados)
    }

# ──────────────────────────────────────────────
# QUERY BALANCE DIRECTLY FOR TESTS
# ──────────────────────────────────────────────

@app.get("/api/v1/planes/balance/{titulo_id}/{especie}")
def obtener_balance(
    titulo_id: str,
    especie: str,
    x_pide_rol: Optional[str] = Header(None, alias="X-PIDE-Rol"),
    x_pide_ruc: Optional[str] = Header(None, alias="X-PIDE-RUC")
):
    conn = get_connection()
    try:
        # Check ownership if Titular
        if x_pide_rol == 'Titular':
            if not x_pide_ruc:
                raise HTTPException(status_code=400, detail="X-PIDE-RUC is required for Titular")
            title = conn.execute("SELECT titular_id FROM titulos_habilitantes WHERE titulo_id = ?", (titulo_id,)).fetchone()
            if title and title["titular_id"] != x_pide_ruc:
                raise HTTPException(status_code=403, detail="Forbidden: Logged-in Titular does not own the target forest Title")

        # Find active plan
        plan = conn.execute("""
            SELECT * FROM planes_aprovechamiento
            WHERE titulo_id = ? AND estado = 'Aprobado'
        """, (titulo_id,)).fetchone()
        
        if not plan:
            raise HTTPException(status_code=404, detail="No active approved plan found")

        # Sum authorized and mobilized volumes
        stats = conn.execute("""
            SELECT SUM(volumen_autorizado) as aut, SUM(volumen_movilizado) as mov
            FROM censo_forestal
            WHERE plan_id = ? AND especie = ? AND estado = 'Autorizado'
        """, (plan["plan_id"], especie)).fetchone()

        vol_aut = stats["aut"] or 0.0
        vol_mov = stats["mov"] or 0.0

        return {
            "plan_id": plan["plan_id"],
            "version": plan["version"],
            "especie": especie,
            "volumen_autorizado": vol_aut,
            "volumen_movilizado": vol_mov,
            "saldo_disponible": vol_aut - vol_mov
        }
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_api:app", host="127.0.0.1", port=8099, log_level="info")
