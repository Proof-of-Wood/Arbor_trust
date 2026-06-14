# Handoff Report — Milestone M1: Database DDL Refactoring

This report provides the results of our investigation, logic chain, caveats, and recommendations for refactoring `backend/database.py` to support the hierarchical schema model of the Peruvian forest sector.

## 1. Observation
- **Original Table Definitions**: In `backend/database.py`, lines 20-31 define the flat `arboles` table, and lines 50-68 define `operaciones` referencing it:
  * Line 20: `CREATE TABLE IF NOT EXISTS arboles (`
  * Line 54: `arbol_id        TEXT REFERENCES arboles(arbol_id),`
- **Spreadsheet Parsing Logic**: In `backend/database.py`, lines 230-261 parse tree records and load them directly into the flat `arboles` table.
- **Seeding Logic**: In `backend/database.py`, lines 548-562 seed sample data using:
  * Line 555: `INSERT OR IGNORE INTO arboles`
- **Validation Engine References**: In `backend/engine/validation.py`, line 137 queries operations:
  * Line 137: `arboles_origen = ops["arbol_id"].dropna().unique()`
- **Test Setup Constraints**: In `backend/test_concurrency.py`, lines 49-78 pre-insert dummy trees directly:
  * Line 50: `INSERT OR IGNORE INTO arboles (arbol_id, titulo_habilitante_id, titular, parcela_corta, especie, volumen_censado)`

## 2. Logic Chain
1. To support the hierarchical model (Titulares ➔ Títulos Habilitantes ➔ Planes de Aprovechamiento ➔ Censo Forestal ➔ Operaciones), we must replace the flat `arboles` table with `censo_forestal` and introduce the intermediate tables `titulares`, `titulos_habilitantes`, and `planes_aprovechamiento`.
2. Because `operaciones` and `balances_extraccion` reference `arboles` and `titulo_habilitante_id` directly, we must update foreign key constraints to point to the new hierarchical structure (`censo_forestal` and `titulos_habilitantes`).
3. Since existing test files (`test_concurrency.py`) and seed files (`arboles_sample.xlsx`) do not contain parent RUC/DNI or Plan mappings, our new `seed_from_excel()` and `preinsert_test_trees()` methods must dynamically extract/deduplicate and register owners, titles, and plans dynamically using a deterministic RUC mapping function.
4. To prevent API endpoints (`obtener_timeline` in `main.py`) from breaking when columns are renamed to `id_arbol` and `id_operacion`, the SQL queries should alias columns (`id_arbol AS arbol_id`) to maintain response compatibility.

## 3. Caveats
- **Read-Only Mode**: We did not implement or execute the database migrations since we are in read-only investigation mode.
- **PIDE Simulated Roles**: Integration of `X-PIDE-*` header authentication has not been verified/implemented in this milestone (slated for Milestone M3). We assumed default values for RUC mappings where headers are absent.

## 4. Conclusion
We recommend refactoring `backend/database.py` utilizing the schemas and parsing updates detailed in `analysis.md` and pre-written in `proposed_database.py`. The transitions preserve transactional WAL safety and enable seamless database migration.

## 5. Verification Method
1. **Apply Proposed Code**: Replace `backend/database.py` with `proposed_database.py` (making sure to adjust path constants if needed).
2. **Update Test Harness**: Apply the changes described in Section 5 of `analysis.md` to `backend/test_concurrency.py` (specifically updating `preinsert_test_trees()`).
3. **Execute Integration Tests**: Run `pytest backend/test_concurrency.py` to confirm the database correctly initializes, seeds, and executes all concurrency scenarios under the new schema.
