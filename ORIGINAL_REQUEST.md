# Original User Request

## Initial Request — 2026-06-14T19:24:04Z

Refactor the 'ArborTrust' platform to be a complete forest management and traceability system reflecting OSINFOR/SERFOR's hierarchical chain of authority. This includes updating the SQLite database schema, enforcing role-based API restrictions (PIDE headers), implementing versioned forest management plans, updating the React UI, and verifying the changes with integration tests.

Working directory: c:\Users\Acer\Desktop\Estudio\Proyectos\ArborTrust\Arbor_trust
Integrity mode: development

## Requirements

### R1. Hierarchical Database Model & Versioning
- Refactor `backend/database.py` schema to support the hierarchical relationship of the Peruvian forest sector:
  * **Titulares**: Columns for RUC/DNI (PK), Name, Address, etc.
  * **Titulos_Habilitantes**: Columns for ID_Título (PK), ID_Titular (FK to Titulares), Name_Concesion/Predio, and Ubicación_Geográfica.
  * **Planes_Aprovechamiento**: Columns for ID_Plan (PK), ID_Título (FK to Titulos_Habilitantes), Versión (integer), Fecha_Aprobación, Estado (Aprobado/Actualizado/Vencido), and Documento_PDF_Hash.
  * **Censo_Forestal**: Columns for ID_Arbol (PK), ID_Plan (FK to Planes_Aprovechamiento), ID_Especie, and Volumen_Autorizado.
  * **Operaciones**: Columns for ID_Operación, ID_Arbol (FK to Censo_Forestal), ID_Titular (FK to Titulares), and existing operation fields (type, volume, species, etc.).
- Implement automatic plan versioning in `procesar_archivo_background` when loading a new Plan of Aprovechamiento: instead of deleting old plans, increment the `Versión` counter and lock previous plans if they are marked as inactive/updated.

### R2. Role-Based Business Logic & Validation (PIDE Simulation)
- Retrieve simulated credentials from HTTP headers (`X-PIDE-Rol`, `X-PIDE-RUC`, `X-PIDE-Serfor`, `X-PIDE-DNI`, `X-PIDE-Placa`) to identify the user.
- **Regente Flow**: Expose `POST /api/v1/planes/subir` for loading plan spreadsheets (.xlsx) containing the plan version metadata and censo records in a single sheet (with columns: `['titulo_habilitante_id', 'plan_id', 'version', 'fecha_aprobacion', 'arbol_id', 'especie', 'volumen_censado']`). This updates the `Planes_Aprovechamiento` and `Censo_Forestal` tables.
- **Titular Flow**: Ingest operations only if the spreadsheet's `titulo_habilitante_id` belongs to the RUC/DNI of the logged-in Titular. 
- For individual/manual operation registration, validate in real time that the requested volume does not exceed the remaining balance of the active `Plan_Aprovechamiento` for that specific species and parcel.

### R3. Role-Redirecting React UI
- **Dashboard.jsx**: After selecting a role profile, display associated Títulos Habilitantes as interactive cards. Clicking on a card opens its specific timeline.
- **Formulario.jsx**: 
  * Add a "Planes de Aprovechamiento" upload panel visible only to the `Regente` role.
  * Enable manual operation entries (Tala, Trozado, Despacho, Transformación) for `Titular`/`Operador_CTP` with real-time validation against the selected title's available balance.
- **Timeline / Pasaporte**: Allow filtering by Título Habilitante, showing a breakdown of which census trees have already been logged (Tala) and which remain standing.

### R4. QA Integration Tests
- Inject 3 new test cases into `backend/test_concurrency.py`:
  1. **Plan Integrity Test**: Verify that uploading operations or census records without an approved plan returns a validation error.
  2. **Plan Versioning Test**: Upload two versions of a plan of aprovechamieto with different volumes and verify that subsequent operations are validated against the latest active version.
  3. **Actor-Title Ownership Test**: Attempt to upload operations for a Title using a Titular RUC that does not own the Title, verifying that the backend rejects it with 403 Forbidden.

## Acceptance Criteria

### Verification Mechanisms
- **Automated Tests**: Running `pytest backend/test_concurrency.py` executes successfully with all concurrency and integration tests (including the 3 new QA tests) passing 100%.
- **Manual UI Check**: The frontend React app starts without compile errors and supports switching roles (Regente, Titular, OSINFOR) with corresponding feature access.
