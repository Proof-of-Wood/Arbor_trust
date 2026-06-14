# Scope: E2E Testing Validation

## Architecture
The E2E testing track is requirement-driven and opaque-box. It executes tests against the REST API boundaries. It targets:
- FastAPI endpoints for plan uploads, operations registration, timeline retrieval, and supervision.
- Simulated PIDE headers for role authentication and authorization.
- Verification of hierarchical DB constraints and versioning logic.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Test Suite Design & Infra | Design the test case matrix (60+ cases across 4 tiers) and document in `TEST_INFRA.md`. Set up the E2E test runner structure. | None | DONE |
| M2 | Test Runner & Mock Setup | Establish a test runner and a helper mock/simulation backend to verify tests run and pass if target backend features are not yet ready. | M1 | DONE |
| M3 | Tier 1 & 2 Test Case Implementation | Implement at least 25 Tier 1 cases (Feature Coverage) and 25 Tier 2 cases (Boundary/Corner). | M2 | DONE |
| M4 | Tier 3 & 4 Test Case Implementation | Implement at least 5 Tier 3 cases (Cross-Feature) and 5 Tier 4 cases (Real-World Workloads). | M3 | DONE |
| M5 | Test Run & Verification | Execute the E2E test suite against the target/mock backend. Ensure 100% pass rate. | M4 | IN_PROGRESS |
| M6 | Publish TEST_READY.md | Write `TEST_READY.md` containing the E2E execution report. | M5 | PLANNED |

## Interface Contracts
- Tests must interact ONLY via the HTTP REST API (endpoints like `POST /api/v1/planes/subir`, `POST /api/v1/operaciones/registrar`, etc.).
- Test inputs: Excel spreadsheets generated dynamically or loaded from mock data files.
- Test headers: `X-PIDE-Rol`, `X-PIDE-RUC`, `X-PIDE-DNI`, etc.
