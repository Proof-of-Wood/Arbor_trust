# Scope: Implementation Track (M1 - M5)

## Architecture
- **Backend (FastAPI + SQLite)**: Main API endpoints located in `backend/api/main.py` which query `backend/database.py`. Rules engine in `backend/engine/validation.py` handles volume balance validations.
- **Frontend (React)**: Main entry point `frontend/src/App.jsx` and components `Dashboard.jsx`, `Formulario.jsx`, `Timeline.jsx`.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Database Refactoring | Refactor `backend/database.py` schema for: Titulares, Titulos_Habilitantes, Planes_Aprovechamiento, Censo_Forestal. Update seed logic. | None | PLANNED |
| M2 | Plan Versioning & Regente Flow | Implement background versioning task, ingest regente census spreadsheet, expose `POST /api/v1/planes/subir`. | M1 | PLANNED |
| M3 | PIDE Validation & Role Logic | Retrieve PIDE credentials from headers, validate Titular ownership of title, validate real-time manual operation volume limit. | M2 | PLANNED |
| M4 | UI Role Redirection | Refactor React UI: dashboard role cards, upload panel/forms in Formulario, timeline filters. | M3 | PLANNED |
| M5 | QA Integration Tests | Implement 3 new integration tests in `backend/test_concurrency.py` and run tests. | M4 | PLANNED |

## Interface Contracts
### PIDE Simulation Headers
- `X-PIDE-Rol`: Actor role ('Regente', 'Titular', 'OSINFOR', 'Operador_CTP')
- `X-PIDE-RUC`: RUC for Titular
- X-PIDE-DNI: DNI for Regente
- X-PIDE-Placa: Vehicle license plate for Transportista
- X-PIDE-Serfor: Serfor credentials

### Regente Plan Upload Spreadsheet
- Columns: `['titulo_habilitante_id', 'plan_id', 'version', 'fecha_aprobacion', 'arbol_id', 'especie', 'volumen_censado']`
- Endpoint: `POST /api/v1/planes/subir`
