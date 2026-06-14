"""
ArborTrust - api/main.py
==========================
MÓDULO 4: Diseño de Endpoints de la API (FastAPI)

Provee la interfaz para registrar operaciones y consultar trazabilidad.
Integra la bitácora de integridad (SHA-256) y el motor de validación.
"""

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timezone
import sys
from pathlib import Path

# Configurar PYTHONPATH para importar módulos locales
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from database import get_connection
from engine.hashing import registrar_evento, Acciones
from engine.validation import validar_lote

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="ArborTrust API",
    description="API para Trazabilidad y Pasaporte Digital Forestal",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# MODELOS DE DATOS (Pydantic)
# ──────────────────────────────────────────────

class OperacionRequest(BaseModel):
    tipo_operacion: str  # 'Tala', 'Trozado', 'Despacho', 'Lote', 'Transformacion'
    punto_cadena: int    # 2, 3, 4
    arbol_id: Optional[str] = None
    troza_id: Optional[str] = None
    lote_id: Optional[str] = None
    parcela_corta: str
    especie: str
    volumen: float
    numero_gtf: Optional[str] = None
    actor_id: str
    tipo_actor: str = "Titular"
    fecha: str
    observacion: Optional[str] = None

class TrazabilidadNode(BaseModel):
    punto: int
    tipo: str
    entidad_id: str
    fecha: str
    actor_id: str
    detalle: str

class TrazabilidadTimelineResponse(BaseModel):
    lote_id: str
    estado_actual: str
    color_semaforo: str
    mensaje: str
    hash_ultimo_evento: Optional[str]
    timeline: List[TrazabilidadNode]

# ──────────────────────────────────────────────
# 1. REGISTRAR OPERACIONES (Puntos 2, 3 o 4)
# ──────────────────────────────────────────────

@app.post("/api/v1/operaciones/registrar", status_code=201)
def registrar_operacion(payload: OperacionRequest):
    """
    Ingresa datos de aprovechamiento (2), transporte (3) o transformación (4).
    1. Guarda en SQLite.
    2. Hashea el evento en logs_auditoria.
    3. Si afecta a un Lote, dispara el motor de validación.
    """
    op_id = f"OP-{uuid.uuid4().hex[:8].upper()}"
    
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO operaciones
            (operacion_id, tipo_operacion, punto_cadena, arbol_id, troza_id, lote_id,
             parcela_corta, especie, volumen, numero_gtf, actor_id, fecha, observacion)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (op_id, payload.tipo_operacion, payload.punto_cadena, payload.arbol_id,
              payload.troza_id, payload.lote_id, payload.parcela_corta, payload.especie,
              payload.volumen, payload.numero_gtf, payload.actor_id, payload.fecha,
              payload.observacion))
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    # Determinar acción para el log
    accion_map = {
        'Tala': Acciones.REGISTRAR_TALA,
        'Trozado': Acciones.REGISTRAR_TROZADO,
        'Despacho': Acciones.REGISTRAR_DESPACHO,
        'Transformacion': Acciones.INGRESO_CTP
    }
    accion = accion_map.get(payload.tipo_operacion, "OTRA_OPERACION")
    
    entidad_id = payload.lote_id if payload.lote_id else (payload.arbol_id or "GENERAL")

    # Hashear y registrar evento en Bitácora de Integridad
    log_result = registrar_evento(
        actor_id=payload.actor_id,
        tipo_actor=payload.tipo_actor,
        accion=accion,
        punto_cadena=payload.punto_cadena,
        entidad_tipo="Operacion",
        entidad_id=entidad_id,
        payload=payload.model_dump()
    )

    # Si hay un lote asociado, disparar validación (Semáforo de Riesgo)
    validacion_result = None
    if payload.lote_id:
        validacion_result = validar_lote(payload.lote_id)

    return {
        "mensaje": "Operación registrada con éxito",
        "operacion_id": op_id,
        "integridad": log_result,
        "validacion": validacion_result
    }

# ──────────────────────────────────────────────
# 2. LÍNEA DE TIEMPO DE TRAZABILIDAD
# ──────────────────────────────────────────────

@app.get("/api/v1/trazabilidad/timeline/{id_lote}", response_model=TrazabilidadTimelineResponse)
def obtener_timeline(id_lote: str):
    """
    Devuelve la estructura JSON para pintar la línea de tiempo visual
    del material: Árbol -> Trozas -> Despachos -> Lote.
    """
    conn = get_connection()
    try:
        # 1. Obtener Lote
        lote = conn.execute("SELECT * FROM lotes WHERE lote_id = ?", (id_lote,)).fetchone()
        if not lote:
            raise HTTPException(status_code=404, detail="Lote no encontrado")
        
        timeline = []
        
        # 2. Buscar operaciones conectadas al GTF del lote
        ops = conn.execute("""
            SELECT * FROM operaciones 
            WHERE numero_gtf = ? OR lote_id = ?
            ORDER BY fecha ASC
        """, (lote["numero_gtf"], id_lote)).fetchall()
        
        for op in ops:
            detalle = f"Especie: {op['especie']}, Vol: {op['volumen']}m3"
            if op['arbol_id']: detalle += f", Árbol: {op['arbol_id']}"
            if op['troza_id']: detalle += f", Troza: {op['troza_id']}"
            
            timeline.append(TrazabilidadNode(
                punto=op['punto_cadena'],
                tipo=op['tipo_operacion'],
                entidad_id=op['operacion_id'],
                fecha=op['fecha'],
                actor_id=op['actor_id'],
                detalle=detalle
            ))

        # Añadir evento del propio Lote (Transporte)
        timeline.append(TrazabilidadNode(
            punto=3,
            tipo="Registro_Lote",
            entidad_id=lote["lote_id"],
            fecha=lote["fecha_creacion"],
            actor_id=lote["titular"],
            detalle=f"GTF: {lote['numero_gtf']}, Vol: {lote['volumen_total']}m3"
        ))

        # Obtener último hash del lote
        hash_lote = conn.execute("""
            SELECT hash_actual FROM logs_auditoria 
            WHERE entidad_id = ? ORDER BY timestamp DESC LIMIT 1
        """, (id_lote,)).fetchone()

        return TrazabilidadTimelineResponse(
            lote_id=lote["lote_id"],
            estado_actual=lote["estado_validacion"],
            color_semaforo=lote["color_semaforo"],
            mensaje=lote["mensaje_validacion"] or "Sin mensaje",
            hash_ultimo_evento=hash_lote["hash_actual"] if hash_lote else None,
            timeline=timeline
        )
    finally:
        conn.close()

# ──────────────────────────────────────────────
# 3. REPORTES DE FALLAS (DASHBOARD FISCALIZADOR)
# ──────────────────────────────────────────────

@app.get("/api/v1/reportes/fallas")
def obtener_fallas():
    """
    Retorna todas las validaciones que resultaron en Rojo (Falla Crítica) 
    o Amarillo (Alerta), agrupadas para el Dashboard del Fiscalizador.
    """
    conn = get_connection()
    try:
        alertas = conn.execute("""
            SELECT v.validacion_id, v.lote_id, v.regla, v.color_semaforo, 
                   v.mensaje, v.fecha_validacion, l.numero_gtf, l.titular
            FROM validaciones v
            JOIN lotes l ON v.lote_id = l.lote_id
            WHERE v.color_semaforo IN ('Rojo', 'Amarillo')
            ORDER BY v.fecha_validacion DESC
        """).fetchall()
        
        resultado = []
        for a in alertas:
            resultado.append(dict(a))
            
        return {
            "total_alertas": len(resultado),
            "reportes": resultado
        }
    finally:
        conn.close()

# ──────────────────────────────────────────────
# PARA CORRER EN MODO DEV
# ──────────────────────────────────────────────
# python -m uvicorn api.main:app --reload --port 8000
