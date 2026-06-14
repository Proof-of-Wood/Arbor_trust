# Milestone M1: Database DDL Refactoring Strategy & Recommendations

## 1. Executive Summary
The primary goal of Milestone M1 is to refactor the ArborTrust database schema from its current flat structure into a normalized, hierarchical relational model that accurately reflects the Peruvian forest sector's official chain of authority (RENIEC, SUNAT, SERFOR, and OSINFOR).

This report outlines:
1. **The Target Hierarchical Schema**: Detailed structure of `titulares`, `titulos_habilitantes`, `planes_aprovechamiento`, `censo_forestal`, and `operaciones`.
2. **DDL Statements**: Exact SQLite DDL scripts to replace the legacy schema.
3. **Data Seeding & Migration**: Strategy to ingest flat sample files (`arboles_sample.xlsx`, etc.) into the normalized schema.
4. **Codebase Ripple Effects**: Detailed impact assessment on background processors, validation engines, API endpoints, and test fixtures.

---

## 2. Legacy vs. Refactored Relational Schema

Currently, the `arboles` table is flat and violates relational database normalization principles by blending actors (titulares), rights (títulos habilitantes), and physical entities (censored trees).

### Conceptual Mapping
| Legacy Table & Columns | Refactored Table & Columns | Normalization Rationale |
| :--- | :--- | :--- |
| **`arboles`** (Table) | **`censo_forestal`** (Table) | Renamed to represent physical inventory. |
| `arboles.titular` (string name) | **`titulares`** (Table) with `ruc_dni` (PK) and `nombre` | Extracts actor metadata. Integrates with Peruvian SUNAT/RENIEC identity systems. |
| `arboles.titulo_habilitante_id` | **`titulos_habilitantes`** (Table) with `id_titulo` (PK) and `id_titular` (FK) | Establishes legal concession ownership. |
| (Implicit in codebase) | **`planes_aprovechamiento`** (Table) with `id_plan` (PK), `id_titulo` (FK), `version`, `fecha_aprobacion`, `estado`, and `documento_pdf_hash` | Enables versioning of forest management plans (M2 prerequisite). |
| `arboles.arbol_id` (PK) | `censo_forestal.id_arbol` (PK) | Represents unique census tree identifier. |
| `arboles.volumen_censado` | `censo_forestal.volumen_autorizado` | Renamed to represent the legal authorized logging volume. |

---

## 3. Proposed SQLite DDL Implementation

The legacy creation statements for `arboles` and `operaciones` inside `DDL_STATEMENTS` in `backend/database.py` should be replaced with the following normalized structure:

```sql
-- 1. Titulares (SUNAT/RENIEC Registry)
CREATE TABLE IF NOT EXISTS titulares (
    ruc_dni             TEXT PRIMARY KEY,
    nombre              TEXT NOT NULL,
    direccion           TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

-- 2. Títulos Habilitantes (Concessions/Predios)
CREATE TABLE IF NOT EXISTS titulos_habilitantes (
    id_titulo           TEXT PRIMARY KEY,
    id_titular          TEXT NOT NULL,
    nombre_concesion    TEXT NOT NULL,
    ubicacion_geografica TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_titular) REFERENCES titulares(ruc_dni) ON DELETE CASCADE
);

-- 3. Planes de Aprovechamiento (Forest Management Plans)
CREATE TABLE IF NOT EXISTS planes_aprovechamiento (
    id_plan             TEXT PRIMARY KEY,
    id_titulo           TEXT NOT NULL,
    version             INTEGER NOT NULL,
    fecha_aprobacion    TEXT NOT NULL,
    estado              TEXT NOT NULL CHECK(estado IN ('Aprobado', 'Actualizado', 'Vencido')),
    documento_pdf_hash  TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_titulo) REFERENCES titulos_habilitantes(id_titulo) ON DELETE CASCADE
);

-- 4. Censo Forestal (Physical Trees)
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

-- 5. Operaciones (Refactored to enforce FK constraints)
CREATE TABLE IF NOT EXISTS operaciones (
    id_operacion        TEXT PRIMARY KEY,
    id_arbol            TEXT,
    id_titular          TEXT NOT NULL,
    tipo_operacion      TEXT NOT NULL CHECK(tipo_operacion IN ('Tala', 'Trozado', 'Despacho', 'Transformacion')),
    punto_cadena        INTEGER NOT NULL CHECK(punto_cadena IN (2, 3, 4)),
    troza_id            TEXT,
    lote_id             TEXT,
    parcela_corta       TEXT NOT NULL,
    especie             TEXT NOT NULL,
    volumen             REAL NOT NULL,
    numero_gtf          TEXT,
    fecha               TEXT NOT NULL,
    observacion         TEXT,
    estado_validacion   TEXT DEFAULT 'Pendiente',
    created_at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (id_arbol) REFERENCES censo_forestal(id_arbol) ON DELETE SET NULL,
    FOREIGN KEY (id_titular) REFERENCES titulares(ruc_dni) ON DELETE CASCADE,
    FOREIGN KEY (lote_id) REFERENCES lotes(lote_id) ON DELETE SET NULL
);
```

### Relational Index Updates
The following indices must be adjusted to align with renamed fields:
```python
DDL_STATEMENTS = [
    # ... Create Table DDL statements above ...
    "CREATE INDEX IF NOT EXISTS idx_operaciones_lote ON operaciones(lote_id)",
    "CREATE INDEX IF NOT EXISTS idx_operaciones_arbol ON operaciones(id_arbol)",
    "CREATE INDEX IF NOT EXISTS idx_logs_entidad ON logs_auditoria(entidad_id)",
    "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs_auditoria(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_validaciones_lote ON validaciones(lote_id)",
    "CREATE INDEX IF NOT EXISTS idx_validaciones_color ON validaciones(color_semaforo)",
    
    -- Unique Constraints to prevent double entries
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_tala_unica ON operaciones(id_arbol) WHERE tipo_operacion = 'Tala'",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_troza_unica ON operaciones(troza_id, tipo_operacion) WHERE troza_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_operaciones_lote_unica ON operaciones(lote_id, tipo_operacion) WHERE lote_id IS NOT NULL AND troza_id IS NULL AND id_arbol IS NULL"
]
```

---

## 4. Seeding & Migration Strategy

The seed Excel spreadsheet files (`arboles_sample.xlsx`, `balances_sample.xlsx`, etc.) contain flat rows with names (e.g. `"PRODUCTOR DEMO"`) and lack explicit `id_plan` or `id_titular` references. 

To maintain backward compatibility, the seeding logic in `seed_from_excel()` must be rewritten to dynamically map flat records into the hierarchical structure.

### 4.1 RUC/DNI Resolution Helper
Since flat tables only contain titular names, we must map them to valid 11-digit Peruvian corporate RUCs:
```python
def resolver_ruc(nombre_titular: str) -> str:
    """Mapea de forma determinista nombres a RUCs válidos del Perú."""
    mapping = {
        "PRODUCTOR DEMO": "20123456789",
        "ACTOR-SEED": "20987654321",
        "ACTOR-LOAD": "20555555555"
    }
    # Fallback determinista
    if nombre_titular in mapping:
        return mapping[nombre_titular]
    import hashlib
    # Genera un RUC válido comenzando con '20'
    digest = hashlib.sha256(nombre_titular.encode()).hexdigest()
    return "20" + str(int(digest, 16))[:9]
```

### 4.2 Seed Execution Order
```python
# 1. Seed Titulares, Títulos, and Planes from arboles_sample.xlsx
df_arboles = pd.read_excel(DATA_DIR / "arboles_sample.xlsx")
for _, row in df_arboles.iterrows():
    ruc = resolver_ruc(str(row["titular"]))
    # Insert Titular
    conn.execute("INSERT OR IGNORE INTO titulares (ruc_dni, nombre) VALUES (?, ?)", (ruc, str(row["titular"])))
    
    # Insert Título Habilitante
    conn.execute("""
        INSERT OR IGNORE INTO titulos_habilitantes (id_titulo, id_titular, nombre_concesion, ubicacion_geografica)
        VALUES (?, ?, ?, 'Loreto, Perú')
    """, (str(row["titulo_habilitante_id"]), ruc, f"Concesión {row['titulo_habilitante_id']}"))
    
    # Insert Plan de Aprovechamiento (Default to version 1)
    plan_id = f"PLAN-{row['titulo_habilitante_id']}"
    conn.execute("""
        INSERT OR IGNORE INTO planes_aprovechamiento (id_plan, id_titulo, version, fecha_aprobacion, estado, documento_pdf_hash)
        VALUES (?, ?, 1, '2026-01-01', 'Aprobado', 'HASH-DEFAULT-PDF')
    """, (plan_id, str(row["titulo_habilitante_id"])))
    
    # Insert Censo Forestal (Physical Tree)
    conn.execute("""
        INSERT OR IGNORE INTO censo_forestal (id_arbol, id_plan, id_especie, volumen_autorizado, estado, condicion)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (str(row["arbol_id"]), plan_id, str(row["especie"]), float(row["volumen_censado"]), row["estado"], row["condicion"]))

# 2. Seed Operaciones
df_ops = pd.read_excel(DATA_DIR / "operaciones_sample.xlsx")
for _, row in df_ops.iterrows():
    # Encontrar RUC del titular del árbol o asignar un default
    id_arbol = str(row["arbol_id"]) if pd.notna(row["arbol_id"]) and row["arbol_id"] != "" else None
    ruc = "20123456789" # Default
    if id_arbol:
        res = conn.execute("""
            SELECT th.id_titular FROM censo_forestal c
            JOIN planes_aprovechamiento p ON c.id_plan = p.id_plan
            JOIN titulos_habilitantes th ON p.id_titulo = th.id_titulo
            WHERE c.id_arbol = ?
        """, (id_arbol,)).fetchone()
        if res:
            ruc = res["id_titular"]
            
    conn.execute("""
        INSERT OR IGNORE INTO operaciones
        (id_operacion, id_arbol, id_titular, tipo_operacion, punto_cadena, troza_id,
         parcela_corta, especie, volumen, numero_gtf, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(row["operacion_id"]), id_arbol, ruc, row["tipo_operacion"], 2,
          str(row["troza_id"]) if row["troza_id"] != "" else None,
          row["parcela_corta"], row["especie"], float(row["volumen"]),
          str(row["numero_gtf"]) if row["numero_gtf"] != "" else None, row["fecha"]))
```

---

## 5. ripple Effects Analysis & Necessary Modifications

Every file referencing the legacy database schema must be refactored. The following sections list the specific adjustments required:

### 5.1 Background Job Parser (`backend/database.py`)
- **Censo Upload Flow**: 
  When a Regente uploads a new censo forestal, the background process must insert/update the `titulares`, `titulos_habilitantes`, `planes_aprovechamiento`, and `censo_forestal` tables hierarchically.
- **Atomic Operations Upload Flow**:
  When processing operation lists, the background job must write to `operaciones` using the new column names (`id_operacion`, `id_arbol`, `id_titular` instead of `operacion_id`, `arbol_id`, `actor_id`).

### 5.2 OSINFOR Cascade Penalization (`backend/database.py`)
The `penalizar_arbol_retroactivo` method must be updated as follows:
- `UPDATE arboles SET estado = 'FRAUDE_DETECTADO' WHERE arbol_id = ?` 
  $\rightarrow$ `UPDATE censo_forestal SET estado = 'FRAUDE_DETECTADO' WHERE id_arbol = ?`
- `SELECT DISTINCT lote_id, troza_id FROM operaciones WHERE arbol_id = ?`
  $\rightarrow$ `SELECT DISTINCT lote_id, troza_id FROM operaciones WHERE id_arbol = ?`

### 5.3 Validation Rules Engine (`backend/engine/validation.py`)
- **Regla `existencia_arbol`**:
  Must check `censo_forestal` instead of `arboles`.
  ```python
  arboles_origen = ops["id_arbol"].dropna().unique()
  ```
- **Regla `volumen_disponible`**:
  Must query `balances_extraccion` based on `id_titulo` and `id_especie`.

### 5.4 FastAPI Endpoints (`backend/api/main.py`)
- **`POST /api/v1/operaciones/registrar`**:
  Update payload mappings to construct the INSERT statement using the refactored columns:
  - Map `payload.arbol_id` $\rightarrow$ `id_arbol`
  - Map `payload.actor_id` $\rightarrow$ `id_titular` (RUC/DNI)
  - Map `op_id` $\rightarrow$ `id_operacion`
- **`GET /api/v1/trazabilidad/timeline/{id_lote}`**:
  Update the query selecting from `operaciones` to retrieve the correct column names, mapping `op['id_arbol']` and `op['id_operacion']` to the JSON nodes.

### 5.5 Test Suite Fixtures (`backend/test_concurrency.py`)
- **`preinsert_test_trees()`**:
  Must insert into the new hierarchical structures (`titulares`, `titulos_habilitantes`, `planes_aprovechamiento`, `censo_forestal`) rather than just `arboles`.
- **Concurrency Test Operations Payload**:
  Verify that the tests send `arbol_id` but the backend maps it to `id_arbol` and validates it successfully.

---

## 6. Implementation & Verification Plan

An implementer should execute the DDL refactoring by following this sequence:

1. **Step 1**: Modify `DDL_STATEMENTS` in `backend/database.py` with the proposed DDL.
2. **Step 2**: Rebuild the `seed_from_excel()` function to parse flat files into the normalized schema.
3. **Step 3**: Rebuild `preinsert_test_trees()` in `backend/test_concurrency.py`.
4. **Step 4**: Apply schema changes across `backend/engine/validation.py` and `backend/api/main.py`.
5. **Step 5**: Run the automated test suite to ensure the migration did not break the concurrency and idempotency rules:
   ```bash
   python -m pytest backend/test_concurrency.py
   ```
