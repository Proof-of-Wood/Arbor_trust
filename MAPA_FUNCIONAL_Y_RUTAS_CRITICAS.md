# 1. Arquitectura de Actores y Permisos en la UI

El sistema ArborTrust define un conjunto de perfiles de usuario o actores que interactúan con la plataforma, tanto para registrar eventos físicos de la madera como para realizar auditorías regulatorias bajo los Lineamientos de OSINFOR.

### A. Perfiles y Actores Soportados en la Base de Datos
La base de datos SQLite en su tabla `logs_auditoria` restringe los tipos de actores mediante un constraint `CHECK(tipo_actor IN (...))`:
*   `Titular`: Titular del Título Habilitante (Productor Forestal).
*   `Regente`: Regente Forestal que avala los censos forestales.
*   `ARFFS`: Autoridad Regional Forestal y de Fauna Silvestre.
*   `SERFOR`: Servicio Nacional Forestal y de Fauna Silvestre.
*   `OSINFOR`: Organismo de Supervisión de los Recursos Forestales y de Fauna Silvestre.
*   `Transportista`: Conductor / CTP encargado del traslado.
*   `Operador_CTP`: Operador del Centro de Transformación Primaria (Aserradero).
*   `Sistema`: Procesos automáticos internos del backend.
*   `Comprador`: Cliente final nacional o internacional.

---

### B. Matriz de Permisos, Vistas y Acciones en el Frontend (React)

El frontend de React expone tres vistas principales organizadas por roles en la barra de navegación:

| Vista UI | Componente React | Actores Principales | Acciones Disponibles | Ingesta de Archivos / Formularios |
| :--- | :--- | :--- | :--- | :--- |
| **Registro Operativo** | `Formulario.jsx` | `Titular`, `Transportista`, `Operador_CTP` | Registrar transacciones individuales o cargas masivas de datos. | **Formulario Individual:** Registro manual de Tala, Trozado, Despacho, y Transformación.<br>**Carga Masiva:** Ingesta de archivos `.xlsx` de Censo, Balances, Lotes y Operaciones. |
| **Pasaporte Digital** | `Timeline.jsx` | `OSINFOR`, `Comprador`, `ARFFS`, `SERFOR` | Consultar la línea de tiempo completa de un lote y validar su cadena de custodia criptográfica. | **Formulario de Consulta:** Búsqueda por ID de Lote.<br>**QR-Route:** Acceso automático mediante lectura de código QR. |
| **Control en Ruta** | `Dashboard.jsx` | `OSINFOR`, `ARFFS` (Fiscalizadores) | Monitoreo en tiempo real de fallas críticas (Semáforo Rojo) y advertencias (Semáforo Amarillo). | **Alertas en Ruta:** Visualización agregada de fallas por lote, regla violada, fecha y responsable con refresco automático de 15s. |

---

# 2. Catálogo Técnico de Documentos de Ingesta (Excel .xlsx)

El sistema procesa cuatro plantillas de hoja de cálculo en formato Excel (.xlsx). A continuación se describe la estructura exacta, campos esperados, bases de datos afectadas y validaciones a nivel de base de datos.

### A. Censo Forestal (`censo`)
*   **Etapa Transaccional:** Planificación (Punto 1).
*   **Tabla Afectada:** `arboles`.
*   **Campos y Tipos en BD:**
    *   `arbol_id` (TEXT, PRIMARY KEY, NOT NULL)
    *   `titulo_habilitante_id` (TEXT, NOT NULL)
    *   `titular` (TEXT, NOT NULL)
    *   `parcela_corta` (TEXT, NOT NULL)
    *   `especie` (TEXT, NOT NULL)
    *   `volumen_censado` (REAL, NOT NULL)
    *   `estado` (TEXT, DEFAULT 'Autorizado')
    *   `condicion` (TEXT, DEFAULT 'Aprovechable')
*   **Validaciones Físicas y de Negocio (Backend):**
    *   Volumen no puede ser negativo (`volumen_censado >= 0`). Si `volumen_censado < 0`, se lanza `ValueError`.
    *   La especie debe estar incluida en las especies permitidas (`Shihuahuaco`, `Cumala`, `Cedro`, `Tornillo`, `Lupuna`, `Caoba`). Si no, se lanza `ValueError`.
    *   Unicidad de árbol: Evita duplicados mediante el índice único `idx_arboles_unicidad` y la sentencia `INSERT OR IGNORE`.

### B. Balances de Extracción (`balances`)
*   **Etapa Transaccional:** Planificación (Punto 1).
*   **Tabla Afectada:** `balances_extraccion`.
*   **Campos y Tipos en BD:**
    *   `balance_id` (TEXT, PRIMARY KEY, NOT NULL)
    *   `titulo_habilitante_id` (TEXT, NOT NULL)
    *   `parcela_corta` (TEXT, NOT NULL)
    *   `especie` (TEXT, NOT NULL)
    *   `volumen_autorizado` (REAL, NOT NULL)
    *   `volumen_movilizado` (REAL, NOT NULL, DEFAULT 0)
    *   `saldo_disponible` (REAL, NOT NULL)
    *   `estado_saldo` (TEXT, DEFAULT 'Positivo')
*   **Validaciones Físicas y de Negocio (Backend):**
    *   Los volúmenes de balance no pueden ser negativos (`volumen_autorizado >= 0` y `volumen_movilizado >= 0`). Si no, se lanza `ValueError`.
    *   La especie debe pertenecer al catálogo permitido. Si no, lanza `ValueError`.
    *   Idempotencia por fila mediante `INSERT OR IGNORE`.

### C. Lotes y Guías (`lotes`)
*   **Etapa Transaccional:** Transporte (Punto 3).
*   **Tabla Afectada:** `lotes`.
*   **Campos y Tipos en BD:**
    *   `lote_id` (TEXT, PRIMARY KEY, NOT NULL)
    *   `numero_gtf` (TEXT, NOT NULL)
    *   `titulo_habilitante_id` (TEXT, NOT NULL)
    *   `titular` (TEXT, NOT NULL)
    *   `parcela_corta` (TEXT, NOT NULL)
    *   `especie` (TEXT, NOT NULL)
    *   `volumen_total` (REAL, NOT NULL)
    *   `punto_origen` (TEXT, DEFAULT 'Bosque')
    *   `punto_destino` (TEXT, DEFAULT 'CTP')
    *   `estado_validacion` (TEXT, DEFAULT 'Pendiente')
    *   `color_semaforo` (TEXT, DEFAULT 'Amarillo')
    *   `mensaje_validacion` (TEXT)
*   **Validaciones Físicas y de Negocio (Backend):**
    *   Volumen total del lote no puede ser negativo.
    *   Especie del lote debe pertenecer al catálogo oficial.
    *   Idempotencia por fila mediante `INSERT OR IGNORE`.

### D. Libro de Operaciones (`operaciones`)
*   **Etapa Transaccional:** Aprovechamiento, Transporte y Transformación (Puntos 2, 3 y 4).
*   **Tabla Afectada:** `operaciones` y `balances_extraccion` (descuento acumulativo).
*   **Campos y Tipos en BD:**
    *   `operacion_id` (TEXT, PRIMARY KEY, NOT NULL)
    *   `tipo_operacion` (TEXT, NOT NULL, CHECK in 'Tala', 'Trozado', 'Despacho', 'Transformacion')
    *   `punto_cadena` (INTEGER, NOT NULL, CHECK in 2, 3, 4)
    *   `arbol_id` (TEXT, REFERENCES `arboles`)
    *   `troza_id` (TEXT)
    *   `lote_id` (TEXT, REFERENCES `lotes`)
    *   `parcela_corta` (TEXT, NOT NULL)
    *   `especie` (TEXT, NOT NULL)
    *   `volumen` (REAL, NOT NULL)
    *   `numero_gtf` (TEXT)
    *   `actor_id` (TEXT, NOT NULL)
    *   `fecha` (TEXT, NOT NULL)
    *   `observacion` (TEXT)
*   **Validaciones Físicas y de Negocio (Backend):**
    *   Volumen de operación >= 0; Especie permitida; Tipo de operación válido.
    *   **Unicidad lógica en Base de Datos (SQLite Constraints):**
        *   `idx_operaciones_tala_unica` ON `operaciones(arbol_id)` WHERE `tipo_operacion = 'Tala'` (Un árbol solo se tala una vez).
        *   `idx_operaciones_troza_unica` ON `operaciones(troza_id, tipo_operacion)` (Una troza no se duplica en una operación del mismo tipo).
        *   `idx_operaciones_lote_unica` ON `operaciones(lote_id, tipo_operacion)` WHERE `arbol_id IS NULL AND troza_id IS NULL` (Evita duplicidad de lotes).
    *   **Descuento de Saldos Atómico:** Cada operación descuenta automáticamente el volumen del balance:
        ```sql
        UPDATE balances_extraccion
        SET volumen_movilizado = volumen_movilizado + ?,
            saldo_disponible = saldo_disponible - ?,
            estado_saldo = CASE WHEN (saldo_disponible - ?) < 0 THEN 'Negativo' ELSE 'Positivo' END
        WHERE titulo_habilitante_id = ? AND parcela_corta = ? AND especie = ?
        ```

---

# 3. Flujo E2E de Trazabilidad Exitoso (Happy Paths)

El flujo de trazabilidad exitoso mapea el ciclo de vida del recurso maderable, pasando por cuatro fases principales, conectando identificadores y volúmenes a través del modelo relacional y la cadena criptográfica.

```
[Fase 1: Planificación]      [Fase 2: Aprovechamiento]       [Fase 3: Transporte]       [Fase 4: Transformación]
   Carga del Censo             Tala: OP-001 (Vol: 12.5)       Lote: LOT-001 (Vol: 12.5)    Sawmill Input: OP-004
      (Arbol: 3403)                      |                               |                   (Lote: LOT-001)
         |                     Trozado: OP-002 / OP-003          GTF: 017-0001271                     |
         v                               |                               v                            v
   Carga de Balances           Trozas: 3403-T1 / 3403-T2        Semáforo: Verde (OK)      Sawmill Output: OP-005
(Shihuahuaco, 50.0m3)          (Vol: 6.25m3 c/u)                Pasaporte Activo (QR)       (Wood aserrada, 10m3)
```

### Flujo de Datos y Transiciones de Tablas:

1.  **Fase 1: Planificación (Censo y Balances)**
    *   Un árbol con `arbol_id = '3403'` es registrado en `arboles` con un volumen estimado de `12.5 m³` para la especie `Shihuahuaco` en la parcela `PC-01`.
    *   Se crea un registro en `balances_extraccion` con `volumen_autorizado = 50.0 m³`, `volumen_movilizado = 0.0 m³`, `saldo_disponible = 50.0 m³`, `estado_saldo = 'Positivo'`.

2.  **Fase 2: Aprovechamiento (Tala y Trozado)**
    *   **Tala:** El productor forestal registra una operación de tipo `Tala` en la tabla `operaciones` (`operacion_id = 'OP-001'`) referenciando al árbol `'3403'` con `volumen = 12.5 m³`.
        *   *Efecto en Balances:* `volumen_movilizado` en `balances_extraccion` se actualiza a `12.5 m³` y `saldo_disponible` baja a `37.5 m³`.
        *   *Efecto en Criptografía:* Se genera un bloque génesis en `logs_auditoria` con `entidad_id = '3403'`, `hash_anterior = NULL` y `hash_actual = sha256(Genesis|Titular|Timestamp|Payload)`.
    *   **Trozado:** El productor troza el árbol en dos secciones y registra dos operaciones en `operaciones` (`'OP-002'` y `'OP-003'`) con `troza_id = '3403-T1'` y `'3403-T2'`, cada una con `volumen = 6.25 m³`.
        *   *Efecto en Criptografía:* Se registran dos eventos encadenados en `logs_auditoria` apuntando al historial del árbol y las trozas.

3.  **Fase 3: Transporte (Lote y Despacho)**
    *   Se registra un lote comercial en la tabla `lotes` (`lote_id = 'LOT-001'`) con `numero_gtf = '017-0001271'`, `volumen_total = 12.5 m³`, `especie = 'Shihuahuaco'`, `parcela_corta = 'PC-01'`.
    *   Se ingresa la operación de tipo `Despacho` en la tabla `operaciones` (`'OP-004'`) asociando `lote_id = 'LOT-001'` y `numero_gtf = '017-0001271'` con `volumen = 12.5 m³`.
    *   **Activación del Motor de Validación:** Al registrar el lote, se dispara `validar_lote('LOT-001')`.
        *   Verifica que la GTF exista en `lotes`.
        *   Verifica que existan operaciones de tala y trozado vinculadas a esa GTF/Lote en `operaciones` y recupera el `arbol_id = '3403'`.
        *   Verifica el saldo en `balances_extraccion` (`saldo_disponible = 37.5 >= volumen_lote`).
        *   Valida la cronología: La fecha de despacho es posterior a la de tala.
        *   *Resultado:* Se inserta un registro en `validaciones` con resultado `Aprobado`, severidad `Baja`, color `Verde`.
        *   Se actualiza `lotes` con `color_semaforo = 'Verde'`, `estado_validacion = 'Validado'` y `mensaje_validacion = 'Lote válido con trazabilidad consistente.'`.
        *   *Efecto en Criptografía:* Se añade el log de auditoría para `'LOT-001'` encadenando los hashes.

4.  **Fase 4: Transformación (CTP)**
    *   El lote ingresa al aserradero y el Operador CTP registra una operación de tipo `Transformacion` (`'OP-005'`) con `lote_id = 'LOT-001'`, `tipo_producto = 'madera_aserrada'`, `volumen = 10.0 m³` (reflejando la merma física de procesamiento de 12.5 a 10.0 m³).
    *   *Efecto en Criptografía:* Se genera un registro de auditoría en `logs_auditoria` con `tipo_actor = 'Operador_CTP'`, `accion = 'INGRESO_CTP'`, `entidad_id = 'LOT-001'`, cuyo `hash_anterior` referencia al hash del Despacho. Esto cierra el ciclo completo de custodia.

---

# 4. Análisis de Resiliencia ante Fraudes y Errores (Matriz de Unhappy Paths)

La arquitectura técnica de ArborTrust mitiga intentos de fraude documental, inconsistencias de volumen y errores de concurrencia mediante validaciones a nivel de base de datos SQLite y controles en el backend.

| Escenario de Falla (Unhappy Path) | Mecanismo de Control Técnico (FastAPI / SQLite) | Reacción del Sistema (Semáforo y Rollbacks) | Impacto y Evidencia en Base de Datos |
| :--- | :--- | :--- | :--- |
| **Caso A:** Intento de modificar/añadir censo en parcelas con registros existentes. | Índice único físico `idx_arboles_unicidad` en la tabla `arboles`. | **Silencioso e Idempotente:** El backend utiliza `INSERT OR IGNORE`. | Las filas duplicadas del archivo XLSX se ignoran. No sobrescriben datos existentes ni alteran el volumen censo base. |
| **Caso B:** Mismatch de volumen por sobreextracción (saldo negativo o volumen real > censo). | Validación en `validar_lote` comparando `volumen_total` del lote contra el `saldo_disponible` de la parcela. | **Advertencia (Amarillo):** Exceso <= 5% del saldo.<br>**Falla Crítica (Rojo):** Exceso > 5% del saldo o saldo ya es negativo. | Se registra la fila en `validaciones` con color `Amarillo` o `Rojo`. El lote en `lotes` se actualiza a `Rojo`/`Amarillo` y bloquea la emisión conforme del Pasaporte. |
| **Caso C:** Lavado de madera (Blanqueo con especies no autorizadas). | Restricción en el parseador de archivos en `database.py` contra el set `ALLOWED_SPECIES`. | **Rechazo Inmediato:** Lanza `ValueError` en el hilo de procesamiento. | **Rollback Transaccional:** Se detiene el proceso y la transacción completa de carga se cancela. Ningún registro del archivo XLSX ingresa a la base de datos. |
| **Caso D:** Condiciones de carrera por concurrencia en SQLite. | Activación del modo **Write-Ahead Logging (WAL)** en `sqlite3` y configuración de timeout de bloqueo. | **Espera Activa / Concurrencia:** `PRAGMA busy_timeout = 30000;` permite a hilos concurrentes esperar hasta 30s a que se libere el lock de escritura. | Los procesos simultáneos se ejecutan secuencialmente sin lanzar errores de "database is locked". Evitado en tests concurrentes. |
| **Caso E:** Ingesta de archivos con estructura corrupta o headers inválidos. | **Doble validación:** Client-side header sniffing (SheetJS) y server-side try/except en el worker de background. | **Bloqueo Preventivo:** El frontend no permite subir si falta la PK.<br>**Fallo y Rollback:** El backend hace rollback en caso de `KeyError`. | El job se registra como `FALLIDO` en `registro_cargas`. El archivo temporal se elimina. Se expone el mensaje traducido al usuario. |

---

# 5. Evaluación del Semáforo de Riesgo y Alertas de OSINFOR

El Motor de Validación en `backend/engine/validation.py` es una pieza clave encargada de calcular de manera determinista el semáforo de riesgo de cada lote según las normativas del D.L. N° 1085.

### Reglas del Motor de Validación y Severidad:

1.  **Regla `gtf_asociada` (Existencia de Guía de Transporte)**
    *   *Propósito:* Asegura que el lote comercial cuente con una GTF oficial asociada.
    *   *Falla (Rojo - Severidad Alta):* Si `numero_gtf` está vacío o es nulo. Mensaje: `"El lote no tiene una GTF asociada."`
    *   *Paso (Verde - Severidad Baja):* Si cuenta con una GTF registrada. Mensaje: `"GTF [Número] válida."`

2.  **Regla `existencia_arbol` (Trazabilidad hacia el origen)**
    *   *Propósito:* Verifica que el lote provenga de un árbol censado y talado legalmente.
    *   *Falla (Rojo - Severidad Alta):*
        *   Si no se encuentran operaciones de tala/trozado en `operaciones` asociadas al lote o GTF. Mensaje: `"No se encontraron operaciones de tala/trozado que originen este lote."`
        *   Si las operaciones existen pero no se especifica un `arbol_id` válido. Mensaje: `"Las operaciones no tienen un ID de árbol asociado."`
    *   *Paso (Verde - Severidad Baja):* Si se verifica la cadena de operaciones y se listan los IDs de los árboles origen. Mensaje: `"Árboles origen verificados: [Lista]."`

3.  **Regla `volumen_disponible` (Validación de Cupo de Extracción)**
    *   *Propósito:* Garantiza que no se extraiga más volumen de madera que el autorizado.
    *   *Falla (Rojo - Severidad Alta):*
        *   No existe registro en `balances_extraccion` para el título habilitante, parcela y especie. Mensaje: `"No existe balance de extracción para esta parcela y especie."`
        *   El balance previo es negativo. Mensaje: `"El saldo disponible en la parcela es negativo previo a esta operación."`
        *   El volumen del lote excede el saldo por más del 5%. Mensaje: `"Volumen sobreexplotado. Excede el saldo por X m3 (>5%)."`
    *   *Falla (Amarillo - Severidad Media):* El volumen excede el saldo disponible por un margen de tolerancia menor o igual al 5%. Mensaje: `"El volumen excede el saldo por una diferencia menor al 5% (X m3)."`
    *   *Paso (Verde - Severidad Baja):* Volumen dentro de los parámetros del saldo disponible. Mensaje: `"El volumen extraído es menor o igual al saldo disponible."`

4.  **Regla `cronologia_operaciones` (Coherencia en la Línea de Tiempo)**
    *   *Propósito:* Evita anomalías cronológicas temporales que sugieran falsificación de datos.
    *   *Falla (Amarillo - Severidad Media):* Si la fecha del despacho es anterior a la fecha registrada de la tala del árbol. Mensaje: `"Inconsistencia de fechas: Despacho registrado antes que la Tala."`

### Lógica de Consolidación de Color y Persistencia:
*   El estado inicial del lote se define como `Verde`.
*   Si una o más reglas resultan en `Amarillo`, el estado consolidado pasa a `Amarillo`.
*   Si una o más reglas resultan en `Rojo`, el estado consolidado pasa a `Rojo`, prevaleciendo sobre el amarillo.
*   **Persistencia:** El resultado de cada regla se escribe en la tabla `validaciones` y el color consolidado junto con el listado de alertas (separado por `" | "`) se persiste en la tabla `lotes` bajo los campos `color_semaforo`, `mensaje_validacion` y `estado_validacion = 'Validado'`.
