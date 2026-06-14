import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import get_connection


# ──────────────────────────────────────────────
# FUNCIÓN PRINCIPAL DE HASH
# ──────────────────────────────────────────────

def compute_hash(
    payload: dict,
    timestamp: str,
    actor_id: str,
    hash_anterior: str | None
) -> str:
    """
    Calcula SHA-256 del bloque actual.

    La entrada del hash es la concatenación de:
        hash_anterior + actor_id + timestamp + payload_ordenado

    Usar separadores fijos garantiza determinismo.
    """
    payload_str = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    raw = "|".join([
        hash_anterior or "GENESIS",
        actor_id,
        timestamp,
        payload_str,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ──────────────────────────────────────────────
# OBTENER EL ÚLTIMO HASH DE LA CADENA
# ──────────────────────────────────────────────

def get_last_hash(entidad_id: str | None = None) -> str | None:
    """
    Devuelve el hash_actual del último evento registrado.

    Si se pasa entidad_id, filtra la cadena de esa entidad específica.
    Si no, devuelve el último hash global (cadena maestra).

    Returns:
        str  → hash del último evento
        None → cadena vacía (primer evento es GENESIS)
    """
    conn = get_connection()
    try:
        if entidad_id:
            row = conn.execute("""
                SELECT hash_actual FROM logs_auditoria
                WHERE entidad_id = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (entidad_id,)).fetchone()
        else:
            row = conn.execute("""
                SELECT hash_actual FROM logs_auditoria
                ORDER BY timestamp DESC LIMIT 1
            """).fetchone()
        return row["hash_actual"] if row else None
    finally:
        conn.close()


# ──────────────────────────────────────────────
# REGISTRAR UN EVENTO EN LA BITÁCORA
# ──────────────────────────────────────────────

def registrar_evento(
    actor_id: str,
    tipo_actor: str,
    accion: str,
    punto_cadena: int,
    entidad_tipo: str,
    entidad_id: str,
    payload: dict,
    ip_origen: str | None = None,
) -> dict:
    """
    Registra un evento en logs_auditoria y calcula su hash en la cadena.

    Args:
        actor_id      : ID del actor
        tipo_actor    : 'Titular'|'Regente'|'ARFFS'|'SERFOR'|'OSINFOR'|'Transportista'|'Operador_CTP'
        accion        : Descripción de la acción ('REGISTRAR_TALA', 'EMITIR_GTF', etc.)
        punto_cadena  : 1=Planificación, 2=Aprovechamiento, 3=Transporte, 4=Transformación
        entidad_tipo  : 'Operacion' | 'Lote' | 'Transformacion' | 'Pasaporte'
        entidad_id    : ID de la entidad afectada (lote_id, operacion_id, etc.)
        payload       : dict con los datos relevantes del evento
        ip_origen     : IP del cliente (opcional)

    Returns:
        dict con evento_id y hash_actual generados
    """
    evento_id  = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    timestamp  = datetime.now(timezone.utc).isoformat()

    # Obtener el hash del evento anterior en la cadena de esta entidad
    hash_anterior = get_last_hash(entidad_id)

    # Calcular el hash del bloque actual
    hash_actual = compute_hash(
        payload=payload,
        timestamp=timestamp,
        actor_id=actor_id,
        hash_anterior=hash_anterior,
    )

    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO logs_auditoria
            (evento_id, timestamp, actor_id, tipo_actor, accion,
             punto_cadena, entidad_tipo, entidad_id,
             hash_anterior, hash_actual, payload_json, ip_origen)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            evento_id, timestamp, actor_id, tipo_actor, accion,
            punto_cadena, entidad_tipo, entidad_id,
            hash_anterior, hash_actual,
            json.dumps(payload, ensure_ascii=False),
            ip_origen,
        ))
        conn.commit()
    finally:
        conn.close()

    return {
        "evento_id": evento_id,
        "timestamp": timestamp,
        "hash_anterior": hash_anterior,
        "hash_actual": hash_actual,
    }


# ──────────────────────────────────────────────
# VERIFICAR INTEGRIDAD DE LA CADENA
# ──────────────────────────────────────────────

def verificar_cadena(entidad_id: str) -> dict:
    """
    Recorre todos los eventos de una entidad y verifica que la cadena
    de hashes sea coherente (ningún bloque fue alterado).

    Returns:
        {
            "cadena_integra": bool,
            "eventos_verificados": int,
            "primer_error": str | None,
        }
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT evento_id, timestamp, actor_id, payload_json,
                   hash_anterior, hash_actual
            FROM logs_auditoria
            WHERE entidad_id = ?
            ORDER BY timestamp ASC
        """, (entidad_id,)).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"cadena_integra": True, "eventos_verificados": 0, "primer_error": None}

    hash_esperado = None  # GENESIS
    for i, row in enumerate(rows):
        payload = json.loads(row["payload_json"])
        hash_calculado = compute_hash(
            payload=payload,
            timestamp=row["timestamp"],
            actor_id=row["actor_id"],
            hash_anterior=hash_esperado,
        )

        if hash_calculado != row["hash_actual"]:
            return {
                "cadena_integra": False,
                "eventos_verificados": i,
                "primer_error": f"Hash inválido en evento {row['evento_id']} "
                                f"(posición {i+1}). Posible manipulación de datos.",
            }
        hash_esperado = row["hash_actual"]

    return {
        "cadena_integra": True,
        "eventos_verificados": len(rows),
        "primer_error": None,
    }


# ──────────────────────────────────────────────
# ACCIONES PREDEFINIDAS (constantes)
# ──────────────────────────────────────────────

class Acciones:
    """Catálogo de acciones estándar para la bitácora."""
    # Punto 2: Aprovechamiento
    REGISTRAR_TALA        = "REGISTRAR_TALA"
    REGISTRAR_TROZADO     = "REGISTRAR_TROZADO"
    REGISTRAR_DESPACHO    = "REGISTRAR_DESPACHO"

    # Punto 3: Transporte
    EMITIR_GTF            = "EMITIR_GTF"
    REGISTRAR_LOTE        = "REGISTRAR_LOTE"
    CONTROL_RUTA          = "CONTROL_RUTA"

    # Punto 4: Transformación
    INGRESO_CTP           = "INGRESO_CTP"
    SALIDA_CTP            = "SALIDA_CTP"
    EMITIR_GTF_SALIDA     = "EMITIR_GTF_SALIDA"

    # Pasaportes
    GENERAR_PASAPORTE     = "GENERAR_PASAPORTE"
    CONSULTAR_PASAPORTE   = "CONSULTAR_PASAPORTE"
    BLOQUEAR_LOTE         = "BLOQUEAR_LOTE"
