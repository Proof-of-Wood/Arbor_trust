import sys
from pathlib import Path
import pandas as pd
import uuid
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import get_connection

def _safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def _guardar_validacion(lote_id: str, regla: str, resultado: str, severidad: str, color: str, mensaje: str, detalle: dict = None):
    """Guarda el resultado de una regla específica en la tabla de validaciones."""
    import json
    val_id = f"VAL-{uuid.uuid4().hex[:8].upper()}"
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO validaciones
            (validacion_id, lote_id, regla, resultado, severidad, color_semaforo, mensaje, detalle_json)
            VALUES (?,?,?,?,?,?,?,?)
        """, (val_id, lote_id, regla, resultado, severidad, color, mensaje,
              json.dumps(detalle) if detalle else None))
        conn.commit()
    finally:
        conn.close()

def _actualizar_estado_lote(lote_id: str, color_final: str, mensaje_final: str):
    """Actualiza el estado general del lote."""
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE lotes
            SET color_semaforo = ?, mensaje_validacion = ?, estado_validacion = 'Validado'
            WHERE lote_id = ?
        """, (color_final, mensaje_final, lote_id))
        conn.commit()
    finally:
        conn.close()

def validar_rendimiento_ctp(volumen_ingreso: float, volumen_salida: float) -> dict:
    """
    Evalúa el rendimiento físico de transformación en CTP (aserradero).
    Fórmula: (volumen_salida / volumen_ingreso) * 100
    - > 60%: Rojo (Máximo biológico superado)
    - > 55%: Amarillo (Auditoría ocular)
    - <= 55%: Verde (Normal)
    """
    if volumen_ingreso <= 0:
        rendimiento = 0.0
    else:
        rendimiento = (volumen_salida / volumen_ingreso) * 100.0

    if rendimiento > 60.0:
        return {
            "resultado": "Rechazado",
            "severidad": "Alta",
            "color_semaforo": "Rojo",
            "mensaje": f"Alerta de Blanqueo: Rendimiento de aserrío físicamente imposible ({rendimiento:.2f}%). Supera el máximo biológico (60%)"
        }
    elif rendimiento > 55.0:
        return {
            "resultado": "Advertencia",
            "severidad": "Media",
            "color_semaforo": "Amarillo",
            "mensaje": f"Rendimiento inusualmente alto ({rendimiento:.2f}%). Requiere auditoría ocular en CTP"
        }
    else:
        return {
            "resultado": "Aprobado",
            "severidad": "Baja",
            "color_semaforo": "Verde",
            "mensaje": f"Rendimiento de aserrío regular ({rendimiento:.2f}%)"
        }

def validar_lote(lote_id: str) -> dict:
    """
    Motor principal. Ejecuta las reglas de negocio sobre un lote.
    
    Reglas:
    - Verde: Árbol registrado en censo + volumen extraído <= saldo disponible + GTF válida.
    - Amarillo: Diferencias menores en volumen (<5%) o marcas de tiempo inconsistentes.
    - Rojo: Árbol inexistente, volumen sobreexplotado (>5% del saldo), o falta de GTF asociada.
    """
    conn = get_connection()
    try:
        # Cargar datos del lote
        lote_row = conn.execute("SELECT * FROM lotes WHERE lote_id = ?", (lote_id,)).fetchone()
        if not lote_row:
            return {"error": "Lote no encontrado"}
        
        # Obtener todas las operaciones de este lote (Aprovechamiento)
        # Para simplificar, asumimos que podemos rastrear el árbol a través del lote.
        # En un modelo real complejo, un lote puede tener varias trozas de distintos árboles.
        # Aquí simplificaremos: buscaremos las operaciones que alimentaron este lote.
        # (Idealmente, la tabla operaciones tendría un lote_id cuando se despacha).
        ops = pd.read_sql_query("SELECT * FROM operaciones WHERE lote_id = ?", conn, params=(lote_id,))
        
        # Si no hay operaciones vinculadas, busquemos por GTF
        if ops.empty and lote_row["numero_gtf"]:
            ops = pd.read_sql_query("SELECT * FROM operaciones WHERE numero_gtf = ?", conn, params=(lote_row["numero_gtf"],))
        
        # Cargar balance de la parcela/especie
        balance_row = conn.execute("""
            SELECT * FROM balances_extraccion
            WHERE titulo_habilitante_id = ? AND parcela_corta = ? AND especie = ?
        """, (lote_row["titulo_habilitante_id"], lote_row["parcela_corta"], lote_row["especie"])).fetchone()
        
        # Cargar operaciones de transformación asociadas a este lote
        ops_trans = pd.read_sql_query("SELECT * FROM operaciones WHERE lote_id = ? AND tipo_operacion = 'Transformacion'", conn, params=(lote_id,))
        
    finally:
        conn.close()

    color_final = "Verde"
    mensajes = []
    
    # ── Regla 1: Existencia de GTF ──
    if not lote_row["numero_gtf"] or str(lote_row["numero_gtf"]).strip() == "":
        _guardar_validacion(lote_id, "gtf_asociada", "Rechazado", "Alta", "Rojo", "El lote no tiene una GTF asociada.")
        color_final = "Rojo"
        mensajes.append("Falta GTF.")
    else:
        _guardar_validacion(lote_id, "gtf_asociada", "Aprobado", "Baja", "Verde", f"GTF {lote_row['numero_gtf']} válida.")

    # ── Regla 2: Existencia del Árbol (Trazabilidad hacia atrás) ──
    if ops.empty:
        # No encontramos operaciones base (tala) asociadas a este GTF/Lote
        _guardar_validacion(lote_id, "existencia_arbol", "Rechazado", "Alta", "Rojo", "No se encontraron operaciones de tala/trozado que originen este lote.")
        color_final = "Rojo"
        mensajes.append("Árbol origen no encontrado.")
    else:
        arboles_origen = [str(x) for x in ops["id_arbol"].dropna().unique() if str(x) != ""]
        if len(arboles_origen) == 0:
            _guardar_validacion(lote_id, "existencia_arbol", "Rechazado", "Alta", "Rojo", "Las operaciones no tienen un ID de árbol asociado.")
            color_final = "Rojo"
            mensajes.append("Operaciones sin ID de árbol.")
        else:
            placeholders = ",".join("?" for _ in arboles_origen)
            conn_v = get_connection()
            try:
                censo_rows = conn_v.execute(f"""
                    SELECT c.id_arbol, c.estado, p.estado as plan_estado
                    FROM censo_forestal c
                    JOIN planes_aprovechamiento p ON c.id_plan = p.id_plan
                    WHERE c.id_arbol IN ({placeholders})
                """, arboles_origen).fetchall()
            finally:
                conn_v.close()
            
            censo_dict = {row["id_arbol"]: (row["estado"], row["plan_estado"]) for row in censo_rows}
            inexistentes = [a for a in arboles_origen if a not in censo_dict]
            fraudulentos = [a for a, (est, plan_est) in censo_dict.items() if est == "FRAUDE_DETECTADO"]
            vencidos = [a for a, (est, plan_est) in censo_dict.items() if plan_est in ("Vencido", "Actualizado")]
            
            if inexistentes:
                _guardar_validacion(lote_id, "existencia_arbol", "Rechazado", "Alta", "Rojo", f"Árboles origen no registrados en el censo: {inexistentes}")
                color_final = "Rojo"
                mensajes.append("Árbol origen no censado.")
            elif fraudulentos:
                _guardar_validacion(lote_id, "existencia_arbol", "Rechazado", "Alta", "Rojo", f"Bloqueo: Árbol origen suspendido por fraude: {fraudulentos}")
                color_final = "Rojo"
                mensajes.append("Árbol origen con fraude.")
            elif vencidos:
                _guardar_validacion(lote_id, "existencia_arbol", "Rechazado", "Alta", "Rojo", f"Bloqueo: Árbol origen pertenece a un Plan de Aprovechamiento vencido: {vencidos}")
                color_final = "Rojo"
                mensajes.append("Plan de Aprovechamiento vencido.")
            else:
                _guardar_validacion(lote_id, "existencia_arbol", "Aprobado", "Baja", "Verde", f"Árboles origen verificados: {arboles_origen}")

    # ── Regla 3: Volumen vs Saldo Disponible ──
    volumen_lote = _safe_float(lote_row["volumen_total"])
    if not balance_row:
        _guardar_validacion(lote_id, "volumen_disponible", "Rechazado", "Alta", "Rojo", "No existe balance de extracción para esta parcela y especie.")
        color_final = "Rojo"
        mensajes.append("Sin balance de extracción.")
    else:
        saldo = _safe_float(balance_row["saldo_disponible"])
        
        if saldo < 0:
            _guardar_validacion(lote_id, "volumen_disponible", "Rechazado", "Alta", "Rojo", "El saldo disponible en la parcela es negativo previo a esta operación.")
            color_final = "Rojo"
            mensajes.append("Saldo negativo en parcela.")
        elif volumen_lote <= saldo:
            _guardar_validacion(lote_id, "volumen_disponible", "Aprobado", "Baja", "Verde", "El volumen extraído es menor o igual al saldo disponible.")
        else:
            # Volumen excede. ¿Es < 5% de tolerancia o es falla crítica?
            exceso = volumen_lote - saldo
            margen_5_porciento = saldo * 0.05
            
            if exceso <= margen_5_porciento:
                _guardar_validacion(lote_id, "volumen_disponible", "Advertencia", "Media", "Amarillo", f"El volumen excede el saldo por una diferencia menor al 5% ({exceso:.2f} m3).")
                if color_final != "Rojo": color_final = "Amarillo"
                mensajes.append("Exceso de volumen menor al 5%.")
            else:
                _guardar_validacion(lote_id, "volumen_disponible", "Rechazado", "Alta", "Rojo", f"Volumen sobreexplotado. Excede el saldo por {exceso:.2f} m3 (>5%).")
                color_final = "Rojo"
                mensajes.append("Sobreexplotación crítica de volumen.")

    # ── Regla 4: Inconsistencias de Timestamps (Amarillo) ──
    # Validamos que Transporte/Despacho no sea antes que la Tala (si tenemos ambas fechas)
    if not ops.empty:
        df_tala = ops[ops["tipo_operacion"] == "Tala"]
        df_desp = ops[ops["tipo_operacion"] == "Despacho"]
        if not df_tala.empty and not df_desp.empty:
            fecha_tala = df_tala["fecha"].min()
            fecha_desp = df_desp["fecha"].max()
            
            # Simple string comparison assumes YYYY-MM-DD
            if fecha_desp < fecha_tala:
                _guardar_validacion(lote_id, "cronologia_operaciones", "Advertencia", "Media", "Amarillo", "Inconsistencia de fechas: Despacho registrado antes que la Tala.")
                if color_final != "Rojo": color_final = "Amarillo"
                mensajes.append("Inconsistencia cronológica.")

    # ── Regla 5: Rendimiento en Planta (CTP) ──
    if not ops_trans.empty:
        volumen_ingreso = _safe_float(lote_row["volumen_total"])
        volumen_salida = _safe_float(ops_trans["volumen"].sum())
        res_ctp = validar_rendimiento_ctp(volumen_ingreso, volumen_salida)
        _guardar_validacion(lote_id, "rendimiento_ctp", res_ctp["resultado"], res_ctp["severidad"], res_ctp["color_semaforo"], res_ctp["mensaje"])
        if res_ctp["color_semaforo"] == "Rojo":
            color_final = "Rojo"
            mensajes.append(res_ctp["mensaje"])
        elif res_ctp["color_semaforo"] == "Amarillo":
            if color_final != "Rojo":
                color_final = "Amarillo"
            mensajes.append(res_ctp["mensaje"])

    mensaje_final_str = " | ".join(mensajes) if mensajes else "Lote válido con trazabilidad consistente."
    
    _actualizar_estado_lote(lote_id, color_final, mensaje_final_str)
    
    return {
        "lote_id": lote_id,
        "color_semaforo": color_final,
        "mensaje": mensaje_final_str
    }
