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
from database import get_connection, init_db, seed_from_csv

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
    seed_from_csv()
    print("[TEST] Base de datos inicializada y sembrada desde CSV.")

def preinsert_test_trees():
    """Pre-inserta los árboles necesarios en la tabla 'arboles' para que las pruebas pasen las FKs y Constraints."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        print("[TEST] Pre-insertando árboles de prueba...")
        
        # 1. Árboles para Caso A
        for i in range(10):
            for j in range(5):
                cursor.execute("""
                    INSERT OR IGNORE INTO arboles (arbol_id, titulo_habilitante_id, titular, parcela_corta, especie, volumen_censado)
                    VALUES (?, 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 10.0)
                """, (f"ARB-A-{i}-{j}",))
                
        # 2. Árboles para Caso B
        cursor.execute("""
            INSERT OR IGNORE INTO arboles (arbol_id, titulo_habilitante_id, titular, parcela_corta, especie, volumen_censado)
            VALUES ('ARB-B-1', 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 10.0)
        """)
        
        # 3. Árboles para Caso C
        for i in range(500):
            cursor.execute("""
                INSERT OR IGNORE INTO arboles (arbol_id, titulo_habilitante_id, titular, parcela_corta, especie, volumen_censado)
                VALUES (?, 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 10.0)
            """, (f"ARB-C-{i}",))
            
        # 4. Árboles para Caso D
        for i in range(5):
            cursor.execute("""
                INSERT OR IGNORE INTO arboles (arbol_id, titulo_habilitante_id, titular, parcela_corta, especie, volumen_censado)
                VALUES (?, 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 10.0)
            """, (f"ARB-D1-{i}",))
            cursor.execute("""
                INSERT OR IGNORE INTO arboles (arbol_id, titulo_habilitante_id, titular, parcela_corta, especie, volumen_censado)
                VALUES (?, 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 10.0)
            """, (f"ARB-D2-{i}",))
            
        conn.commit()
        print("[TEST] Pre-inserción de árboles de prueba exitosa.")
    finally:
        conn.close()

def generate_csv_file(path: str, rows: list):
    """Genera un archivo CSV con las filas especificadas."""
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8")

async def main():
    print("=" * 60)
    print("INICIANDO PRUEBAS DE CONCURRENCIA E IDEMPOTENCIA EN CSV")
    print("=" * 60)
    
    # 1. Resetear base de datos y pre-insertar árboles
    reset_database()
    preinsert_test_trees()
    
    # 2. Levantar el servidor Uvicorn en un puerto separado
    print(f"[TEST] Iniciando servidor Uvicorn en el puerto {PORT}...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(BACKEND_DIR)
    )
    
    # Esperar a que el servidor esté listo
    time.sleep(3)
    
    # Verificar si el servidor está levantado
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{BASE_URL}/api/v1/reportes/fallas")
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
        print("EJECUTANDO CASO A: 10 Cargas Simultáneas de Archivos CSV Diferentes")
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
            
            filepath = test_files_dir / f"test_a_{i}.csv"
            generate_csv_file(str(filepath), rows)
            filenames.append(filepath)
            
        # Lanzar las 10 peticiones de subida al mismo tiempo
        start_time = time.time()
        async def upload_file(client, filepath):
            with open(filepath, "rb") as f:
                # Enviar con el MIME type correcto para CSV
                files = {"file": (filepath.name, f, "text/csv")}
                return await client.post(
                    f"{BASE_URL}/api/v1/trazabilidad/cargar-archivo?tipo_archivo=operaciones",
                    files=files,
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
                    status_res = await client.get(f"{BASE_URL}/api/v1/trazabilidad/estado/{jid}")
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
        print("EJECUTANDO CASO B: Intento de Duplicidad de Archivo CSV Idéntico")
        print("-" * 50)
        
        # Generar un archivo único
        filepath_b = test_files_dir / "test_b.csv"
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
        generate_csv_file(str(filepath_b), rows_b)
        
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
            
        filepath_c = test_files_dir / "test_c.csv"
        generate_csv_file(str(filepath_c), rows_c)
        
        # Cargar archivo
        async with httpx.AsyncClient() as client:
            res_c = await upload_file(client, filepath_c)
            
        assert res_c.status_code == 202
        jid_c = res_c.json()["job_id"]
        print(f"[TEST] Archivo corrupto subido. Job ID: {jid_c}")
        
        # Esperar a que el job falle
        while True:
            async with httpx.AsyncClient() as client:
                status_res = await client.get(f"{BASE_URL}/api/v1/trazabilidad/estado/{jid_c}")
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
        
        filepath_d1 = test_files_dir / "test_d1.csv"
        filepath_d2 = test_files_dir / "test_d2.csv"
        generate_csv_file(str(filepath_d1), rows_d1)
        generate_csv_file(str(filepath_d2), rows_d2)
        
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
                    status_res = await client.get(f"{BASE_URL}/api/v1/trazabilidad/estado/{jid}")
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

        print("\n" + "=" * 60)
        print("¡TODAS LAS PRUEBAS DE CONCURRENCIA E IDEMPOTENCIA EN CSV PASARON CON ÉXITO!")
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

if __name__ == "__main__":
    asyncio.run(main())
