## 2026-06-14T19:27:22Z
You are a teamwork_preview_worker.
Your working directory is: c:\Users\Acer\Desktop\Estudio\Proyectos\ArborTrust\Arbor_trust\.agents\worker_m1

Your objective is to implement Milestone M1: Database DDL refactoring (backend/database.py schema + seed/init methods).
Please read the synthesis report at:
c:\Users\Acer\Desktop\Estudio\Proyectos\ArborTrust\Arbor_trust\.agents\sub_orch_impl\synthesis_m1.md
and the detailed analysis report at:
c:\Users\Acer\Desktop\Estudio\Proyectos\ArborTrust\Arbor_trust\.agents\explorer_m1_3\analysis.md

Tasks to execute:
1. Update DDL_STATEMENTS in backend/database.py to create the normalized schema (titulares, titulos_habilitantes, planes_aprovechamiento, censo_forestal, operaciones) and index commands as described.
2. Update seed_from_excel() in backend/database.py to dynamically resolve name to RUC and seed parent structures.
3. Update database methods and queries elsewhere in backend/database.py (like penalizar_arbol_retroactivo).
4. Update validation queries in backend/engine/validation.py and API endpoints in backend/api/main.py that touch arboles or operations tables/columns to use censo_forestal and the new column names (like id_arbol, id_titular).
5. Update preinsert_test_trees() in backend/test_concurrency.py to seed the new hierarchical tables.
6. Verify your work by running the build/tests (e.g. pytest backend/test_concurrency.py) and check that they compile and run correctly.
7. Write your changes and verification logs in c:\Users\Acer\Desktop\Estudio\Proyectos\ArborTrust\Arbor_trust\.agents\worker_m1\handoff.md and notify me.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
