# AUDITORÍA DE ALINEACIÓN DE USUARIO - ARBORTRUST
**Director de Producto - Secretaría de Gobierno y Transformación Digital (PCM) & Especialista en Interoperabilidad PIDE**

Este informe presenta el diagnóstico de la arquitectura de negocio y la interfaz de ArborTrust, identificando las brechas existentes entre la implementación actual y el flujo de trabajo real de la cadena de valor forestal en el Perú. Comparamos los hallazgos técnicos en [Formulario.jsx](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/frontend/src/pages/Formulario.jsx) y los componentes de backend como [main.py](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/backend/api/main.py), [database.py](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/backend/database.py) y [validation.py](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/backend/engine/validation.py) con plataformas nacionales gubernamentales como **SIGOsfc** (OSINFOR), **SISFOR** (SERFOR) y **MiBosque**.

---

# I. Diagnóstico de Identificadores Técnicos vs. Datos Reales Peruanos (DNI/RUC)

El modelo de datos actual de ArborTrust emplea identificadores puramente técnicos o artificiales que generan fricción operativa para los usuarios reales del sector forestal y bloquean la posibilidad de interoperar con bases del Estado.

### 1. El problema del actor_id técnico
> [!WARNING]
> La exposición de ID técnicos internos a los usuarios finales en campo rompe la experiencia de usuario y es propensa a errores fatales de entrada.

*   **En la UI de Registro:** En [Formulario.jsx](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/frontend/src/pages/Formulario.jsx#L56), el formulario de registro manual inicializa por defecto el campo `"ID del Actor Responsable"` con la clave estática `"ACTOR-001"`. Un concesionario o conductor forestal real no posee ni conoce un "ID de actor".
*   **En el Backend y Base de Datos:** En [database.py](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/backend/database.py#L50-L68), la tabla `operaciones` define `actor_id TEXT NOT NULL` sin verificar su formato ni realizar cruces de validez. De igual forma, en el worker asíncrono [database.py](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/backend/database.py#L382), se asigna el valor por defecto `"ACTOR-LOAD"` o `"ACTOR-SEED"`.
*   **En la Integridad:** El esquema de logs de auditoría en [database.py](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/backend/database.py#L124-L139) usa la columna `tipo_actor` con un constraint `CHECK(tipo_actor IN ('Titular','Regente','ARFFS','SERFOR','OSINFOR','Transportista','Operador_CTP','Sistema','Comprador'))`, pero el valor de `actor_id` subyacente sigue siendo una cadena arbitraria que no valida la identidad civil del firmante.

### 2. Mapeo Funcional hacia Datos de Identidad Real
Para lograr una correcta interoperabilidad nacional a través de la Plataforma PIDE, se deben sustituir los identificadores simulados por los datos tributarios, civiles y sectoriales auténticos:

| Actor Sectorial | ID actual en Código | Identificador Real Requerido | Servicio Interoperable PIDE |
| :--- | :--- | :--- | :--- |
| **Titular del Título Habilitante** | `actor_id` (Ej. `"ACTOR-001"`) | **RUC** (11 dígitos, de la empresa concesionaria) o **DNI** (8 dígitos, persona natural) + **Número de Contrato del Título Habilitante** | Consulta RUC de SUNAT & Registro de Títulos Habilitantes (SERFOR/OSINFOR) |
| **Regente Forestal** | `actor_id` (Ej. `"ACTOR-LOAD"`) | **Código de Registro Nacional de Regentes Forestales** (SERFOR) + **DNI** del Regente | Registro de Regentes Habilitados (SERFOR) |
| **Transportista / Conductor** | `actor_id` (Ej. `"ACTOR-TEST"`) | **DNI del Chofer** + **Placa Única de Rodaje** del camión | Licencia de Conducir (MTC) & Consulta vehicular (SUNARP) |
| **Operador de Aserradero (CTP)** | `actor_id` (Ej. `"ACTOR-CTP"`) | **RUC de la Planta** + **Código de Registro de Establecimiento Industrial (CTP)** (otorgado por la ARFFS/PRODUCE) | Padrón de Establecimientos Autorizados (PRODUCE/ARFFS) |

---

# II. Matriz de Brechas de Seguridad en la Ingesta de Archivos por Rol

### 1. Ausencia de Control de Roles (RBAC) en API
En el backend, el endpoint `/api/v1/trazabilidad/cargar-archivo` de [main.py](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/backend/api/main.py#L52) recibe directamente archivos `.xlsx` sin requerir tokens de sesión, firmas electrónicas, ni cabeceras que validen la identidad del actor.
*   **Consecuencia de Riesgo:** Cualquier cliente HTTP puede cargar archivos de categoría `censo` o `balances` para inyectar recursos ilegales en la base de datos, simulando el rol de OSINFOR o de la Autoridad Regional Forestal y de Fauna Silvestre (ARFFS).

### 2. Matriz de Permisos y Restricciones Propuesta
Para asegurar que un actor no pueda registrar datos ajenos a su nivel operativo en la cadena, el backend debe restringir la ingesta de las plantillas Excel según el perfil digital autenticado:

```
+------------------------------------+--------------------------+-------------------------------+
| Plantilla Excel (.xlsx)            | Rol Autorizado           | Entidad Estatal Registradora  |
+------------------------------------+--------------------------+-------------------------------+
| Censo Forestal                     | Regente Forestal /       | ARFFS (Autoridad Regional)    |
| (Árboles autorizados para tala)    | Titular del Contrato     |                               |
+------------------------------------+--------------------------+-------------------------------+
| Balances de Extracción             | Solo Fiscalizadores      | OSINFOR / ARFFS               |
| (Cupos autorizados y verificados)  | Gubernamentales          |                               |
+------------------------------------+--------------------------+-------------------------------+
| Libro de Operaciones - Bosque (LOE) | Titular del Contrato /   | SERFOR / OSINFOR              |
| (Registros de Tala y Trozado)      | Supervisor Técnico       |                               |
+------------------------------------+--------------------------+-------------------------------+
| Libro de Operaciones - Planta (LOE)| Operador del CTP         | PRODUCE / ARFFS               |
| (Ingreso de troza, Salida de aserr)| (Aserradero)             |                               |
+------------------------------------+--------------------------+-------------------------------+
```

> [!IMPORTANT]
> **El rol exclusivo del Transportista:**
> El conductor del camión transportista no carga ningún Libro de Operaciones ni balance al sistema. Su acceso en la UI debe limitarse a la consulta del estado de la Guía de Transporte Forestal (GTF) y al registro puntual de incidencias físicas durante la ruta (averías del vehículo, robos, retrasos o incautación regional).

---

# III. Rediseño del Flujo Operativo (Subida Masiva vs. Formularios de Consulta)

### 1. Eliminación de la Fricción en el Frontend
*   **Diagnóstico de la UI:** La pestaña `"Registro Individual"` en [Formulario.jsx](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/frontend/src/pages/Formulario.jsx#L408-L539) presenta un formulario manual interactivo para que el usuario digite campo por campo datos técnicos de tala, trozado y transporte.
*   **Brecha con la Realidad en Selva/Aserradero:** El ingreso fila por fila (digitando individualmente el ID de cada árbol o troza) es impracticable en las operaciones forestales peruanas masivas. Los aserraderos y titulares ya procesan estas transacciones de manera agrupada y las reportan a las autoridades en formatos Excel consolidados (Libros de Operaciones y GTFs).
*   **Redefinición de Roles de Interfaz:**
    *   **Carga Masiva (Exclusivo para Ingesta):** Toda carga operativa de datos de Tala, Trozas, Guías de despacho y Balance debe realizarse al 100% mediante la subida de los archivos Excel (`.xlsx`) que ya generan por obligación legal los regentes, concesionarios y plantas.
    *   **Formularios de Digitación Manual (Para Consulta e Inicio):** El formulario manual debe limitarse en la UI para:
        1.  La creación del perfil de la concesión o ingreso de metadatos básicos del Título Habilitante.
        2.  Consultas en ruta rápidas realizadas por fiscalizadores forestales (ej. ingresar un número físico de GTF para auditar el camión).

### 2. Comportamiento Semántico de las Consultas en la UI
*   **Brecha de Timeline:** En [main.py](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/backend/api/main.py#L253), el endpoint `/api/v1/trazabilidad/timeline/{id_lote}` requiere el ID técnico del lote (`lote_id`, ej. `"LOT-001"`). Sin embargo, un comprador internacional en puerto o un fiscalizador del SERFOR/OSINFOR en carretera no tienen acceso a los IDs internos generados por la base de datos del sistema. Ellos validan utilizando identificadores físicos impresos o visibles.
*   **Propuesta de Rediseño Semántico:** Los endpoints de consulta y el componente frontend [Timeline.jsx](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/frontend/src/pages/Timeline.jsx) deben permitir buscar y resolver la trazabilidad profunda utilizando como parámetros de búsqueda el **Número de la Guía de Transporte Forestal (GTF)** o la **Placa del Vehículo**, haciendo la correspondencia lógica en la base de datos de forma transparente.

---

# IV. Comparativa de Buenas Prácticas con el SIGOsfc e Interoperabilidad PIDE

Para ser considerado una plataforma robusta de nivel de gobierno electrónico peruano, ArborTrust debe acoplarse con la normativa e interoperabilidad oficial:

### 1. Alineación con el SIGOsfc (OSINFOR)
*   **Origen de Balances:** El SIGOsfc es el único repositorio oficial que consolida los volúmenes supervisados y aprobados. En lugar de permitir que los titulares carguen de forma libre sus balances a través del frontend, ArborTrust debe consumir mediante un servicio web de interoperabilidad los saldos oficiales de extracción autorizados directamente del SIGOsfc. Esto previene fraudes de "creación artificial de saldos" en la base de datos local.
*   **Cascada Retroactiva Ex-post:** La lógica de penalización retroactiva en [database.py](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/backend/database.py#L625) se alinea con la potestad sancionadora del OSINFOR. Si una inspección posterior de OSINFOR detecta un árbol inexistente en campo, el sistema bloquea inmediatamente todos los lotes comerciales asociados. Esto debe integrarse con las alertas en tiempo real generadas por el SIGOsfc.

### 2. Alineación con el SISFOR (SERFOR)
*   **Libro de Operaciones Electrónico (LOE):** Las plantillas de carga masiva de ArborTrust no deben requerir esquemas personalizados. Deben heredar la estructura exacta de las hojas de cálculo oficiales del LOE (tanto para Títulos Habilitantes como para Centros de Transformación Primaria) publicadas por SERFOR. De este modo se mitiga el doble registro administrativo para el empresario maderero.

### 3. Integración de Servicios Interoperables en la Plataforma PIDE (PCM)
Para eliminar la digitación propensa a fraudes y las declaraciones juradas falsas, el flujo de operaciones debe consumir servicios web interoperables de las siguientes entidades estatales de control:

```
+------------------------------------+-------------------------------+------------------------------------------+
| Entidad Estatal (PCM-PIDE)         | Servicio Web de Consulta      | Objetivo del Servicio en ArborTrust      |
+------------------------------------+-------------------------------+------------------------------------------+
| SUNAT                              | Consulta RUC                  | Validar que la Concesión y el Aserradero  |
|                                    |                               | tengan RUC activo y habido.              |
+------------------------------------+-------------------------------+------------------------------------------+
| RENIEC                             | Consulta DNI / Huella Digital | Validar la identidad del Regente que     |
|                                    |                               | firma el censo y del conductor.          |
+------------------------------------+-------------------------------+------------------------------------------+
| SUNARP                             | Consulta Vehicular por Placa  | Verificar que la placa del camión        |
|                                    |                               | registrada en la GTF existe y coincide.  |
+------------------------------------+-------------------------------+------------------------------------------+
| MTC                                | Consulta Licencia Conducir    | Validar la vigencia del brevete del      |
|                                    |                               | transportista para el viaje forestal.    |
+------------------------------------+-------------------------------+------------------------------------------+
```

---
*Fin del reporte de Auditoría Funcional y Alineación.*
