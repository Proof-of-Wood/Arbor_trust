# Handoff Report — 2026-06-14T19:26:20Z

This handoff report summarizes the investigation findings and recommended refactoring strategy for Milestone M1 (Database DDL Refactoring) of the ArborTrust project.

## 1. Observation
*   **File Path & Lines**: `backend/database.py` lines 20-31 define the flat `arboles` schema containing both metadata and owner names (`titular`):
    ```python
    CREATE TABLE IF NOT EXISTS arboles (
        arbol_id             TEXT PRIMARY KEY,
        titulo_habilitante_id TEXT NOT NULL,
        titular              TEXT NOT NULL,
        parcela_corta        TEXT NOT NULL,
        especie              TEXT NOT NULL,
        volumen_censado      REAL NOT NULL,
        estado               TEXT DEFAULT 'Autorizado',
        condicion            TEXT DEFAULT 'Aprovechable',
        created_at           TEXT DEFAULT (datetime('now'))
    )
    ```
*   **File Path & Lines**: `backend/database.py` lines 50-68 define the `operaciones` schema referencing `arboles(arbol_id)`:
    ```python
    CREATE TABLE IF NOT EXISTS operaciones (
        operacion_id    TEXT PRIMARY KEY,
        tipo_operacion  TEXT NOT NULL CHECK(tipo_operacion IN ('Tala','Trozado','Despacho','Transformacion')),
        punto_cadena    INTEGER NOT NULL CHECK(punto_cadena IN (2,3,4)),
        arbol_id        TEXT REFERENCES arboles(arbol_id),
        ...
    )
    ```
*   **File Path & Lines**: `backend/engine/validation.py` lines 101, 137 check tree references in dataframe filters:
    ```python
    ops = pd.read_sql_query("SELECT * FROM operaciones WHERE lote_id = ?", conn, params=(lote_id,))
    arboles_origen = ops["arbol_id"].dropna().unique()
    ```
*   **File Path & Lines**: `backend/api/main.py` lines 200-208 insert operations and line 277 retrieves tree details from operations:
    ```python
    conn.execute("""
        INSERT INTO operaciones
        (operacion_id, tipo_operacion, punto_cadena, arbol_id, troza_id, lote_id,
         parcela_corta, especie, volumen, numero_gtf, actor_id, fecha, observacion)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """)
    ...
    if op['arbol_id']: detalle += f", Árbol: {op['arbol_id']}"
    ```
*   **File Path & Lines**: `backend/test_concurrency.py` lines 39-81 pre-insert test trees into the database:
    ```python
    cursor.execute("""
        INSERT OR IGNORE INTO arboles (arbol_id, titulo_habilitante_id, titular, parcela_corta, especie, volumen_censado)
        VALUES (?, 'TH-001', 'PRODUCTOR DEMO', 'PC1', 'Shihuahuaco', 10.0)
    """)
    ```

## 2. Logic Chain
1.  **Normalization Necessity**: The current `arboles` table violates the hierarchical relationship specified in the Peruvian forest sector because it merges the owner (Titular), the title, and the physical tree into a single flat model. Breaking this flat structure into four separate normalized tables (`titulares`, `titulos_habilitantes`, `planes_aprovechamiento`, and `censo_forestal`) resolves the relationship cleanly.
2.  **Referential Integrity Ripple**: By renaming `arboles` to `censo_forestal` and modifying primary/foreign keys (`arbol_id` to `id_arbol`, referencing `censo_forestal` instead of `arboles`), any database queries or DDL statements that query `arboles` or reference `arbol_id` must be adapted.
3.  **Engine and API Updates**: Because the validation engine (`backend/engine/validation.py`) and API routes (`backend/api/main.py`) read from `operaciones.arbol_id` and insert operations referencing it, they must be updated to use `id_arbol`.
4.  **Seeding Backwards Compatibility**: The existing Excel sample files (`arboles_sample.xlsx`, etc.) contain flat rows. To prevent seeding errors and retain compatibility with the current data files, the seed script must dynamically resolve RUC names, check/create parent references (`titulares`, `titulos_habilitantes`, `planes_aprovechamiento`), and then insert censo records.

## 3. Caveats
*   The actual DNI/RUC identifiers for testing are simulated. We assume standard 11-digit Peruvian corporate RUCs (starting with `20`) will be generated deterministically from company names if not explicitly provided.
*   We assume that existing indexes like `idx_operaciones_troza_unica` and `idx_operaciones_lote_unica` should remain structurally unchanged, only adapting column names from `arbol_id` to `id_arbol`.

## 4. Conclusion
Milestone M1 (Database Refactoring) is highly feasible. A normalized, hierarchical model with robust DDL commands can be implemented without breaking existing seed data or concurrency tests, provided that:
*   The `DDL_STATEMENTS` in `backend/database.py` are updated with the defined schema.
*   The seeding method `seed_from_excel()` dynamically maps names to RUCs and populates intermediate tables.
*   Search filter columns are aligned in the validation engine and API logic.

## 5. Verification Method
To verify the implementation of Milestone M1:
1.  **Check database creation**: Run `python backend/database.py` and inspect the tables using a SQLite client to ensure the hierarchical tables (`titulares`, `titulos_habilitantes`, `planes_aprovechamiento`, `censo_forestal`) are successfully created and seeded.
2.  **Run tests**: Execute `pytest backend/test_concurrency.py` to ensure no database locking or syntax errors occur.
