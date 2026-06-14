import sys
import os
from pathlib import Path

# Agregar directorio backend al path de Python
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from database import DB_PATH, init_db, seed_from_excel, get_connection, resolver_ruc

def reset_demo():
    print("=" * 60)
    print("ARBORTRUST - RESTABLECIMIENTO DE ENTORNO DE DEMOSTRACIÓN")
    print("=" * 60)
    
    # 1. Borrar base de datos antigua
    if DB_PATH.exists():
        try:
            os.remove(DB_PATH)
            print(f"[RESET] Base de datos borrada con éxito en: {DB_PATH}")
        except Exception as e:
            print(f"[RESET] Error al borrar base de datos: {e}")
    else:
        print("[RESET] No se encontró base de datos previa. Se creará una limpia.")

    # 2. Inicializar tablas
    try:
        init_db()
        print("[RESET] Tablas del esquema relacional creadas con éxito.")
    except Exception as e:
        print(f"[RESET] Error al inicializar tablas: {e}")
        return

    # 3. Sembrar datos base desde los Excel en data/sample/
    try:
        seed_from_excel()
        print("[RESET] Base de datos sembrada con los archivos base de muestra.")
    except Exception as e:
        print(f"[RESET] Error al sembrar datos base: {e}")
        return

    # 4. Inserción de Entidades GovTech / PIDE para la Demo
    conn = get_connection()
    try:
        print("[RESET] Configurando identidades PIDE / GovTech...")
        cursor = conn.cursor()
        
        # Titular Concesionario (PRODUCTOR DEMO)
        ruc_titular = "20123456789"
        cursor.execute("""
            INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion)
            VALUES (?, 'PRODUCTOR DEMO', 'Av. La Marina 450, Iquitos, Loreto')
        """, (ruc_titular,))
        
        # Título Habilitante (TH-001) vinculado a PRODUCTOR DEMO
        cursor.execute("""
            INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica)
            VALUES ('TH-001', ?, 'Concesión Forestal Río Amazonas', 'Maynas, Loreto')
        """, (ruc_titular,))
        
        # Operador CTP (ASERRADERO PUCALLPA DEMO)
        ruc_ctp = "20999999999"
        cursor.execute("""
            INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion)
            VALUES (?, 'ASERRADERO PUCALLPA DEMO', 'Vía de Evitamiento Km 4.2, Pucallpa')
        """, (ruc_ctp,))
        
        # Pre-cargar el plan de aprovechamiento para permitir registro de operaciones directo
        plan_id = "PLAN-DEMO-V1"
        cursor.execute("""
            INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado, documento_pdf_hash)
            VALUES (?, 'TH-001', 1, '2026-06-14', 'Aprobado', 'PDF_HASH_DEMO_OK')
        """, (plan_id,))
        
        # Árboles en censo_forestal para PLAN-DEMO-V1
        arboles_demo = [
            ("ARB-DEMO-001", "Shihuahuaco", 8.5),
            ("ARB-DEMO-002", "Shihuahuaco", 9.0),
            ("ARB-DEMO-003", "Cumala", 6.2),
            ("ARB-DEMO-004", "Cedro", 12.4),
            ("ARB-DEMO-005", "Tornillo", 15.0),
        ]
        
        for arbol_id, especie, vol in arboles_demo:
            cursor.execute("""
                INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                VALUES (?, ?, ?, ?, 'Autorizado', 'Aprovechable')
            """, (arbol_id, plan_id, especie, vol))
            
        # Balances de extracción correspondientes
        cursor.execute("""
            INSERT OR IGNORE INTO balances_extraccion (balance_id, titulo_habilitante_id, parcela_corta, especie, volumen_autorizado, volumen_movilizado, saldo_disponible, estado_saldo)
            VALUES ('BAL-DEMO-001', 'TH-001', 'PC1', 'Shihuahuaco', 17.5, 0.0, 17.5, 'Positivo')
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO balances_extraccion (balance_id, titulo_habilitante_id, parcela_corta, especie, volumen_autorizado, volumen_movilizado, saldo_disponible, estado_saldo)
            VALUES ('BAL-DEMO-002', 'TH-001', 'PC1', 'Cumala', 6.2, 0.0, 6.2, 'Positivo')
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO balances_extraccion (balance_id, titulo_habilitante_id, parcela_corta, especie, volumen_autorizado, volumen_movilizado, saldo_disponible, estado_saldo)
            VALUES ('BAL-DEMO-003', 'TH-001', 'PC1', 'Cedro', 12.4, 0.0, 12.4, 'Positivo')
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO balances_extraccion (balance_id, titulo_habilitante_id, parcela_corta, especie, volumen_autorizado, volumen_movilizado, saldo_disponible, estado_saldo)
            VALUES ('BAL-DEMO-004', 'TH-001', 'PC1', 'Tornillo', 15.0, 0.0, 15.0, 'Positivo')
        """)

        # Lote / GTF listo para consulta ex-ante/ex-post
        cursor.execute("""
            INSERT OR IGNORE INTO lotes (lote_id, numero_gtf, titulo_habilitante_id, titular, parcela_corta, especie, volumen_total, estado_validacion, color_semaforo, mensaje_validacion)
            VALUES ('LOT-DEMO-001', 'GTF-DEMO-001', 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 8.5, 'Conforme', 'Verde', 'Lote conforme verificado en origen.')
        """)

        conn.commit()
        print("[RESET] Datos e identidades para la demo insertados exitosamente.")
    except Exception as e:
        conn.rollback()
        print(f"[RESET] Error al insertar datos de demo: {e}")
    finally:
        conn.close()
        
    print("=" * 60)
    print("RESUMEN DE ESTADO DE LA DEMO:")
    print("Sistema listo y aprovisionado.")
    print("- Titular Concesionario precargado: PRODUCTOR DEMO (RUC: 20123456789)")
    print("- Operador CTP precargado: ASERRADERO PUCALLPA DEMO (RUC: 20999999999)")
    print("- Regente Forestal asignado: REG-SER-2026-0001")
    print("- Título Habilitante activo: TH-001 (Concesión Forestal Río Amazonas)")
    print("- Árboles en Censo (Standing): ARB-DEMO-001 al ARB-DEMO-005 (Listos para Tala)")
    print("- Balances de Extracción activos: BAL-DEMO-001 al BAL-DEMO-004")
    print("- GTF pre-existente para consulta: GTF-DEMO-001 (Lote: LOT-DEMO-001)")
    print("=" * 60)

if __name__ == "__main__":
    reset_demo()
