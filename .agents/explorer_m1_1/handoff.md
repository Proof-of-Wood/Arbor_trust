# Handoff Report: Milestone M1 DDL Refactoring

## 1. Observation
- **Legacy Database Table Definitions**:
  * In `backend/database.py` lines 20–31:
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
  * In `backend/database.py` lines 50–68:
    ```python
    CREATE TABLE IF NOT EXISTS operaciones (
        operacion_id    TEXT PRIMARY KEY,
        tipo_operacion  TEXT NOT NULL CHECK(tipo_operacion IN ('Tala','Trozado','Despacho','Transformacion')),
        punto_cadena    INTEGER NOT NULL CHECK(punto_cadena IN (2,3,4)),
        arbol_id        TEXT REFERENCES arboles(arbol_id),
        ...
        actor_id        TEXT NOT NULL,
        ...
    )
    ```
- **Seeding Method**:
  * In `backend/database.py` lines 540–623, `seed_from_excel()` directly inserts flat rows from sample Excel sheets into `arboles` and `operaciones`.
- **Validation Engine**:
  * In `backend/engine/validation.py` lines 137–139, the existence validation checks `ops["arbol_id"]`:
    ```python
    arboles_origen = ops["arbol_id"].dropna().unique()
    ```
- **FastAPI Endpoints**:
  * In `backend/api/main.py` lines 200–208, the endpoint inserts into `operaciones` using:
    ```python
    conn.execute("""
        INSERT INTO operaciones
        (operacion_id, tipo_operacion, punto_cadena, arbol_id, troza_id, lote_id,
         parcela_corta, especie, volumen, numero_gtf, actor_id, fecha, observacion)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, ...)
    ```
- **Test Pre-insertion Helper**:
  * In `backend/test_concurrency.py` lines 39–82, `preinsert_test_trees()` inserts directly into `arboles` using legacy fields.

---

## 2. Logic Chain
1. To support the hierarchical relationship of the Peruvian forest sector, the flat `arboles` table must be split into four distinct normalized tables: `titulares` (owners), `titulos_habilitantes` (concessions/predios), `planes_aprovechamiento` (management plans), and `censo_forestal` (census trees).
2. Consequently, `operaciones` must reference the new tables: `id_arbol` (referencing `censo_forestal(id_arbol)`) and `id_titular` (referencing `titulares(ruc_dni)`).
3. The sample seed files are flat spreadsheets. The seeding method `seed_from_excel()` must be rewritten to dynamically resolve names to RUCs, create the parent rows in `titulares`, `titulos_habilitantes`, and `planes_aprovechamiento`, and then insert records into `censo_forestal` and `operaciones`.
4. Any files querying `arboles` or old columns in `operaciones` (`arbol_id`, `operacion_id`, `actor_id`) will fail unless updated. Thus, we must modify the validation engine (`validation.py`), API endpoints (`api/main.py`), and test suite setup (`test_concurrency.py`) to align with the new schema names.

---

## 3. Caveats
- Command execution was requested but timed out because the host system requires prompt approval, which was not given. The current codebase was not tested dynamically; recommendations are based on static analysis.
- It is assumed that 11-digit Peruvian corporate RUCs starting with `20` will be generated deterministically from company names (e.g. `20123456789` for `PRODUCTOR DEMO`) in the absence of explicit data.

---

## 4. Conclusion
Milestone M1 (Database DDL refactoring) can be implemented safely by updating `DDL_STATEMENTS` in `backend/database.py`, modifying `seed_from_excel()` to handle hierarchical relationships, and applying column-rename updates to validation rules, endpoints, and test suites. Detailed changes are provided in `analysis.md`.

---

## 5. Verification Method
1. **Schema Check**:
   Once changes are applied, verify tables exist by executing:
   ```bash
   sqlite3 backend/arbortrust.db ".schema"
   ```
   Check for the presence of tables `titulares`, `titulos_habilitantes`, `planes_aprovechamiento`, and `censo_forestal`.
2. **Seeding Execution**:
   Run the database module to initialize and seed the tables:
   ```bash
   python backend/database.py
   ```
3. **Automated Testing**:
   Execute the concurrency test suite to verify all logic holds together:
   ```bash
   python -m pytest backend/test_concurrency.py
   ```
   *(Ensure the test suite executes without database locks or integrity constraint violations).*
