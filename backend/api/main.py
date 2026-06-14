"""
ArborTrust - api/main.py
==========================
MÓDULO 4: Diseño de Endpoints de la API (FastAPI)

Provee la interfaz para registrar operaciones y consultar trazabilidad.
Integra la bitácora de integridad (SHA-256) y el motor de validación.
"""

from fastapi import FastAPI, HTTPException, Body, BackgroundTasks, UploadFile, File, Header, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timezone
import sys
from pathlib import Path

# Configurar PYTHONPATH para importar módulos locales
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from database import get_connection, init_db, procesar_archivo_background, resolver_ruc, pide_rol_var, pide_ruc_var, pide_serfor_var, pide_dni_var, pide_placa_var
from engine.hashing import registrar_evento, Acciones
from engine.validation import validar_lote
from fastapi.responses import JSONResponse
import json
import urllib.parse

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

@app.middleware("http")
async def pide_headers_middleware(request: Request, call_next):
    path = request.url.path
    is_api = path.startswith("/api/v1/")
    
    # Extraer cadena de sesión
    sesion_str = request.headers.get("X-PIDE-Sesion") or request.headers.get("x-pide-sesion")
    sesion_data = {}
    if sesion_str:
        try:
            decoded_str = urllib.parse.unquote(sesion_str)
            sesion_data = json.loads(decoded_str)
        except Exception:
            try:
                sesion_data = json.loads(sesion_str)
            except Exception:
                pass
                
    # Extraer cabeceras individuales con respaldo en sesión
    rol = (
        request.headers.get("X-PIDE-Rol") or 
        request.headers.get("x-pide-rol") or 
        sesion_data.get("X-PIDE-Rol") or 
        sesion_data.get("rol")
    )
    ruc = (
        request.headers.get("X-PIDE-RUC") or 
        request.headers.get("x-pide-ruc") or 
        sesion_data.get("X-PIDE-RUC") or 
        sesion_data.get("ruc")
    )
    serfor = (
        request.headers.get("X-PIDE-Serfor") or 
        request.headers.get("x-pide-serfor") or 
        sesion_data.get("X-PIDE-Serfor") or 
        sesion_data.get("serfor") or 
        sesion_data.get("registro_serfor")
    )
    dni = (
        request.headers.get("X-PIDE-DNI") or 
        request.headers.get("x-pide-dni") or 
        sesion_data.get("X-PIDE-DNI") or 
        sesion_data.get("dni") or 
        sesion_data.get("dni_chofer")
    )
    placa = (
        request.headers.get("X-PIDE-Placa") or 
        request.headers.get("x-pide-placa") or 
        sesion_data.get("X-PIDE-Placa") or 
        sesion_data.get("placa") or 
        sesion_data.get("placa_vehiculo")
    )
    
    if is_api and not rol:
        return JSONResponse(
            status_code=401,
            content={"detail": "No autorizado: Falta sesión PIDE o rol en las cabeceras."}
        )
        
    token_rol = pide_rol_var.set(rol)
    token_ruc = pide_ruc_var.set(ruc)
    token_serfor = pide_serfor_var.set(serfor)
    token_dni = pide_dni_var.set(dni)
    token_placa = pide_placa_var.set(placa)
    
    try:
        response = await call_next(request)
    finally:
        pide_rol_var.reset(token_rol)
        pide_ruc_var.reset(token_ruc)
        pide_serfor_var.reset(token_serfor)
        pide_dni_var.reset(token_dni)
        pide_placa_var.reset(token_placa)
        
    return response


@app.on_event("startup")
def startup_event():
    init_db()


# ──────────────────────────────────────────────
# ENDPOINTS DE CARGA ASÍNCRONA E IDEMPOTENTE
# ──────────────────────────────────────────────

@app.post("/api/v1/trazabilidad/cargar-archivo", status_code=202)
async def cargar_archivo(
    background_tasks: BackgroundTasks,
    tipo_archivo: str,
    file: UploadFile = File(...)
):
    import hashlib
    import json
    
    rol = pide_rol_var.get()
    ruc = pide_ruc_var.get()
    
    # 0. Role-based Ingestion Security Validation (PIDE Simulation)
    if rol:
        if rol == "Transportista":
            raise HTTPException(status_code=403, detail="Acceso denegado: El transportista solo cuenta con permisos de consulta en ruta.")
        
        if rol in ("Regente", "ARFFS"):
            if tipo_archivo != "censo":
                raise HTTPException(status_code=400, detail=f"Acceso denegado: El rol {rol} solo puede cargar archivos de tipo 'censo'.")
        elif rol == "OSINFOR":
            if tipo_archivo != "balances":
                raise HTTPException(status_code=400, detail="Acceso denegado: El rol OSINFOR solo puede cargar archivos de tipo 'balances'.")
        elif rol in ("Titular", "Operador_CTP"):
            if tipo_archivo != "operaciones":
                raise HTTPException(status_code=400, detail=f"Acceso denegado: El rol {rol} solo puede cargar archivos de tipo 'operaciones'.")

    # Validación de formato y content-type
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Debe ser .xlsx")
        
    expected_mimetypes = ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
    if file.content_type not in expected_mimetypes:
        raise HTTPException(status_code=400, detail=f"Content-Type inválido. Debe ser {expected_mimetypes[0]}")

    # 1. Leer contenido para calcular hash SHA-256
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    
    conn = get_connection()
    try:
        # 2. Control de Idempotencia: Verificar si el hash ya existe y no falló
        carga = conn.execute("SELECT * FROM registro_cargas WHERE file_hash = ? AND estado != 'FALLIDO'", (file_hash,)).fetchone()
        if carga:
            resultado_data = None
            if carga["resultado"]:
                try:
                    resultado_data = json.loads(carga["resultado"])
                except Exception:
                    resultado_data = carga["resultado"]
            return {
                "mensaje": "Archivo ya procesado o en cola (Idempotencia)",
                "job_id": carga["id"],
                "estado": carga["estado"],
                "resultado": resultado_data
            }
            
        # 3. Registrar nuevo job
        job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        conn.execute("""
            INSERT INTO registro_cargas (id, file_hash, tipo_archivo, estado)
            VALUES (?, ?, ?, 'EN_COLA')
        """, (job_id, file_hash, tipo_archivo))
        conn.commit()
    finally:
        conn.close()
        
    # 4. Guardar archivo temporalmente
    temp_dir = Path("./temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / f"{job_id}.xlsx"
    
    with open(temp_file_path, "wb") as f:
        f.write(content)
        
    # 5. Agregar background task
    background_tasks.add_task(procesar_archivo_background, job_id, str(temp_file_path), tipo_archivo, rol, ruc)
    
    return {
        "mensaje": "Archivo recibido y en cola para procesamiento",
        "job_id": job_id,
        "estado": "EN_COLA"
    }


@app.get("/api/v1/trazabilidad/estado/{job_id}")
def obtener_estado_carga(job_id: str):
    import json
    
    conn = get_connection()
    try:
        carga = conn.execute("SELECT * FROM registro_cargas WHERE id = ?", (job_id,)).fetchone()
        if not carga:
            raise HTTPException(status_code=404, detail="Trabajo de carga no encontrado")
            
        resultado_data = None
        if carga["resultado"]:
            try:
                resultado_data = json.loads(carga["resultado"])
            except Exception:
                resultado_data = carga["resultado"]
                
        return {
            "job_id": carga["id"],
            "tipo_archivo": carga["tipo_archivo"],
            "estado": carga["estado"],
            "resultado": resultado_data,
            "fecha_creacion": carga["fecha_creacion"]
        }
    finally:
        conn.close()



# ──────────────────────────────────────────────
# MODELOS DE DATOS (Pydantic)
# ──────────────────────────────────────────────

class OperacionRequest(BaseModel):
    tipo_operacion: str  # 'Tala', 'Trozado', 'Despacho', 'Lote', 'Transformacion'
    punto_cadena: int    # 2, 3, 4
    arbol_id: Optional[str] = None
    id_arbol: Optional[str] = None
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
    ruc_institucion: Optional[str] = None
    registro_serfor: Optional[str] = None
    dni_chofer: Optional[str] = None
    placa_vehiculo: Optional[str] = None

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
def registrar_operacion(
    payload: OperacionRequest,
):
    """
    Ingresa datos de aprovechamiento (2), transporte (3) o transformación (4).
    1. Valida propiedad, planes activos y límites de volumen.
    2. Guarda en SQLite.
    3. Hashea el evento en logs_auditoria.
    4. Si afecta a un Lote, dispara el motor de validación.
    """
    import re
    op_id = f"OP-{uuid.uuid4().hex[:8].upper()}"
    target_arbol_id = payload.id_arbol or payload.arbol_id
    
    # 0. Resolviendo valores de identificación y rol estrictamente de ContextVars
    rol = pide_rol_var.get()
    ruc = pide_ruc_var.get()
    serfor = pide_serfor_var.get()
    dni = pide_dni_var.get()
    placa = pide_placa_var.get()
    
    if not rol:
        raise HTTPException(status_code=401, detail="No autorizado: Falta sesión PIDE o rol.")
        
    # Validaciones según rol y tipo de operación
    if rol not in ("Titular", "Operador_CTP", "Transportista"):
        raise HTTPException(status_code=403, detail=f"Acceso denegado: El rol {rol} no tiene permisos para registrar operaciones.")
        
    if rol == "Titular" or rol == "Operador_CTP":
        if not ruc:
            raise HTTPException(status_code=400, detail="Se requiere RUC para este rol.")
        if not re.match(r"^(10|20)\d{9}$", ruc):
            raise HTTPException(status_code=400, detail="Formato de RUC inválido.")
    elif rol == "Regente":
        if not serfor:
            raise HTTPException(status_code=400, detail="Se requiere Registro SERFOR para este rol.")
        if not re.match(r"^REG-SER-20\d{2}-\d{4}$", serfor):
            raise HTTPException(status_code=400, detail="Formato de Registro SERFOR inválido.")
    elif rol == "Transportista":
        if not dni:
            raise HTTPException(status_code=400, detail="Se requiere DNI para el transportista.")
        if not re.match(r"^\d{8}$", dni):
            raise HTTPException(status_code=400, detail="Formato de DNI inválido.")
        if not placa:
            raise HTTPException(status_code=400, detail="Se requiere placa del vehículo para el transportista.")
        if not re.match(r"^[A-Z0-9]{3}-[A-Z0-9]{3}$", placa):
            raise HTTPException(status_code=400, detail="Formato de placa inválido.")

    id_titular = ruc
    
    conn = get_connection()
    try:
        # 0. Resolviendo th_id para validaciones
        th_id = None
        if target_arbol_id:
            res_arb = conn.execute("SELECT p.id_titulo FROM censo_forestal c JOIN planes_aprovechamiento p ON c.id_plan = p.id_plan WHERE c.id_arbol = ?", (target_arbol_id,)).fetchone()
            if res_arb: th_id = res_arb["id_titulo"]
        if not th_id and payload.lote_id:
            res_lote = conn.execute("SELECT titulo_habilitante_id FROM lotes WHERE lote_id = ?", (payload.lote_id,)).fetchone()
            if res_lote: th_id = res_lote["titulo_habilitante_id"]
        
        target_th_id = th_id
        
        # Validación de relación Actor-Título (RUC)
        if rol == "Titular" and ruc and target_th_id:
            res_title = conn.execute("SELECT id_titular FROM titulos_habilitantes WHERE id_titulo = ?", (target_th_id,)).fetchone()
            if res_title and res_title["id_titular"] != ruc:
                raise HTTPException(status_code=403, detail=f"Acceso denegado: El Titulo Habilitante {target_th_id} no pertenece al Titular autenticado ({ruc}).")

        # Validación de Integridad de Plan (Debe existir un plan de aprovechamiento aprobado)
        plan_aprobado = None
        if target_th_id:
            plan_aprobado = conn.execute("SELECT 1 FROM planes_aprovechamiento WHERE id_titulo = ? AND estado = 'Aprobado'", (target_th_id,)).fetchone()
        if not plan_aprobado:
            raise HTTPException(status_code=400, detail="No existe un Plan de Aprovechamiento aprobado asociado a este título.")

        # Validación de Censo y Volumen Autorizado
        if target_arbol_id:
            arbol_row = conn.execute("""
                SELECT c.volumen_autorizado, p.estado as plan_estado, p.id_plan
                FROM censo_forestal c
                JOIN planes_aprovechamiento p ON c.id_plan = p.id_plan
                WHERE c.id_arbol = ?
            """, (target_arbol_id,)).fetchone()
            
            if not arbol_row:
                raise HTTPException(status_code=400, detail="El árbol no existe en el Censo Forestal.")
            
            if arbol_row["plan_estado"] in ("Vencido", "Actualizado"):
                raise HTTPException(status_code=400, detail="El Plan de Aprovechamiento de este árbol ya venció.")
            
            # Sumar volumen ya talado/aprovechado
            sum_vol = conn.execute("SELECT SUM(volumen) as total FROM operaciones WHERE id_arbol = ? AND tipo_operacion = 'Tala'", (target_arbol_id,)).fetchone()["total"] or 0.0
            if sum_vol + payload.volumen > arbol_row["volumen_autorizado"]:
                raise HTTPException(status_code=400, detail="El volumen ingresado excede el saldo de su Plan de Aprovechamiento vigente.")

        # Determinar actor_id para auditoría e inserción en base de datos
        audit_actor_id = ruc if (rol in ("Titular", "Operador_CTP") and ruc) else (serfor if (rol == "Regente" and serfor) else (f"{dni}/{placa}" if (rol == "Transportista" and dni and placa) else "AUTOR"))

        # Insertar operación
        conn.execute("""
            INSERT INTO operaciones
            (operacion_id, tipo_operacion, punto_cadena, id_arbol, troza_id, lote_id,
             parcela_corta, especie, volumen, numero_gtf, actor_id, ruc_institucion,
             registro_serfor, dni_chofer, placa_vehiculo, id_titular, fecha, observacion)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (op_id, payload.tipo_operacion, payload.punto_cadena, target_arbol_id,
              payload.troza_id, payload.lote_id, payload.parcela_corta, payload.especie,
              payload.volumen, payload.numero_gtf, audit_actor_id, ruc,
              serfor, dni, placa, id_titular, payload.fecha, payload.observacion))
        conn.commit()
    except HTTPException:
        raise
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
    
    entidad_id = payload.lote_id if payload.lote_id else (target_arbol_id or "GENERAL")

    log_result = registrar_evento(
        actor_id=audit_actor_id,
        tipo_actor=rol,
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
# 2. BÚSQUEDA DE TRAZABILIDAD
# ──────────────────────────────────────────────

@app.get("/api/v1/trazabilidad/buscar")
def buscar_trazabilidad(
    criterio: str,
    valor: Optional[str] = None,
):
    """
    Busca de manera polimórfica trazabilidad por árbol, GTF/lote o título habilitante,
    restringiendo el acceso según rol PIDE.
    """
    from database import buscar_trazabilidad_semantica
    
    rol = pide_rol_var.get()
    ruc = pide_ruc_var.get()
    
    target_criterio = criterio
    target_valor = valor
    
    if not target_valor:
        # Legacy auto-detect mode
        target_valor = criterio
        if target_valor.startswith("ARB-"):
            target_criterio = "arbol_id"
        elif target_valor.startswith("TH-"):
            target_criterio = "titulo_habilitante"
        else:
            target_criterio = "gtf"
            
    ruc_filtro = None
    if rol == "Titular":
        if not ruc:
            raise HTTPException(status_code=400, detail="Falta cabecera X-PIDE-RUC para autenticación de Titular.")
        ruc_filtro = ruc
        
    try:
        res = buscar_trazabilidad_semantica(target_criterio, target_valor, ruc_filtro)
        if not res:
            raise HTTPException(status_code=404, detail=f"No se encontró información para el criterio '{target_criterio}' con valor '{target_valor}'.")
        return res
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

# ──────────────────────────────────────────────
# 3. LÍNEA DE TIEMPO DE TRAZABILIDAD
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
        lote = conn.execute("SELECT * FROM lotes WHERE lote_id = ? AND ruc_titular = X-PIDE-RUC", (id_lote,)).fetchone()
        if not lote:
            exists = conn.execute("SELECT 1 FROM lotes WHERE lote_id = ?", (id_lote,)).fetchone()
            if exists:
                raise HTTPException(status_code=403, detail="Acceso denegado: El lote no pertenece a sus títulos habilitantes.")
            else:
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
            if op['id_arbol']: detalle += f", Árbol: {op['id_arbol']}"
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
            WHERE v.color_semaforo IN ('Rojo', 'Amarillo') AND ruc_titular = X-PIDE-RUC
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

class PenalizacionRequest(BaseModel):
    arbol_id: str
    id_arbol: Optional[str] = None
    motivo: str

@app.post("/api/v1/supervision/penalizar-origen")
def penalizar_origen(payload: PenalizacionRequest):
    """
    Endpoint administrativo para que OSINFOR declare un árbol del censo como falso.
    Desencadena una penalización en cascada sobre toda la cadena derivada.
    """
    from database import penalizar_arbol_retroactivo
    try:
        target_arbol_id = payload.id_arbol or payload.arbol_id
        resultado = penalizar_arbol_retroactivo(target_arbol_id, payload.motivo)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ──────────────────────────────────────────────
# 4. ENDPOINTS GOVTECH: TITULOS Y PLANES
# ──────────────────────────────────────────────

@app.get("/api/v1/titulos")
def obtener_titulos():
    """
    Devuelve los Títulos Habilitantes asociados al titular autenticado.
    Si es Regente, OSINFOR, o ARFFS, se devuelven todos.
    """
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM titulos_habilitantes WHERE ruc_titular = X-PIDE-RUC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.get("/api/v1/titulos/{id_titulo}/arboles")
def obtener_arboles_titulo(id_titulo: str):
    """
    Retorna el listado de árboles del censo asociados a un Título Habilitante,
    junto con su estado de aprovechamiento (Tala o Standing).
    """
    conn = get_connection()
    try:
        # Validate that the Titular owns this title if role is Titular
        check = conn.execute("SELECT 1 FROM titulos_habilitantes WHERE id_titulo = ? AND ruc_titular = X-PIDE-RUC", (id_titulo,)).fetchone()
        if not check:
            raise HTTPException(status_code=403, detail="Acceso denegado: El título habilitante no le pertenece.")
            
        rows = conn.execute("""
            SELECT c.id_arbol, c.id_especie, c.volumen_autorizado, c.estado as censo_estado,
                   (SELECT COUNT(*) FROM operaciones o WHERE o.id_arbol = c.id_arbol AND o.tipo_operacion = 'Tala') > 0 as talado
            FROM censo_forestal c
            JOIN planes_aprovechamiento p ON c.id_plan = p.id_plan
            WHERE p.id_titulo = ?
        """, (id_titulo,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@app.post("/api/v1/planes/subir", status_code=201)
async def subir_plan(
    file: UploadFile = File(...)
):
    """
    Sube un Plan de Aprovechamiento (.xlsx) de forma versionada.
    """
    import os
    rol = pide_rol_var.get()
    if rol not in ("Regente", "ARFFS"):
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo Regentes o ARFFS pueden subir planes de aprovechamiento.")
    
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Debe ser .xlsx")
        
    content = await file.read()
    
    temp_dir = Path("./temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / f"plan_{uuid.uuid4().hex[:8]}.xlsx"
    with open(temp_file_path, "wb") as f:
        f.write(content)
    
    from database import procesar_plan_xlsx
    try:
        result = procesar_plan_xlsx(str(temp_file_path))
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_file_path.exists():
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

# ──────────────────────────────────────────────
# PARA CORRER EN MODO DEV
# ──────────────────────────────────────────────
# python -m uvicorn api.main:app --reload --port 8000
