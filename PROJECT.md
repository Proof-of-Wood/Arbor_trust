# Project: ArborTrust Forest Management Refactoring

## Architecture
ArborTrust is composed of:
- **Backend (FastAPI + SQLite)**: REST API (`backend/api/main.py`) managing operations, plan versions, and validation rules. Database schema in `backend/database.py` stores actors, titles, plans, census records, operations, and audit logs.
- **Frontend (React + Vite)**: User dashboard and forms (`frontend/src/pages/...`) with role-based routing and conditional UI elements.

## Code Layout
- `backend/api/main.py` - FastAPI App endpoints
- `backend/database.py` - Database connections, DDL schema, seed methods, background processing
- `backend/engine/validation.py` - Risk semaphore and operational volume limits rules engine
- `backend/engine/hashing.py` - Cryptographic chain of custody integrity log
- `backend/test_concurrency.py` - Integration and concurrency tests
- `frontend/src/App.jsx` - Main React router
- `frontend/src/pages/Dashboard.jsx` - Role selection and titles dashboard
- `frontend/src/pages/Formulario.jsx` - Plans uploading panel and manual operations entry
- `frontend/src/pages/Timeline.jsx` - Census trees status timeline

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Database Refactoring | Refactor `backend/database.py` for hierarchical relations: Titulares, Titulos_Habilitantes, Planes_Aprovechamiento, Censo_Forestal. Update schema initialization and seed methods. | None | PLANNED |
| M2 | Plan Versioning & Regente Flow | Implement automatic plan versioning in background task. Expose regente spreadsheet upload endpoint `POST /api/v1/planes/subir`. | M1 | PLANNED |
| M3 | PIDE Validation & Role Logic | Implement simulated PIDE headers extraction, Titular spreadsheet ownership validation, and real-time manual volume validation. | M2 | PLANNED |
| M4 | Role-Redirecting UI | Refactor React frontend: role profile cards in Dashboard, upload panel and manual operations form in Formulario, and filtered timeline. | M3 | PLANNED |
| M5 | QA Integration Tests | Inject 3 new integration tests in `backend/test_concurrency.py` and run tests. | M4 | PLANNED |
| M6 | E2E Testing Validation | Verify implementation passes 100% of E2E tests built on the parallel track. | M5, E2E_READY | PLANNED |

## Interface Contracts
### PIDE Request Headers Simulation
- `X-PIDE-Rol`: Actor role ('Regente', 'Titular', 'OSINFOR', 'Operador_CTP')
- `X-PIDE-RUC`: RUC for Titular
- `X-PIDE-DNI`: DNI for Regente
- `X-PIDE-Placa`: Vehicle license plate for Transportista
- `X-PIDE-Serfor`: Serfor official credentials

### Plan Upload Spreadsheet Format (Regente Flow)
- Columns: `['titulo_habilitante_id', 'plan_id', 'version', 'fecha_aprobacion', 'arbol_id', 'especie', 'volumen_censado']`
- Endpoint: `POST /api/v1/planes/subir`
