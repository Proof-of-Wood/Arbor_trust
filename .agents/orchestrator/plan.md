# Execution Plan: ArborTrust Forest Management Refactoring

## Objectives
- Refactor backend SQLite schema and endpoints to reflect hierarchical authority (OSINFOR/SERFOR).
- Enforce simulated PIDE headers and role-based validations on operations and plan uploads.
- Build UI supporting role switching and conditional views for Regente, Titular, OSINFOR.
- Enforce parallel E2E Testing Track and Implementation Track.
- Ensure 100% test success of both integration and E2E tests, clean Forensic Auditor audit.

## Steps
1. **Initialize Tracks**:
   - Spawn E2E Testing Track Orchestrator (`sub_orch_e2e`) to design E2E test infrastructure and generate Tier 1-4 tests, writing `TEST_INFRA.md` and eventually `TEST_READY.md`.
   - Spawn Implementation Track Orchestrator (`sub_orch_impl`) to coordinate milestones M1 to M5.
2. **Track E2E Test Suite Creation**:
   - Monitor `sub_orch_e2e` progress. Update plans and ensure it outputs `TEST_READY.md`.
3. **Track Implementation Progress**:
   - Monitor `sub_orch_impl` progress from M1 (Database DDL refactoring) to M5 (QA Integration Tests).
4. **Integration Phase (M6)**:
   - Once implementation is done and E2E tests are ready, direct the implementation track to verify against E2E tests and perform coverage hardening (Tier 5).
5. **Final Review & Audit**:
   - Spawn Forensic Auditor to verify integrity and correctness.
   - Deliver final report and signal victory.
