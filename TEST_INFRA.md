# E2E Test Infra: ArborTrust Forest Management

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|---------------------|:------:|:------:|:------:|:------:|
| 1 | Plan Ingestion | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 2 | Automatic Plan Versioning | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 3 | Actor-Title Ownership Validation | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 4 | Real-time Volume Balance Validation | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| 5 | Role-based Authorization & PIDE Headers | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Test Runner**: pytest, running against HTTP boundaries (using `httpx`).
- **Test Target**: fastapi application running on port 8099.
- **Directory Layout**:
  - `backend/test_e2e.py` - pytest suite file
  - `backend/mock_api.py` - high-fidelity simulation server with SQLite engine

## Test Cases Inventory (60 cases)

### Feature 1: Plan Ingestion
#### Tier 1: Feature Coverage
1. **F1_T1_1**: Regente uploads a valid forest management plan via spreadsheet (`POST /api/v1/planes/subir`). Verify 202 Accepted.
2. **F1_T1_2**: Verify that plan ingestion creates records in the `Planes_Aprovechamiento` table.
3. **F1_T1_3**: Verify that plan ingestion creates matching census records in the `Censo_Forestal` table.
4. **F1_T1_4**: Regente queries details of the ingested plan via API. Verify details match the spreadsheet data.
5. **F1_T1_5**: Ingest a plan containing multiple valid trees and verify all are parsed and inserted correctly.

#### Tier 2: Boundary & Corner Cases
6. **F1_T2_1**: Attempt to ingest a plan with an empty tree ID (`arbol_id`). Verify rejection or empty validation.
7. **F1_T2_2**: Attempt to ingest a plan with negative volume (`volumen_censado`). Verify 400 Bad Request.
8. **F1_T2_3**: Attempt to ingest a plan with an unsupported species (not in allowed list). Verify 400 Bad Request.
9. **F1_T2_4**: Ingest a plan referencing a non-existent `titulo_habilitante_id`. Verify rejection or fallback validation.
10. **F1_T2_5**: Attempt to upload a plan with missing spreadsheet columns. Verify 400 Bad Request.

---

### Feature 2: Automatic Plan Versioning
#### Tier 1: Feature Coverage
11. **F2_T1_1**: Upload first version of plan (version 1). Verify saved version metadata is correct.
12. **F2_T1_2**: Upload second version of the same plan (version 2). Verify version increments in database.
13. **F2_T1_3**: Ingest a new version and verify that the older version is marked as inactive/updated.
14. **F2_T1_4**: Query active plan for a Title. Verify that it returns the latest version (version 2).
15. **F2_T1_5**: Ingest a plan and verify the background processing registers a `COMPLETADO` job state in `registro_cargas`.

#### Tier 2: Boundary & Corner Cases
16. **F2_T2_1**: Attempt to upload a plan version with a version number lower than the currently active version. Verify rejection.
17. **F2_T2_2**: Upload a duplicate version number (e.g. version 2 twice). Verify idempotent handling or rejection.
18. **F2_T2_3**: Upload a plan skipping a version sequence (e.g. version 3 directly after version 1). Verify correct ingestion behavior.
19. **F2_T2_4**: Ingest plan where the approval date is set in the future. Verify system behavior.
20. **F2_T2_5**: Concurrently upload two plan versions. Verify database locks prevent version collision/corruption.

---

### Feature 3: Actor-Title Ownership Validation
#### Tier 1: Feature Coverage
21. **F3_T1_1**: Titular uploads operations spreadsheet for a Title they own. Verify success.
22. **F3_T1_2**: Titular queries operations belonging to a Title they own. Verify details returned.
23. **F3_T1_3**: Titular queries available balance for their own Title. Verify success.
24. **F3_T1_4**: Perform operations with correct credentials (`X-PIDE-Rol = 'Titular'`, `X-PIDE-RUC` match). Verify success.
25. **F3_T1_5**: OSINFOR/Admin role queries details for any Title. Verify access is allowed regardless of ownership.

#### Tier 2: Boundary & Corner Cases
26. **F3_T2_1**: Titular attempts to upload operations spreadsheet for a Title they do NOT own. Verify 403 Forbidden.
27. **F3_T2_2**: Titular attempts manual operation registration for a Title they do NOT own. Verify 403 Forbidden.
28. **F3_T2_3**: Titular attempts action without `X-PIDE-RUC` header. Verify 401 Unauthorized or 400 Bad Request.
29. **F3_T2_4**: Titular attempts action with an invalid or non-existent RUC in headers. Verify 403 Forbidden.
30. **F3_T2_5**: Titular attempts to read details of a Title they do not own. Verify 403 Forbidden.

---

### Feature 4: Real-time Volume Balance Validation
#### Tier 1: Feature Coverage
31. **F4_T1_1**: Register manual Tala operation consuming volume within available balance. Verify success and updated balance.
32. **F4_T1_2**: Register manual Trozado operation within available balance. Verify success.
33. **F4_T1_3**: Register manual Despacho operation within available balance. Verify success.
34. **F4_T1_4**: Register manual Transformación operation within available balance. Verify success.
35. **F4_T1_5**: Verify that a validation record is generated with 'Aprobado' state.

#### Tier 2: Boundary & Corner Cases
36. **F4_T2_1**: Register operation exceeding remaining balance by > 5%. Verify rejection with Rojo semáforo.
37. **F4_T2_2**: Register operation exceeding remaining balance by <= 5%. Verify warning with Amarillo semáforo.
38. **F4_T2_3**: Register operation with negative volume. Verify 400 Bad Request.
39. **F4_T2_4**: Register operation referencing a non-existent `arbol_id`. Verify rejection with Rojo semáforo.
40. **F4_T2_5**: Register transformation operation with volume_salida > 60% of volume_ingreso. Verify rejection with Rojo semáforo (rendimiento imposible).

---

### Feature 5: Role-based Authorization & PIDE Headers
#### Tier 1: Feature Coverage
41. **F5_T1_1**: Regente accesses plan upload endpoint. Verify 202 Accepted.
42. **F5_T1_2**: Titular registers manual operations. Verify 201 Created.
43. **F5_T1_3**: OSINFOR accesses ex-post supervision endpoint. Verify 200 OK.
44. **F5_T1_4**: Transportista registers dispatch operation (punto_cadena = 3). Verify success.
45. **F5_T1_5**: Operador_CTP registers transformation operation (punto_cadena = 4). Verify success.

#### Tier 2: Boundary & Corner Cases
46. **F5_T2_1**: Non-Regente attempts to upload plan spreadsheet. Verify 403 Forbidden.
47. **F5_T2_2**: Non-OSINFOR attempts to access ex-post supervision endpoint. Verify 403 Forbidden.
48. **F5_T2_3**: Access endpoints with missing `X-PIDE-Rol` header. Verify 400 Bad Request or 401 Unauthorized.
49. **F5_T2_4**: Access endpoints with invalid `X-PIDE-Rol` value. Verify 403 Forbidden.
50. **F5_T2_5**: Transportista attempts to register transformation operation. Verify 403 Forbidden.

---

### Tier 3: Cross-Feature Combinations
51. **F3_C1**: Ingest plan as Regente, then Titular uploads operations for that plan. Verify ownership and balance constraints are enforced in a chain.
52. **F3_C2**: Ingest plan version 1, execute Tala operation, ingest version 2 with expanded volume, and execute second Tala operation. Verify version tracking and cumulative balance calculations.
53. **F3_C3**: Titular uploads operations matching a non-owner Title. Verify both 403 Forbidden rejection and that no balance is updated.
54. **F3_C4**: OSINFOR ex-post penalizes a tree that was logged by a Titular. Verify that the cascade block sets the lote to Rojo semáforo and blocks subsequent operations.
55. **F3_C5**: Regente uploads a plan. Operador_CTP logs a transformation exceeding 60% rendement. Verify both balance validation and rendement check trigger a Rojo semáforo.

---

### Tier 4: Real-World Application Scenarios
56. **F4_S1**: E2E Happy Path Flow:
    1. Regente uploads plan v1.
    2. Titular Tala tree.
    3. Titular Trozado log.
    4. Transportista Despacho (Lote created).
    5. Operador_CTP Transformacion (volumen_salida <= 55%).
    Verify all validations are Verde and cryptographically chained.
57. **F4_S2**: Concession plan update and adjustment flow:
    1. Regente uploads plan v1.
    2. Titular logs some Tala.
    3. Regente uploads plan v2 (with adjusted balance).
    4. Titular logs additional Tala against v2.
    Verify balance calculations are correctly resolved against the active version.
58. **F4_S3**: Contraband/Illegal wood detection flow:
    1. Titular logs Tala.
    2. Titular attempts to dispatch a Lote with volume exceeding the Tala volume.
    3. Verify system flags it as Rojo/Amarillo and reports volume discrepancy validation error.
59. **F4_S4**: OSINFOR post-harvest inspection audit:
    1. E2E flow finishes successfully (Verde semáforo).
    2. OSINFOR inspects and finds the original tree was non-existent.
    3. OSINFOR penalizes the tree ex-post.
    4. Verify the tree state updates to 'FRAUDE_DETECTADO', and the lote and operations are flagged Rojo retroactively.
60. **F4_S5**: Multi-actor parallel execution simulation:
    1. Two different Titulares perform operations on their respective titles simultaneously.
    2. Verify no cross-talk occurs (perfect isolation).
    3. Verify and validate their respective balances.
