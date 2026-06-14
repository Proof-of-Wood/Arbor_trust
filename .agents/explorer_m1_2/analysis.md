# Milestone M1 Analysis & Refactoring Strategy: Database DDL Refactoring

## 1. Executive Summary
This document presents the analysis and detailed strategy for refactoring the database schema of the **ArborTrust** platform to represent the hierarchical structure of the Peruvian forest sector (OSINFOR/SERFOR regulations).
The goal is to transition from a flat representation of trees and operations to a hierarchical model:
`Titulares` ➔ `Titulos Habilitantes` ➔ `Planes de Aprovechamiento` ➔ `Censo Forestal` ➔ `Operaciones`.
This document details the new SQL DDL statements, updates to seed/ingestion tasks, backward compatibility mappings, impacts on validation/APIs, and verification instructions.

---

## 2. Hierarchical Database Model & DDL Design

The database will be refactored into five main tables supporting cascade operations, foreign key integrity, index optimizations, and WAL (Write-Ahead Logging) concurrence compliance.

### 2.1 Entity Relationship Diagram (Mental Model)
```
[Titulares] (PK: ruc_dni)
    └── [Titulos_Habilitantes] (PK: id_titulo, FK: id_titular)
          └── [Planes_Aprovechamiento] (PK: id_plan, FK: id_titulo)
                └── [Censo_Forestal] (PK: id_arbol, FK: id_plan)
                      └── [Operaciones] (PK: id_operacion, FK: id_arbol, FK: id_titular)
```

### 2.2 Refactored SQL Definitions
The new schema replaces the existing `arboles` table with `censo_forestal` and inserts the intermediate hierarchical relations (`titulares`, `titulos_habilitantes`, `planes_aprovechamiento`). It also adjusts the `operaciones` table columns.

#### Table: `titulares`
Holds unique identification (RUC/DNI) for concession/predio owners.
```sql
CREATE TABLE IF NOT EXISTS titulares (
    ruc_dni             TEXT PRIMARY KEY,
    nombre              TEXT NOT NULL,
    direccion           TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);
```

#### Table: `titulos_habilitantes`
Represents titles representing rights to use forest resources.
```sql
CREATE TABLE IF NOT EXISTS titulos_habilitantes (
    id_titulo           TEXT PRIMARY KEY,
    id_titular          TEXT NOT NULL,
    nombre_concesion    TEXT,
    ubicacion_geografica TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_titular) REFERENCES titulares(ruc_dni) ON DELETE CASCADE
);
```

#### Table: `planes_aprovechamiento`
Tracks specific operational/census plans (with multiple versions supported in future milestones).
```sql
CREATE TABLE IF NOT EXISTS planes_aprovechamiento (
    id_plan             TEXT PRIMARY KEY,
    id_titulo           TEXT NOT NULL,
    version             INTEGER NOT NULL,
    fecha_aprobacion    TEXT,
    estado              TEXT DEFAULT 'Aprobado' CHECK(estado IN ('Aprobado','Actualizado','Vencido')),
    documento_pdf_hash  TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_titulo) REFERENCES titulos_habilitantes(id_titulo) ON DELETE CASCADE
);
```

#### Table: `censo_forestal`
Stores authorized trees associated with specific approved plans. Replaces `arboles`.
```sql
CREATE TABLE IF NOT EXISTS censo_forestal (
    id_arbol            TEXT PRIMARY KEY,
    id_plan             TEXT NOT NULL,
    id_especie          TEXT NOT NULL,
    volumen_autorizado  REAL NOT NULL,
    estado              TEXT DEFAULT 'Autorizado',
    condicion           TEXT DEFAULT 'Aprovechable',
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_plan) REFERENCES planes_aprovechamiento(id_plan) ON DELETE CASCADE
);
```

#### Table: `operaciones`
Refactored to point to `censo_forestal` (`id_arbol`) and the responsible actor/owner (`id_titular`), preserving audit fields.
```sql
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
);
```

### 2.3 Optimization Indexes & Unique Constraints
Update the SQLite index set to target new tables and columns to ensure high performance and idempotency under concurrent workloads:
```sql
CREATE INDEX IF NOT EXISTS idx_operaciones_lote ON operaciones(lote_id);
CREATE INDEX IF NOT EXISTS idx_operaciones_arbol ON operaciones(id_arbol);
CREATE UNIQUE INDEX IF NOT EXISTS idx_arboles_unicidad ON censo_forestal(id_arbol);
CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_tala_unica ON operaciones(id_arbol) WHERE tipo_operacion = 'Tala';
CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_troza_unica ON operaciones(troza_id, tipo_operacion) WHERE troza_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_lote_unica ON operaciones(lote_id, tipo_operacion) WHERE lote_id IS NOT NULL AND troza_id IS NULL AND id_arbol IS NULL;
```

---

## 3. Ingestion & Seed Ingestion Strategy (Backward Compatibility)

### 3.1 Migration of Excel Seed Data
The database seed module (`seed_from_excel`) must parse existing legacy samples (like `arboles_sample.xlsx` which has columns: `arbol_id`, `titulo_habilitante_id`, `titular`, `parcela_corta`, `especie`, `volumen_censado`, `estado`, `condicion`) and populate the normalized tables dynamically.

**Seed Logic Flow**:
1. **Derive Titular**: Use a deterministic RUC generator helper `get_ruc_for_titular(nombre)` (e.g. converting "PRODUCTOR DEMO" to RUC `"20123456789"`). Insert into `titulares`.
2. **Derive Title**: Insert `titulo_habilitante_id` into `titulos_habilitantes` using the derived RUC.
3. **Derive Plan**: Insert `PLAN-{titulo_habilitante_id}` into `planes_aprovechamiento` (with default `version = 1`, `fecha_aprobacion = '2026-06-14'`).
4. **Insert Census**: Insert rows into `censo_forestal` linking to the derived `id_plan`.
5. **Deduplicate & Seed Balances/Lotes**: Ensure related titles are registered beforehand.
6. **Insert Operations**: Link operations to `id_arbol` and `id_titular` by looking up the tree owner inside `censo_forestal ➔ planes_aprovechamiento ➔ titulos_habilitantes`.

### 3.2 Update Spreadsheet Ingestion (`procesar_archivo_background`)
- **Censo Spreadsheet**: The spreadsheet parser will support both the legacy sample structure and the new M2 metadata template (`['titulo_habilitante_id', 'plan_id', 'version', 'fecha_aprobacion', 'arbol_id', 'especie', 'volumen_censado']`). It dynamically checks column existence, creates parent entities (`titulares`, `titulos_habilitantes`, `planes_aprovechamiento`) if missing, and then bulk upserts `censo_forestal`.
- **Operations Spreadsheet**: When importing tala/transport operations, look up the RUC of the title owner associated with the tree ID to populate `id_titular` in `operaciones`.

---

## 4. Codebase Impact Analysis

### 4.1 Changes required in `backend/database.py`
- Replace `DDL_STATEMENTS` with the refactored schemas.
- Refactor `seed_from_excel()` to handle the multi-level hierarchy seeding from flat files.
- Refactor `procesar_archivo_background()` to correctly resolve references for both `censo` and `operaciones` spreadsheet ingestion.
- Refactor `penalizar_arbol_retroactivo()` to update `censo_forestal` and join using `id_arbol` and `id_operacion` columns.

### 4.2 Changes required in `backend/api/main.py`
- **Pydantic Models**: Keep the API schema compatible (e.g., `arbol_id` can be mapped to database column `id_arbol`).
- **Endpoint `registrar_operacion`**: Map the insert statement fields to `id_operacion`, `id_arbol`, and resolve/insert `id_titular`.
- **Endpoint `obtener_timeline`**: To avoid API breakages, execute the SQL query aliasing `id_arbol AS arbol_id` and `id_operacion AS operacion_id`:
  ```sql
  SELECT *, id_arbol AS arbol_id, id_operacion AS operacion_id FROM operaciones WHERE ...
  ```
  This is a critical backward compatibility pattern that prevents UI/API response contract breakages.

### 4.3 Changes required in `backend/engine/validation.py`
- Update database queries on `operaciones` to refer to `id_arbol` instead of `arbol_id`.
  - Line 137: Change `ops["arbol_id"]` to `ops["id_arbol"]`.
  - Line 108-111: Join `titulos_habilitantes` to verify titles if needed.

---

## 5. Test Harness Adaptation (`test_concurrency.py`)

The test suite relies heavily on pre-inserting trees to satisfy foreign key constraints. With a hierarchical model, `test_concurrency.py`'s `preinsert_test_trees()` will fail unless it inserts the parent hierarchy.

### 5.1 Proposed updates to `preinsert_test_trees()`
Update the pre-insertion code in `backend/test_concurrency.py` to insert necessary hierarchical records first:
```python
def preinsert_test_trees():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Preinsert Titular
        cursor.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre) VALUES ('20123456789', 'PRODUCTOR DEMO')")
        
        # 2. Preinsert Title
        cursor.execute("INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion) VALUES ('TH-001', '20123456789', 'Concesión Demo')")
        
        # 3. Preinsert Plan
        cursor.execute("INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion) VALUES ('PLAN-TH-001', 'TH-001', 1, '2026-06-14')")
        
        # 4. Preinsert trees in censo_forestal
        # Modify the insertions to write to censo_forestal and set id_plan = 'PLAN-TH-001'
        ...
        conn.commit()
    finally:
        conn.close()
```

---

## 6. Proposed implementation file location
A fully syntax-checked implementation proposal has been written to the agent's folder:
`c:\Users\Acer\Desktop\Estudio\Proyectos\ArborTrust\Arbor_trust\.agents\explorer_m1_2\proposed_database.py`

This file can be directly reviewed and integrated into `backend/database.py` during implementation.
