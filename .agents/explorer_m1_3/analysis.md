# Analysis Report: Milestone M1 Database DDL Refactoring Strategy

## Core Summary
This report analyzes the database schema in `backend/database.py` and proposes a comprehensive refactoring strategy to introduce the hierarchical relationship of the Peruvian forest sector (Titulares -> Títulos Habilitantes -> Planes de Aprovechamiento -> Censo Forestal). Precise schema design, data migration/seeding logic, and ripple effects across the validation engine, API, and tests are provided to guide the upcoming implementation phase.

---

## 1. Current Schema Assessment
Currently, the database schema (`backend/database.py`) uses a flat model for census trees, balances, and operations:
*   `arboles` table holds both census metadata and owner names (`titular`) in a single row, violating relational design and authority hierarchy.
*   `balances_extraccion` relies on text identifiers without foreign keys to titles.
*   `operaciones` links to `arboles` via `arbol_id` but lacks ownership link to `titulares`.

The table below summarizes the current vs. proposed refactored relational structure:

| Current Table / Column | Proposed Target Table / Column | Description of Change |
|---|---|---|
| `arboles` (table) | `censo_forestal` (table) | Renamed to reflect census forest structure. |
| `arboles.arbol_id` | `censo_forestal.id_arbol` (PK) | Rename ID column to match standard. |
| `arboles.titular` | `titulares.nombre` | Normalize out to `titulares` table with RUC/DNI as PK. |
| `arboles.titulo_habilitante_id` | `titulos_habilitantes.id_titulo` (PK) | Normalize out to `titulos_habilitantes` table. |
| (None) | `planes_aprovechamiento` (table) | Introduce new intermediate table for versioned management plans. |
| `operaciones.arbol_id` | `operaciones.id_arbol` (FK) | Rename and point FK to `censo_forestal(id_arbol)`. |
| (None) | `operaciones.id_titular` (FK) | Add FK pointing to `titulares(ruc_dni)` to trace active operator. |

---

## 2. Refactored Database DDL Specification
Below is the proposed SQLite DDL structure to be implemented in `backend/database.py` inside `DDL_STATEMENTS`.

```sql
-- 1. Table for Titulares (concession owners)
CREATE TABLE IF NOT EXISTS titulares (
    ruc_dni TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    direccion TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 2. Table for Títulos Habilitantes (concessions or properties)
CREATE TABLE IF NOT EXISTS titulos_habilitantes (
    id_titulo TEXT PRIMARY KEY,
    id_titular TEXT NOT NULL,
    nombre_concesion TEXT NOT NULL,
    ubicacion_geografica TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_titular) REFERENCES titulares(ruc_dni) ON DELETE CASCADE
);

-- 3. Table for Planes de Aprovechamiento (forest management plans, versioned)
CREATE TABLE IF NOT EXISTS planes_aprovechamiento (
    id_plan TEXT PRIMARY KEY,
    id_titulo TEXT NOT NULL,
    version INTEGER NOT NULL,
    fecha_aprobacion TEXT NOT NULL,
    estado TEXT NOT NULL CHECK(estado IN ('Aprobado', 'Actualizado', 'Vencido')),
    documento_pdf_hash TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_titulo) REFERENCES titulos_habilitantes(id_titulo) ON DELETE CASCADE
);

-- 4. Refactored Censo Forestal Table (replacing arboles)
CREATE TABLE IF NOT EXISTS censo_forestal (
    id_arbol TEXT PRIMARY KEY,
    id_plan TEXT NOT NULL,
    id_especie TEXT NOT NULL,
    volumen_autorizado REAL NOT NULL,
    estado TEXT DEFAULT 'Autorizado',
    condicion TEXT DEFAULT 'Aprovechable',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_plan) REFERENCES planes_aprovechamiento(id_plan) ON DELETE CASCADE
);

-- 5. Updated Operaciones Table with foreign key references
CREATE TABLE IF NOT EXISTS operaciones (
    operacion_id TEXT PRIMARY KEY,
    tipo_operacion TEXT NOT NULL CHECK(tipo_operacion IN ('Tala','Trozado','Despacho','Transformacion')),
    punto_cadena INTEGER NOT NULL CHECK(punto_cadena IN (2,3,4)),
    id_arbol TEXT,
    troza_id TEXT,
    lote_id TEXT,
    parcela_corta TEXT NOT NULL,
    especie TEXT NOT NULL,
    volumen REAL NOT NULL,
    numero_gtf TEXT,
    actor_id TEXT NOT NULL,
    id_titular TEXT,
    fecha TEXT NOT NULL,
    observacion TEXT,
    estado_validacion TEXT DEFAULT 'Pendiente',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_arbol) REFERENCES censo_forestal(id_arbol) ON DELETE SET NULL,
    FOREIGN KEY (lote_id) REFERENCES lotes(lote_id) ON DELETE SET NULL,
    FOREIGN KEY (id_titular) REFERENCES titulares(ruc_dni) ON DELETE SET NULL
);
```

### Required Index Modifications
The following index definitions must be updated to refer to the new column and table names:
```sql
CREATE INDEX IF NOT EXISTS idx_operaciones_lote ON operaciones(lote_id);
CREATE INDEX IF NOT EXISTS idx_operaciones_arbol ON operaciones(id_arbol);
CREATE UNIQUE INDEX IF NOT EXISTS idx_censo_unicidad ON censo_forestal(id_arbol);
CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_tala_unica ON operaciones(id_arbol) WHERE tipo_operacion = 'Tala';
CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_troza_unica ON operaciones(troza_id, tipo_operacion) WHERE troza_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_lote_unica ON operaciones(lote_id, tipo_operacion) WHERE lote_id IS NOT NULL AND troza_id IS NULL AND id_arbol IS NULL;
```

---

## 3. Seeding Strategy and Backward Compatibility
To avoid breaking current seed sheets (`arboles_sample.xlsx`, `balances_sample.xlsx`, etc.) which contain flat structure without `plan_id` or explicit `ruc_dni`, `seed_from_excel()` in `backend/database.py` must dynamically resolve the hierarchy.

### Dynamic Resolution Algorithm during Seeding:
1.  **RUC Resolution**: Map string owner names (e.g. `"PRODUCTOR DEMO"`) to standard 11-digit Peruvian RUCs. Use a deterministic generation algorithm or a predefined map.
    ```python
    def resolver_ruc(nombre_titular: str) -> str:
        # Predefined mapping or deterministic hash-based RUC starting with 20 (Peruvian corporate RUC prefix)
        predefined = {
            "PRODUCTOR DEMO": "20123456789",
            "ACTOR-LOAD": "20987654321",
            "ACTOR-SEED": "20987654321"
        }
        if nombre_titular in predefined:
            return predefined[nombre_titular]
        # Generate stable numeric hash
        h = str(abs(hash(nombre_titular)))[:9].ljust(9, '0')
        return f"20{h}"
    ```
2.  **Parent Insertions**:
    *   For each record, resolve its Titular and insert into `titulares` if not exists.
    *   Resolve Título Habilitante ID (e.g. `"TH-001"`) and insert into `titulos_habilitantes` if not exists.
    *   Create a default Plan de Aprovechamiento `"PLAN-DEFAULT"` (version `1`, state `'Aprobado'`) linked to the Title if not exists.
3.  **Census Insertions**:
    *   Insert into `censo_forestal` with `id_plan = "PLAN-DEFAULT"`.

---

## 4. Codebase Ripple Effects & Remediation Steps

### A. Modifications to `backend/database.py`
1.  **`procesar_archivo_background`**:
    *   When processing `tipo_archivo == "censo"`, support the updated spreadsheet columns specified in R2: `['titulo_habilitante_id', 'plan_id', 'version', 'fecha_aprobacion', 'arbol_id', 'especie', 'volumen_censado']`.
    *   Check ownership and insert into `planes_aprovechamiento` and `censo_forestal`.
    *   When processing `tipo_archivo == "operaciones"`, insert into `operaciones` using `id_arbol` and `id_titular`.
2.  **`penalizar_arbol_retroactivo`**:
    *   Update references of `arboles` table to `censo_forestal`.
    *   Update `arbol_id` column to `id_arbol`.
    ```python
    -- Before
    conn.execute("UPDATE arboles SET estado = 'FRAUDE_DETECTADO' WHERE arbol_id = ?", (arbol_id,))
    -- After
    conn.execute("UPDATE censo_forestal SET estado = 'FRAUDE_DETECTADO' WHERE id_arbol = ?", (arbol_id,))
    ```

### B. Modifications to `backend/engine/validation.py`
In `validar_lote()`:
*   Replace references to `arbol_id` with `id_arbol` in Pandas queries.
    ```python
    -- Line 137 in backend/engine/validation.py
    arboles_origen = ops["id_arbol"].dropna().unique()
    ```
*   Add a direct validation rule to check if any of the trees in `arboles_origen` has the state `'FRAUDE_DETECTADO'` in `censo_forestal`. This prevents new lotes from referencing penalized/fraudulent trees.

### C. Modifications to `backend/api/main.py`
*   In `registrar_operacion` endpoint, modify the SQL insert command to use the updated columns: `id_arbol` instead of `arbol_id`, and write `id_titular` (optionally resolved from headers/headers simulation).
*   In `obtener_timeline` endpoint, change output mapping from `op['arbol_id']` to `op['id_arbol']` when constructing the timeline nodes.

### D. Modifications to `backend/test_concurrency.py`
*   Modify `preinsert_test_trees()` to populate `titulares`, `titulos_habilitantes`, and `planes_aprovechamiento` prior to inserting trees into `censo_forestal`.
*   Update case D and case cascada insert statements to point to the new tables.

---

## 5. Verification Plan
To verify the database refactoring, execute:
1.  Initialize database: `python backend/database.py` (Verify it runs without SQL syntax errors and creates the updated tables).
2.  Run the tests: `pytest backend/test_concurrency.py` (Once the implementer adapts the test queries, the entire suite should pass 100% without locked database errors).
