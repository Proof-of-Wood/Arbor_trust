import asyncio
import httpx
import subprocess
import time
import os
import sys
import uuid
import shutil
import sqlite3
import pandas as pd
from pathlib import Path

# Configurar rutas
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Importar funciones de base de datos para resetearla
from database import get_connection, init_db, seed_from_excel, resolver_ruc

PORT = 8099
BASE_URL = f"http://127.0.0.1:{PORT}"

def reset_database():
    """Resetea la base de datos eliminando el archivo .db y volviendo a inicializarla."""
    db_file = BACKEND_DIR / "arbortrust.db"
    if db_file.exists():
        try:
            os.remove(db_file)
            print("[TEST] Base de datos eliminada.")
        except Exception as e:
            print(f"[TEST] No se pudo eliminar la base de datos: {e}")
            
    # Inicializar y sembrar
    init_db()
    seed_from_excel()
    print("[TEST] Base de datos inicializada y sembrada desde Excel.")

def preinsert_test_trees():
    """Pre-inserta los árboles necesarios en la tabla censo_forestal/titulares/titulos/planes para que las pruebas pasen."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        print("[TEST] Pre-insertando árboles de prueba...")
        
        # Preinsert titular, title, and plan
        titular = "PRODUCTOR DEMO"
        ruc = resolver_ruc(titular)
        conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, 'Direccion Demo')", (ruc, titular))
        conn.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES ('TH-001', ?, 'Concesion TH-001', 'Loreto, Peru')", (ruc,))
        conn.execute("INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado) VALUES ('PLAN-TH-001', 'TH-001', 1, '2026-06-14', 'Aprobado')")

        # 1. Árboles para Caso A
        for i in range(10):
            for j in range(5):
                cursor.execute("""
                    INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                    VALUES (?, 'PLAN-TH-001', 'Shihuahuaco', 10.0, 'Autorizado', 'Aprovechable')
                """, (f"ARB-A-{i}-{j}",))
                
        # 2. Árboles para Caso B
        cursor.execute("""
            INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
            VALUES ('ARB-B-1', 'PLAN-TH-001', 'Shihuahuaco', 10.0, 'Autorizado', 'Aprovechable')
        """)
        
        # 3. Árboles para Caso C
        for i in range(500):
            cursor.execute("""
                INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                VALUES (?, 'PLAN-TH-001', 'Shihuahuaco', 10.0, 'Autorizado', 'Aprovechable')
            """, (f"ARB-C-{i}",))
            
        # 4. Árboles para Caso D
        for i in range(5):
            cursor.execute("""
                INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                VALUES (?, 'PLAN-TH-001', 'Shihuahuaco', 10.0, 'Autorizado', 'Aprovechable')
            """, (f"ARB-D1-{i}",))
            cursor.execute("""
                INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                VALUES (?, 'PLAN-TH-001', 'Shihuahuaco', 10.0, 'Autorizado', 'Aprovechable')
            """, (f"ARB-D2-{i}",))
            
        conn.commit()
        print("[TEST] Pre-inserción de árboles de prueba exitosa.")
    finally:
        conn.close()

def generate_excel_file(path: str, rows: list):
    """Genera un archivo Excel con las filas especificadas."""
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False, engine='openpyxl')

async def main():
    print("=" * 60)
    print("INICIANDO PRUEBAS DE CONCURRENCIA E IDEMPOTENCIA EN EXCEL (XLSX)")
    print("=" * 60)
    
    # 1. Resetear base de datos y pre-insertar árboles
    reset_database()
    preinsert_test_trees()
    
    # 2. Levantar el servidor Uvicorn en un puerto separado
    print(f"[TEST] Iniciando servidor Uvicorn en el puerto {PORT}...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(BACKEND_DIR)
    )
    
    # Esperar a que el servidor esté listo
    time.sleep(3)
    
    # Verificar si el servidor está levantado
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{BASE_URL}/api/v1/reportes/fallas", headers={"X-PIDE-Rol": "OSINFOR"})
            if res.status_code == 200:
                print("[TEST] Servidor levantado correctamente.")
        except Exception as e:
            print(f"[TEST] ERROR: No se pudo conectar al servidor de pruebas: {e}")
            server_process.terminate()
            sys.exit(1)
            
    # Crear carpeta para archivos de prueba temporales
    test_files_dir = BACKEND_DIR / "test_temp_files"
    test_files_dir.mkdir(exist_ok=True)
    
    try:
        # ───────────────────────────────────────────────────────────
        # CASO A: PETICIONES SIMULTÁNEAS (10 Cargas Concurrentes)
        # ───────────────────────────────────────────────────────────
        print("\n" + "-" * 50)
        print("EJECUTANDO CASO A: 10 Cargas Simultáneas de Archivos Excel Diferentes")
        print("-" * 50)
        
        # Generar 10 archivos de operaciones diferentes
        filenames = []
        for i in range(10):
            rows = [
                {
                    "operacion_id": f"OP-A-{i}-{j}",
                    "tipo_operacion": "Tala",
                    "arbol_id": f"ARB-A-{i}-{j}",
                    "troza_id": "",
                    "parcela_corta": "PC1",
                    "especie": "Shihuahuaco",
                    "volumen": 0.5,
                    "numero_gtf": "",
                    "fecha": "2026-06-14"
                }
                for j in range(5) # 5 operaciones por archivo
            ]
            
            filepath = test_files_dir / f"test_a_{i}.xlsx"
            generate_excel_file(str(filepath), rows)
            filenames.append(filepath)
            
        # Lanzar las 10 peticiones de subida al mismo tiempo
        start_time = time.time()
        async def upload_file(client, filepath):
            with open(filepath, "rb") as f:
                # Enviar con el MIME type correcto para Excel
                files = {"file": (filepath.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                return await client.post(
                    f"{BASE_URL}/api/v1/trazabilidad/cargar-archivo?tipo_archivo=operaciones",
                    files=files,
                    headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"},
                    timeout=30.0
                )
                
        async with httpx.AsyncClient() as client:
            tasks = [upload_file(client, fn) for fn in filenames]
            responses = await asyncio.gather(*tasks)
            
        end_time = time.time()
        elapsed = (end_time - start_time) * 1000
        print(f"[TEST] Respuestas de subida recibidas en {elapsed:.2f} ms.")
        
        # Verificar respuestas
        job_ids = []
        for idx, res in enumerate(responses):
            assert res.status_code == 202, f"Subida {idx} falló con código {res.status_code}: {res.text}"
            res_json = res.json()
            assert "job_id" in res_json
            job_ids.append(res_json["job_id"])
            print(f"[TEST] Archivo {idx} en cola con job_id: {res_json['job_id']}")
            
        assert elapsed < 2000, f"Error: Las respuestas demoraron {elapsed:.2f} ms (esperado < 2000 ms en carga asíncrona total)"
        print("[TEST] CASO A SUBIDAS EXITOSAS (<200ms por petición en promedio).")
        
        # Esperar a que todos los jobs terminen
        print("[TEST] Esperando que terminen los 10 procesos de carga...")
        for jid in job_ids:
            while True:
                async with httpx.AsyncClient() as client:
                    status_res = await client.get(f"{BASE_URL}/api/v1/trazabilidad/estado/{jid}", headers={"X-PIDE-Rol": "Titular"})
                    status = status_res.json()["estado"]
                    if status in ("COMPLETADO", "FALLIDO"):
                        print(f"[TEST] Job {jid} finalizado con estado: {status}")
                        if status == "FALLIDO":
                            print(f"[TEST] ERROR en Job {jid}: {status_res.json()['resultado']}")
                        assert status == "COMPLETADO"
                        break
                await asyncio.sleep(0.5)
                
        print("[TEST] CASO A COMPLETADO CON ÉXITO: Sin errores de 'database is locked' y procesado al 100%.")

        # ───────────────────────────────────────────────────────────
        # CASO B: INTENTO DE DUPLICIDAD (Idempotencia)
        # ───────────────────────────────────────────────────────────
        print("\n" + "-" * 50)
        print("EJECUTANDO CASO B: Intento de Duplicidad de Archivo Excel Idéntico")
        print("-" * 50)
        
        # Generar un archivo único
        filepath_b = test_files_dir / "test_b.xlsx"
        rows_b = [
            {
                "operacion_id": "OP-B-1",
                "tipo_operacion": "Tala",
                "arbol_id": "ARB-B-1",
                "troza_id": "",
                "parcela_corta": "PC1",
                "especie": "Shihuahuaco",
                "volumen": 1.0,
                "numero_gtf": "",
                "fecha": "2026-06-14"
            }
        ]
        generate_excel_file(str(filepath_b), rows_b)
        
        # Subir concurrentemente el mismo archivo dos veces
        async with httpx.AsyncClient() as client:
            res1_task = upload_file(client, filepath_b)
            res2_task = upload_file(client, filepath_b)
            res1, res2 = await asyncio.gather(res1_task, res2_task)
            
        assert res1.status_code in (202, 200)
        assert res2.status_code in (202, 200)
        
        json1 = res1.json()
        json2 = res2.json()
        
        print(f"[TEST] Petición 1: job_id={json1['job_id']}, estado={json1['estado']}")
        print(f"[TEST] Petición 2: job_id={json2['job_id']}, estado={json2['estado']}")
        
        assert json1["job_id"] == json2["job_id"], "Error: Deben tener el mismo job_id por idempotencia de hash SHA256"
        assert "Idempotencia" in json2["mensaje"] or "Idempotencia" in json1["mensaje"], "Error: Se debió interceptar por idempotencia"
        print("[TEST] CASO B COMPLETADO CON ÉXITO: Archivos duplicados detectados y resueltos de manera idempotente.")

        # ───────────────────────────────────────────────────────────
        # CASO C: FALLO EN LA MITAD DEL ARCHIVO (Rollback Atómico)
        # ───────────────────────────────────────────────────────────
        print("\n" + "-" * 50)
        print("EJECUTANDO CASO C: Fallo en Fila 500 y Rollback Completo")
        print("-" * 50)
        
        # Crear 500 filas de operaciones. La fila 500 (index 499) es corrupta (volumen negativo)
        rows_c = []
        for i in range(500):
            # Usar operacion_id único
            op_id = f"OP-C-{i}"
            vol = 0.1
            especie = "Shihuahuaco"
            if i == 499:
                vol = -5.0 # Corrupto! Volumen negativo
            
            rows_c.append({
                "operacion_id": op_id,
                "tipo_operacion": "Tala",
                "arbol_id": f"ARB-C-{i}",
                "troza_id": "",
                "parcela_corta": "PC1",
                "especie": especie,
                "volumen": vol,
                "numero_gtf": "",
                "fecha": "2026-06-14"
            })
            
        filepath_c = test_files_dir / "test_c.xlsx"
        generate_excel_file(str(filepath_c), rows_c)
        
        # Cargar archivo
        async with httpx.AsyncClient() as client:
            res_c = await upload_file(client, filepath_c)
            
        assert res_c.status_code == 202
        jid_c = res_c.json()["job_id"]
        print(f"[TEST] Archivo corrupto subido. Job ID: {jid_c}")
        
        # Esperar a que el job falle
        while True:
            async with httpx.AsyncClient() as client:
                status_res = await client.get(f"{BASE_URL}/api/v1/trazabilidad/estado/{jid_c}", headers={"X-PIDE-Rol": "Titular"})
                status = status_res.json()["estado"]
                if status in ("COMPLETADO", "FALLIDO"):
                    print(f"[TEST] Job corrupto finalizó con estado: {status}")
                    assert status == "FALLIDO"
                    print(f"[TEST] Detalle del fallo: {status_res.json()['resultado']['error']}")
                    break
            await asyncio.sleep(0.5)
            
        # Verificar que NINGUNA de las 499 filas previas fue guardada en base de datos
        conn = get_connection()
        try:
            db_rows = conn.execute("SELECT count(*) as cnt FROM operaciones WHERE operacion_id LIKE 'OP-C-%'").fetchone()
            cnt = db_rows["cnt"]
            print(f"[TEST] Registros guardados en base de datos que inician con 'OP-C-': {cnt}")
            assert cnt == 0, "Error: Se insertaron registros a medias. El rollback falló!"
            print("[TEST] CASO C COMPLETADO CON ÉXITO: Rollback realizado correctamente. Carga atómica confirmada.")
        finally:
            conn.close()

        # ───────────────────────────────────────────────────────────
        # CASO D: ACTUALIZACIÓN CONCURRENTE DE BALANCES
        # ───────────────────────────────────────────────────────────
        print("\n" + "-" * 50)
        print("EJECUTANDO CASO D: Actualización Concurrente de Balances")
        print("-" * 50)
        
        # Obtener balance inicial para Shihuahuaco en PC1
        conn = get_connection()
        try:
            bal_ini = conn.execute("""
                SELECT * FROM balances_extraccion 
                WHERE titulo_habilitante_id = 'TH-001' AND parcela_corta = 'PC1' AND especie = 'Shihuahuaco'
            """).fetchone()
            vol_mov_ini = bal_ini["volumen_movilizado"]
            saldo_ini = bal_ini["saldo_disponible"]
            print(f"[TEST] Balances iniciales: movilizado={vol_mov_ini}, disponible={saldo_ini}")
        finally:
            conn.close()
            
        # Generar dos archivos de operaciones que descuentan del mismo balance al mismo tiempo
        # Archivo 1
        rows_d1 = [
            {
                "operacion_id": f"OP-D1-{i}",
                "tipo_operacion": "Tala",
                "arbol_id": f"ARB-D1-{i}",
                "troza_id": "",
                "parcela_corta": "PC1",
                "especie": "Shihuahuaco",
                "volumen": 1.0,
                "numero_gtf": "",
                "fecha": "2026-06-14"
            }
            for i in range(5) # Total volumen = 5.0
        ]
        # Archivo 2
        rows_d2 = [
            {
                "operacion_id": f"OP-D2-{i}",
                "tipo_operacion": "Tala",
                "arbol_id": f"ARB-D2-{i}",
                "troza_id": "",
                "parcela_corta": "PC1",
                "especie": "Shihuahuaco",
                "volumen": 1.0,
                "numero_gtf": "",
                "fecha": "2026-06-14"
            }
            for i in range(5) # Total volumen = 5.0
        ]
        
        filepath_d1 = test_files_dir / "test_d1.xlsx"
        filepath_d2 = test_files_dir / "test_d2.xlsx"
        generate_excel_file(str(filepath_d1), rows_d1)
        generate_excel_file(str(filepath_d2), rows_d2)
        
        # Subir los dos archivos concurrentemente
        async with httpx.AsyncClient() as client:
            res_d1_task = upload_file(client, filepath_d1)
            res_d2_task = upload_file(client, filepath_d2)
            res_d1, res_d2 = await asyncio.gather(res_d1_task, res_d2_task)
            
        assert res_d1.status_code == 202
        assert res_d2.status_code == 202
        jid_d1 = res_d1.json()["job_id"]
        jid_d2 = res_d2.json()["job_id"]
        
        # Esperar a que terminen ambos jobs
        print("[TEST] Esperando que terminen los procesos de carga de Caso D...")
        for jid in (jid_d1, jid_d2):
            while True:
                async with httpx.AsyncClient() as client:
                    status_res = await client.get(f"{BASE_URL}/api/v1/trazabilidad/estado/{jid}", headers={"X-PIDE-Rol": "Titular"})
                    status = status_res.json()["estado"]
                    if status in ("COMPLETADO", "FALLIDO"):
                        assert status == "COMPLETADO"
                        break
                await asyncio.sleep(0.5)
                
        # Verificar balances finales
        conn = get_connection()
        try:
            bal_fin = conn.execute("""
                SELECT * FROM balances_extraccion 
                WHERE titulo_habilitante_id = 'TH-001' AND parcela_corta = 'PC1' AND especie = 'Shihuahuaco'
            """).fetchone()
            vol_mov_fin = bal_fin["volumen_movilizado"]
            saldo_fin = bal_fin["saldo_disponible"]
            print(f"[TEST] Balances finales: movilizado={vol_mov_fin}, disponible={saldo_fin}")
            
            # Verificar consistencia matemática exacta (5.0 + 5.0 = 10.0 m3 descontados)
            assert vol_mov_fin == vol_mov_ini + 10.0, f"Error: volumen movilizado esperado {vol_mov_ini + 10.0}, obtenido {vol_mov_fin}"
            assert saldo_fin == saldo_ini - 10.0, f"Error: saldo disponible esperado {saldo_ini - 10.0}, obtenido {saldo_fin}"
            print("[TEST] CASO D COMPLETADO CON ÉXITO: Balances descontados matemáticamente con precisión exacta y sin pérdida de volumen.")
        finally:
            conn.close()

        # ───────────────────────────────────────────────────────────
        # NUEVO CASO DE PRUEBA: TEST ADENDA (UPSERT)
        # ───────────────────────────────────────────────────────────
        print("\n" + "-" * 50)
        print("EJECUTANDO PRUEBA ADENDA: Actualización de Balances (UPSERT)")
        print("-" * 50)
        
        # Generar un archivo de balance con un volumen autorizado modificado para BAL-001
        filepath_adenda = test_files_dir / "test_adenda.xlsx"
        rows_adenda = [
            {
                "balance_id": "BAL-001",
                "titulo_habilitante_id": "TH-001",
                "parcela_corta": "PC1",
                "especie": "Shihuahuaco",
                "volumen_autorizado": 150.0,
                "volumen_movilizado": 86.0,
                "saldo_disponible": 64.0,
                "estado_saldo": "Positivo"
            }
        ]
        generate_excel_file(str(filepath_adenda), rows_adenda)
        
        # Subir el archivo de balance modificado
        async with httpx.AsyncClient() as client:
            with open(filepath_adenda, "rb") as f:
                files = {"file": (filepath_adenda.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                res_adenda = await client.post(
                    f"{BASE_URL}/api/v1/trazabilidad/cargar-archivo?tipo_archivo=balances",
                    files=files,
                    headers={"X-PIDE-Rol": "OSINFOR"},
                    timeout=30.0
                )
        assert res_adenda.status_code == 202
        jid_adenda = res_adenda.json()["job_id"]
        
        # Esperar a que termine
        while True:
            async with httpx.AsyncClient() as client:
                status_res = await client.get(f"{BASE_URL}/api/v1/trazabilidad/estado/{jid_adenda}", headers={"X-PIDE-Rol": "OSINFOR"})
                status = status_res.json()["estado"]
                if status in ("COMPLETADO", "FALLIDO"):
                    assert status == "COMPLETADO"
                    break
            await asyncio.sleep(0.5)
            
        # Verificar en base de datos que el volumen fue actualizado y el saldo recalculado
        conn = get_connection()
        try:
            bal_updated = conn.execute("SELECT * FROM balances_extraccion WHERE balance_id = 'BAL-001'").fetchone()
            print(f"[TEST] Balance BAL-001 después de adenda: autorizado={bal_updated['volumen_autorizado']}, disponible={bal_updated['saldo_disponible']}")
            assert bal_updated["volumen_autorizado"] == 150.0, f"Esperado 150.0, obtenido {bal_updated['volumen_autorizado']}"
            # Saldo disponible debe ser 150.0 - volumen_movilizado
            assert bal_updated["saldo_disponible"] == 150.0 - bal_updated["volumen_movilizado"]
            print("[TEST] PRUEBA ADENDA COMPLETADA CON ÉXITO: Cláusula UPSERT actualizó el volumen de forma correcta.")
        finally:
            conn.close()

        # ───────────────────────────────────────────────────────────
        # NUEVO CASO DE PRUEBA: TEST RENDIMIENTO IMPOSIBLE (CTP)
        # ───────────────────────────────────────────────────────────
        print("\n" + "-" * 50)
        print("EJECUTANDO PRUEBA RENDIMIENTO IMPOSIBLE: Regla de 60% Máximo CTP")
        print("-" * 50)
        
        # Insertar un lote de prueba LOT-R y pre-insertar árbol y tala para pasar validaciones previas
        conn = get_connection()
        try:
            titular = "PRODUCTOR DEMO"
            ruc = resolver_ruc(titular)
            conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, 'Direccion Demo')", (ruc, titular))
            conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, 'Direccion Demo')", (resolver_ruc('ACTOR-TEST'), 'ACTOR-TEST'))
            conn.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES ('TH-001', ?, 'Concesion TH-001', 'Loreto, Peru')", (ruc,))
            conn.execute("INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado) VALUES ('PLAN-TH-001', 'TH-001', 1, '2026-06-14', 'Aprobado')")

            conn.execute("""
                INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                VALUES ('ARB-R-1', 'PLAN-TH-001', 'Shihuahuaco', 100.0, 'Autorizado', 'Aprovechable')
            """)
            conn.execute("""
                INSERT OR IGNORE INTO lotes (lote_id, numero_gtf, titulo_habilitante_id, titular, parcela_corta, especie, volumen_total)
                VALUES ('LOT-R', 'GTF-R-1', 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 10.0)
            """)
            conn.execute("""
                INSERT OR IGNORE INTO operaciones (operacion_id, tipo_operacion, punto_cadena, id_arbol, lote_id, parcela_corta, especie, volumen, numero_gtf, actor_id, id_titular, fecha)
                VALUES ('OP-R-TALA', 'Tala', 2, 'ARB-R-1', 'LOT-R', 'PC1', 'Shihuahuaco', 10.0, 'GTF-R-1', 'ACTOR-TEST', ?, '2026-06-14')
            """, (resolver_ruc('ACTOR-TEST'),))
            conn.commit()
        finally:
            conn.close()
            
        # Generar un archivo de operación de transformación con rendimiento imposible: salida = 8.5 m³ (rendimiento = 85%)
        filepath_trans = test_files_dir / "test_trans.xlsx"
        rows_trans = [
            {
                "operacion_id": "OP-R-TRANS",
                "tipo_operacion": "Transformacion",
                "lote_id": "LOT-R",
                "parcela_corta": "PC1",
                "especie": "Shihuahuaco",
                "volumen": 8.5,
                "actor_id": "ACTOR-CTP",
                "fecha": "2026-06-15"
            }
        ]
        generate_excel_file(str(filepath_trans), rows_trans)
        
        # Subir la operación de transformación
        async with httpx.AsyncClient() as client:
            with open(filepath_trans, "rb") as f:
                files = {"file": (filepath_trans.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                res_trans = await client.post(
                    f"{BASE_URL}/api/v1/trazabilidad/cargar-archivo?tipo_archivo=operaciones",
                    files=files,
                    headers={"X-PIDE-Rol": "Operador_CTP", "X-PIDE-RUC": "20123456789"},
                    timeout=30.0
                )
        assert res_trans.status_code == 202
        jid_trans = res_trans.json()["job_id"]
        
        # Esperar a que termine
        while True:
            async with httpx.AsyncClient() as client:
                status_res = await client.get(f"{BASE_URL}/api/v1/trazabilidad/estado/{jid_trans}", headers={"X-PIDE-Rol": "Operador_CTP"})
                status = status_res.json()["estado"]
                if status in ("COMPLETADO", "FALLIDO"):
                    assert status == "COMPLETADO"
                    break
            await asyncio.sleep(0.5)
            
        # Verificar que el lote LOT-R pasó a Semáforo Rojo debido al rendimiento imposible
        conn = get_connection()
        try:
            lote_r = conn.execute("SELECT * FROM lotes WHERE lote_id = 'LOT-R'").fetchone()
            print(f"[TEST] Lote LOT-R semáforo: {lote_r['color_semaforo']}, mensaje: {lote_r['mensaje_validacion']}")
            assert lote_r["color_semaforo"] == "Rojo"
            assert "Rendimiento de aserrío físicamente imposible" in lote_r["mensaje_validacion"]
            
            # Verificar validaciones
            val_r = conn.execute("SELECT * FROM validaciones WHERE lote_id = 'LOT-R' AND regla = 'rendimiento_ctp'").fetchone()
            assert val_r is not None
            assert val_r["color_semaforo"] == "Rojo"
            print("[TEST] PRUEBA RENDIMIENTO IMPOSIBLE COMPLETADA CON ÉXITO: Bloqueo de aserrío ilegal confirmado.")
        finally:
            conn.close()

        # ───────────────────────────────────────────────────────────
        # NUEVO CASO DE PRUEBA: TEST CASCADA RETROACTIVA
        # ───────────────────────────────────────────────────────────
        print("\n" + "-" * 50)
        print("EJECUTANDO PRUEBA CASCADA RETROACTIVA: Efecto Dominó OSINFOR")
        print("-" * 50)
        
        # Insertar árbol, lote y operación de tala inicial
        conn = get_connection()
        try:
            titular = "PRODUCTOR DEMO"
            ruc = resolver_ruc(titular)
            conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, 'Direccion Demo')", (ruc, titular))
            conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES (?, ?, 'Direccion Demo')", (resolver_ruc('ACTOR-TEST'), 'ACTOR-TEST'))
            conn.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES ('TH-001', ?, 'Concesion TH-001', 'Loreto, Peru')", (ruc,))
            conn.execute("INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado) VALUES ('PLAN-TH-001', 'TH-001', 1, '2026-06-14', 'Aprobado')")

            conn.execute("""
                INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
                VALUES ('ARB-CASCADA-1', 'PLAN-TH-001', 'Shihuahuaco', 100.0, 'Autorizado', 'Aprovechable')
            """)
            conn.execute("""
                INSERT OR IGNORE INTO lotes (lote_id, numero_gtf, titulo_habilitante_id, titular, parcela_corta, especie, volumen_total)
                VALUES ('LOT-CASCADA-1', 'GTF-C-1', 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 5.0)
            """)
            conn.execute("""
                INSERT OR IGNORE INTO operaciones (operacion_id, tipo_operacion, punto_cadena, id_arbol, lote_id, parcela_corta, especie, volumen, numero_gtf, actor_id, id_titular, fecha)
                VALUES ('OP-C-TALA', 'Tala', 2, 'ARB-CASCADA-1', 'LOT-CASCADA-1', 'PC1', 'Shihuahuaco', 5.0, 'GTF-C-1', 'ACTOR-TEST', ?, '2026-06-14')
            """, (resolver_ruc('ACTOR-TEST'),))
            conn.commit()
        finally:
            conn.close()
            
        # Validar el lote para que quede en Verde
        async with httpx.AsyncClient() as client:
            val_res = await client.get(f"{BASE_URL}/api/v1/trazabilidad/timeline/LOT-CASCADA-1", headers={"X-PIDE-Rol": "OSINFOR"})
            assert val_res.status_code == 200
            print(f"[TEST] Semáforo inicial del lote cascada: {val_res.json()['color_semaforo']}")
            
        # Penalizar el árbol origen mediante endpoint administrativo
        async with httpx.AsyncClient() as client:
            penalizar_payload = {
                "arbol_id": "ARB-CASCADA-1",
                "motivo": "Árbol fantasma detectado por OSINFOR"
            }
            res_penalizar = await client.post(
                f"{BASE_URL}/api/v1/supervision/penalizar-origen",
                json=penalizar_payload,
                headers={"X-PIDE-Rol": "OSINFOR"},
                timeout=30.0
            )
        assert res_penalizar.status_code == 200
        print(f"[TEST] Respuesta de penalización: {res_penalizar.json()}")
        
        # Verificar estado final del lote y del árbol
        conn = get_connection()
        try:
            arbol_f = conn.execute("SELECT estado FROM censo_forestal WHERE id_arbol = 'ARB-CASCADA-1'").fetchone()
            assert arbol_f["estado"] == "FRAUDE_DETECTADO"
            
            lote_f = conn.execute("SELECT * FROM lotes WHERE lote_id = 'LOT-CASCADA-1'").fetchone()
            print(f"[TEST] Lote final semáforo: {lote_f['color_semaforo']}")
            print(f"[TEST] Lote final mensaje: {lote_f['mensaje_validacion']}")
            assert lote_f["color_semaforo"] == "Rojo"
            assert lote_f["mensaje_validacion"].startswith("[ALERTA RETROACTIVA OSINFOR]")
            
            # Verificar auditoría criptográfica
            audit_f = conn.execute("SELECT * FROM logs_auditoria WHERE entidad_id = 'LOT-CASCADA-1' AND tipo_actor = 'OSINFOR'").fetchone()
            assert audit_f is not None
            assert audit_f["accion"] == "BLOQUEAR_LOTE"
            print("[TEST] PRUEBA CASCADA RETROACTIVA COMPLETADA CON ÉXITO: Penalización ex-post propagada con éxito.")
        finally:
            conn.close()

        # ───────────────────────────────────────────────────────────
        # NUEVOS TESTS DE INTEGRIDAD Y ROLES PCM/PIDE
        # ───────────────────────────────────────────────────────────
        print("\n" + "-" * 50)
        print("EJECUTANDO NUEVOS TESTS DE INTEGRIDAD Y ROLES PIDE")
        print("-" * 50)

        async with httpx.AsyncClient() as client:
            # 1. Test de Integridad de Plan (Sin plan aprobado)
            # Preinsertar titular y título pero NO plan
            conn = get_connection()
            try:
                conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES ('20555555555', 'Titular No Plan', 'Direccion')")
                conn.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES ('TH-NO-PLAN', '20555555555', 'Concesion Sin Plan', 'Puno')")
                conn.commit()
            finally:
                conn.close()

            print("[TEST] 1. Ejecutando Test de Integridad de Plan (Tala sin plan)...")
            res_no_plan = await client.post(
                f"{BASE_URL}/api/v1/operaciones/registrar",
                json={
                    "tipo_operacion": "Tala",
                    "punto_cadena": 2,
                    "arbol_id": "ARB-NO-PLAN",
                    "parcela_corta": "PC1",
                    "especie": "Shihuahuaco",
                    "volumen": 5.0,
                    "actor_id": "ACTOR-NO-PLAN",
                    "fecha": "2026-06-14"
                },
                headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20555555555"}
            )
            print(f"[TEST] Resultado Tala sin plan: status={res_no_plan.status_code}, respuesta={res_no_plan.text}")
            assert res_no_plan.status_code == 400
            assert "No existe un Plan de Aprovechamiento aprobado" in res_no_plan.json()["detail"]
            print("[TEST] Test de Integridad de Plan aprobado con éxito.")

            # 2. Test de Relación Actor-Título (403 si RUC ajeno intenta registrar)
            print("[TEST] 2. Ejecutando Test de Relación Actor-Título (RUC ajeno)...")
            res_wrong_actor = await client.post(
                f"{BASE_URL}/api/v1/operaciones/registrar",
                json={
                    "tipo_operacion": "Tala",
                    "punto_cadena": 2,
                    "arbol_id": "ARB-A-0-0",
                    "parcela_corta": "PC1",
                    "especie": "Shihuahuaco",
                    "volumen": 1.0,
                    "actor_id": "ACTOR-LOAD",
                    "fecha": "2026-06-14"
                },
                headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20999999999"} # RUC ajeno
            )
            print(f"[TEST] Resultado RUC ajeno: status={res_wrong_actor.status_code}, respuesta={res_wrong_actor.text}")
            assert res_wrong_actor.status_code == 403
            assert "no pertenece al Titular autenticado" in res_wrong_actor.json()["detail"]
            print("[TEST] Test de Relación Actor-Título aprobado con éxito.")

            # 3. Test de Actualización de Versión (Versioning & Volume validation)
            print("[TEST] 3. Ejecutando Test de Actualización de Versión...")
            # Subir Version 1 del plan con 10.0 m3
            plan_v1_path = test_files_dir / "plan_v1.xlsx"
            generate_excel_file(str(plan_v1_path), [{
                "titulo_habilitante_id": "TH-001",
                "plan_id": "PLAN-V",
                "version": 1,
                "fecha_aprobacion": "2026-06-14",
                "arbol_id": "ARB-VERSION-TEST",
                "especie": "Shihuahuaco",
                "volumen_censado": 10.0
            }])

            with open(plan_v1_path, "rb") as f:
                files_v1 = {"file": (plan_v1_path.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                res_plan_v1 = await client.post(
                    f"{BASE_URL}/api/v1/planes/subir",
                    files=files_v1,
                    headers={"X-PIDE-Rol": "Regente"}
                )
            assert res_plan_v1.status_code == 201
            print(f"[TEST] Plan V1 subido: {res_plan_v1.json()}")

            # Registrar Tala de 5.0 (succeeds)
            res_tala_1 = await client.post(
                f"{BASE_URL}/api/v1/operaciones/registrar",
                json={
                    "tipo_operacion": "Tala",
                    "punto_cadena": 2,
                    "arbol_id": "ARB-VERSION-TEST",
                    "parcela_corta": "PC1",
                    "especie": "Shihuahuaco",
                    "volumen": 5.0,
                    "actor_id": "PRODUCTOR DEMO",
                    "fecha": "2026-06-14"
                },
                headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"}
            )
            assert res_tala_1.status_code == 201
            print("[TEST] Primera Tala de 5.0 registrada con éxito.")

            # Subir Version 2 del plan con volumen reducido de 2.0 m3
            plan_v2_path = test_files_dir / "plan_v2.xlsx"
            generate_excel_file(str(plan_v2_path), [{
                "titulo_habilitante_id": "TH-001",
                "plan_id": "PLAN-V",
                "version": 2,
                "fecha_aprobacion": "2026-06-15",
                "arbol_id": "ARB-VERSION-TEST",
                "especie": "Shihuahuaco",
                "volumen_censado": 2.0
            }])

            with open(plan_v2_path, "rb") as f:
                files_v2 = {"file": (plan_v2_path.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                res_plan_v2 = await client.post(
                    f"{BASE_URL}/api/v1/planes/subir",
                    files=files_v2,
                    headers={"X-PIDE-Rol": "Regente"}
                )
            assert res_plan_v2.status_code == 201
            print(f"[TEST] Plan V2 subido: {res_plan_v2.json()}")

            # Intentar registrar Tala de 5.0 (debe fallar contra saldo de V2 que es 2.0)
            res_tala_2 = await client.post(
                f"{BASE_URL}/api/v1/operaciones/registrar",
                json={
                    "tipo_operacion": "Tala",
                    "punto_cadena": 2,
                    "arbol_id": "ARB-VERSION-TEST",
                    "parcela_corta": "PC1",
                    "especie": "Shihuahuaco",
                    "volumen": 5.0,
                    "actor_id": "PRODUCTOR DEMO",
                    "fecha": "2026-06-15"
                },
                headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"}
            )
            print(f"[TEST] Resultado segunda Tala: status={res_tala_2.status_code}, respuesta={res_tala_2.text}")
            assert res_tala_2.status_code == 400
            assert "excede el saldo de su Plan de Aprovechamiento vigente" in res_tala_2.json()["detail"]
            print("[TEST] Test de Actualización de Versión aprobado con éxito.")

        print("\n" + "=" * 60)
        print("¡TODAS LAS PRUEBAS DE CONCURRENCIA E IDEMPOTENCIA EN EXCEL (XLSX) PASARON CON ÉXITO!")
        print("=" * 60)
        
    finally:
        # Cerrar el servidor Uvicorn
        print("[TEST] Apagando el servidor Uvicorn...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
            
        # Limpiar carpeta de pruebas temporales
        if test_files_dir.exists():
            shutil.rmtree(test_files_dir)
            print("[TEST] Carpeta temporal de archivos de prueba eliminada.")

def test_concurrency_all_cases():
    """Wrapper para ejecutar las pruebas de concurrencia e idempotencia bajo pytest."""
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
