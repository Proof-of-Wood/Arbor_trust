import sys
from pathlib import Path

# Configurar ruta para importar módulos locales
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from api.main import app
from database import get_connection

client = TestClient(app)

def setup_module(module):
    """
    Inserta datos de prueba estructurados en la base de datos para validar
    los privilegios e inyección de scoping.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Titular A (PRODUCTOR DEMO - 20123456789)
        cursor.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES ('20123456789', 'PRODUCTOR DEMO', 'Av. Amazonas 123')")
        cursor.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES ('TH-001', '20123456789', 'Concesion TH-001', 'Loreto')")
        cursor.execute("INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado, documento_pdf_hash) VALUES ('PLAN-DEMO-V1', 'TH-001', 1, '2026-06-14', 'Aprobado', 'HASH1')")
        cursor.execute("INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion) VALUES ('ARB-DEMO-001', 'PLAN-DEMO-V1', 'Shihuahuaco', 10.0, 'Autorizado', 'Aprovechable')")
        
        # 2. Titular B (OTRO PRODUCTOR - 20987654321)
        cursor.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre, direccion) VALUES ('20987654321', 'OTRO PRODUCTOR', 'Calle Ucayali 456')")
        cursor.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica) VALUES ('TH-002', '20987654321', 'Concesion TH-002', 'Ucayali')")
        cursor.execute("INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado, documento_pdf_hash) VALUES ('PLAN-OTRO-V1', 'TH-002', 1, '2026-06-14', 'Aprobado', 'HASH2')")
        cursor.execute("INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion) VALUES ('ARB-OTRO-001', 'PLAN-OTRO-V1', 'Shihuahuaco', 8.0, 'Autorizado', 'Aprovechable')")
        
        # 3. Lotes
        cursor.execute("INSERT OR IGNORE INTO lotes (lote_id, numero_gtf, titulo_habilitante_id, titular, parcela_corta, especie, volumen_total, estado_validacion) VALUES ('LOT-DEMO-001', 'GTF-DEMO-001', 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 10.0, 'Conforme')")
        cursor.execute("INSERT OR IGNORE INTO lotes (lote_id, numero_gtf, titulo_habilitante_id, titular, parcela_corta, especie, volumen_total, estado_validacion) VALUES ('LOT-OTRO-001', 'GTF-OTRO-001', 'TH-002', 'OTRO PRODUCTOR', 'PC1', 'Shihuahuaco', 8.0, 'Conforme')")
        
        conn.commit()
    finally:
        conn.close()

def test_search_privileges():
    """
    Valida las siguientes reglas de RBAC y Scoping:
    - Un Titular puede buscar recursos que pertenecen a sus títulos habilitantes.
    - Un Titular recibe 403 Forbidden si busca recursos ajenos.
    - OSINFOR puede buscar cualquier recurso a nivel global.
    """
    
    # ── CASO 1: Búsqueda de Árbol Propio por Titular A (20123456789) ──
    res = client.get(
        "/api/v1/trazabilidad/buscar?criterio=arbol_id&valor=ARB-DEMO-001",
        headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tipo"] == "arbol"
    assert data["id"] == "ARB-DEMO-001"
    assert data["arbol"]["id_titulo"] == "TH-001"
    
    # ── CASO 2: Búsqueda de Árbol Ajeno por Titular A (Debe fallar con 403) ──
    res = client.get(
        "/api/v1/trazabilidad/buscar?criterio=arbol_id&valor=ARB-OTRO-001",
        headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"}
    )
    assert res.status_code == 403
    assert "no pertenece a sus títulos habilitantes autorizados" in res.json()["detail"]
    
    # ── CASO 3: Búsqueda de Árbol Ajeno por OSINFOR (Acceso Global OK) ──
    res = client.get(
        "/api/v1/trazabilidad/buscar?criterio=arbol_id&valor=ARB-OTRO-001",
        headers={"X-PIDE-Rol": "OSINFOR"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tipo"] == "arbol"
    assert data["id"] == "ARB-OTRO-001"
    assert data["arbol"]["id_titulo"] == "TH-002"

    # ── CASO 4: Búsqueda de GTF Propia por Titular A ──
    res = client.get(
        "/api/v1/trazabilidad/buscar?criterio=gtf&valor=GTF-DEMO-001",
        headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tipo"] == "gtf"
    assert data["lote_id"] == "LOT-DEMO-001"

    # ── CASO 5: Búsqueda de GTF Ajena por Titular A (Debe fallar con 403) ──
    res = client.get(
        "/api/v1/trazabilidad/buscar?criterio=gtf&valor=GTF-OTRO-001",
        headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"}
    )
    assert res.status_code == 403
    
    # ── CASO 6: Búsqueda de GTF Ajena por OSINFOR (Acceso Global OK) ──
    res = client.get(
        "/api/v1/trazabilidad/buscar?criterio=gtf&valor=GTF-OTRO-001",
        headers={"X-PIDE-Rol": "OSINFOR"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tipo"] == "gtf"
    assert data["lote_id"] == "LOT-OTRO-001"

    # ── CASO 7: Búsqueda de Título Propio por Titular A ──
    res = client.get(
        "/api/v1/trazabilidad/buscar?criterio=titulo_habilitante&valor=TH-001",
        headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tipo"] == "titulo"
    assert data["id_titulo"] == "TH-001"

    # ── CASO 8: Búsqueda de Título Ajeno por Titular A (Debe fallar con 403) ──
    res = client.get(
        "/api/v1/trazabilidad/buscar?criterio=titulo_habilitante&valor=TH-002",
        headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"}
    )
    assert res.status_code == 403

def test_ignore_body_identity():
    """
    Validar que el backend ignore campos de identidad (RUC, DNI, SERFOR, Placa)
    enviados en el JSON body y asocie la operación estrictamente con los de las cabeceras PIDE.
    """
    payload = {
        "tipo_operacion": "Tala",
        "punto_cadena": 2,
        "arbol_id": "ARB-DEMO-001",
        "parcela_corta": "PC1",
        "especie": "Shihuahuaco",
        "volumen": 1.0,
        "actor_id": "PRODUCTOR DEMO",
        "fecha": "2026-06-14",
        "ruc_institucion": "20987654321",  # RUC ajeno
        "tipo_actor": "OSINFOR"  # Rol ajeno en el body
    }
    
    res = client.post(
        "/api/v1/operaciones/registrar",
        json=payload,
        headers={"X-PIDE-Rol": "Titular", "X-PIDE-RUC": "20123456789"}
    )
    
    assert res.status_code == 201
    op_id = res.json()["operacion_id"]
    
    conn = get_connection()
    try:
        row = conn.execute("SELECT ruc_institucion, id_titular, actor_id FROM operaciones WHERE operacion_id = ?", (op_id,)).fetchone()
        assert row["ruc_institucion"] == "20123456789"
        assert row["id_titular"] == "20123456789"
    finally:
        conn.close()

def test_regente_forbidden_ops():
    """
    Validar que el rol Regente no pueda registrar operaciones manuales (debe retornar 403).
    """
    payload = {
        "tipo_operacion": "Tala",
        "punto_cadena": 2,
        "arbol_id": "ARB-DEMO-001",
        "parcela_corta": "PC1",
        "especie": "Shihuahuaco",
        "volumen": 1.0,
        "actor_id": "REGENTE-TEST",
        "fecha": "2026-06-14"
    }
    
    res = client.post(
        "/api/v1/operaciones/registrar",
        json=payload,
        headers={"X-PIDE-Rol": "Regente", "X-PIDE-Serfor": "REG-SER-2026-1234"}
    )
    
    assert res.status_code == 403

