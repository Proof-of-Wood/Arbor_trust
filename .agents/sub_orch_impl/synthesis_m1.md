# Synthesis Report: Milestone M1 Database DDL Refactoring

## Consensus
There is 100% agreement between Explorer 1 and Explorer 3 on the target database schema structure and the seeding compatibility strategy:
- **Normalization**: Flat `arboles` table is normalized into four tables:
  1. `titulares` (ruc_dni PRIMARY KEY, nombre, direccion)
  2. `titulos_habilitantes` (id_titulo PRIMARY KEY, id_titular FOREIGN KEY, nombre_concesion, ubicacion_geografica)
  3. `planes_aprovechamiento` (id_plan PRIMARY KEY, id_titulo FOREIGN KEY, version, fecha_aprobacion, estado, documento_pdf_hash)
  4. `censo_forestal` (id_arbol PRIMARY KEY, id_plan FOREIGN KEY, id_especie, volumen_autorizado, estado, condicion)
- **Operaciones Table**: Modified columns:
  - `arbol_id` -> `id_arbol` (FOREIGN KEY referencing `censo_forestal(id_arbol)`)
  - `actor_id` -> `id_titular` (FOREIGN KEY referencing `titulares(ruc_dni)`)
- **Seeding Backward Compatibility**: Seeding must dynamically map flat `arboles_sample.xlsx` rows to the normalized structure:
  - Generate/resolve RUC for name (e.g. `"PRODUCTOR DEMO"` maps to `"20123456789"`).
  - Seed parent entities (`titulares`, `titulos_habilitantes`, `planes_aprovechamiento` version 1) before seeding `censo_forestal`.
- **Validation Rules & API Ripple Effects**: Update Pandas query filters to check `id_arbol` and check for `'FRAUDE_DETECTADO'` state in `censo_forestal`.

## Resolved Conflicts
No conflicts identified. Both reports suggest the exact same schema structure and naming convention.

## Dissenting Views
None.

## Gaps
None.
