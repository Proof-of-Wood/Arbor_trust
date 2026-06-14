# Guía de Demostración y Pitch (Cheat Sheet): ArborTrust

Esta guía proporciona el guion técnico y de negocio paso a paso para presentar **ArborTrust** ante el jurado, destacando la interoperabilidad con PIDE y el "Efecto Guau" de la validación retroactiva.

---

## 1. Matriz de Identidades PIDE (Credenciales de Demo)

Configura estas identidades en el panel superior de **Simulación de Sesión PIDE** según el rol del acto correspondiente:

| Rol de Presentación | Rol PIDE Seleccionado | RUC / Registro / Identidad | Nombre / Razón Social | Permisos de UI |
| :--- | :--- | :--- | :--- | :--- |
| **Regente Forestal** | `Regente` | `REG-SER-2026-0001` | REGENTE DEMO | Carga de Planes de Aprovechamiento y Censo |
| **Titular Concesionario** | `Titular` | `20123456789` | PRODUCTOR DEMO | Registro de Tala, Trozado e Ingesta LOE |
| **Operador CTP** | `Operador_CTP` | `20999999999` | ASERRADERO PUCALLPA DEMO | Registro de Transformación CTP |
| **Transportista** | `Transportista` | DNI: `12345678` / Placa: `ABC-123` | CHOFER DEMO | Consulta en Ruta |
| **Fiscalizador OSINFOR**| `OSINFOR` | *Acceso de Autoridad Estatal* | OSINFOR SUPERVISOR | Buscador Semántico Global, Semáforos y Alertas |

---

## 2. Guion del Pitch: Paso a Paso (3 Actos)

### **Acto I: Planificación y Versionado de Planes (Rol: Regente)**
* **Objetivo**: Mostrar cómo el Regente Forestal (profesional autorizado por el Estado) inicia la cadena de custodia subiendo el Plan de Aprovechamiento aprobado y su censo forestal.
* **Pasos**:
  1. Configura el panel superior PIDE:
     - Rol: `Regente Forestal`
     - Registro SERFOR: `REG-SER-2026-0001`
  2. Ve a la sección **Registro y Carga de Datos** en la barra lateral y selecciona la pestaña **Carga Masiva (Excel / XLSX)**.
  3. Arrastra y suelta el archivo [plan_demo.xlsx](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/demo_data/plan_demo.xlsx) de la carpeta `demo_data/` (se autodetecta la categoría como `Plan de Aprovechamiento`).
  4. Haz clic en **Cargar Archivos**.
  5. *Discurso*: *"Explicamos al jurado que el sistema valida automáticamente la firma digital del Regente y los datos del censo, creando la Versión 1 en la base de datos de manera atómica. Si se sube una nueva versión, el sistema incrementa el número y marca la anterior como 'Vencido' de forma transaccional."*

### **Acto II: Ingesta en el Libro de Operaciones y Verificación Ex-ante (Rol: Titular)**
* **Objetivo**: Mostrar el flujo de aprovechamiento forestal (Tala, Trozado y Despacho) y cómo el backend valida en tiempo real la propiedad del título y los volúmenes del censo.
* **Pasos**:
  1. Configura el panel superior PIDE:
     - Rol: `Titular Concesionario`
     - RUC Institucional: `20123456789`
  2. En la pestaña **Carga Masiva**, arrastra y suelta el archivo [operaciones_demo.xlsx](file:///c:/Users/Acer/Desktop/Estudio/Proyectos/ArborTrust/Arbor_trust/demo_data/operaciones_demo.xlsx) (se autodetecta como `Libro de Operaciones`).
  3. Haz clic en **Cargar Archivos**.
  4. *Discurso*: *"El sistema procesa en paralelo los eventos de Tala, Trozado y Despacho. El backend verifica mediante las cabeceras PIDE que la concesión pertenezca al RUC autenticado, que el árbol exista en el censo y que el volumen talado esté dentro de la cuota autorizada. Cada evento es firmado con SHA-256 en nuestra bitácora de integridad."*
  5. Ve a la vista de **Títulos Habilitantes** (Dashboard de Titular) y haz clic en **Ver Censo y Trazabilidad** para el título `TH-001`. Muestra cómo el árbol `ARB-DEMO-001` figura ahora como **Aprovechado** mientras los demás siguen en pie.

### **Acto III: Consulta Semántica y el "Efecto Guau" (Rol: OSINFOR)**
* **Objetivo**: Demostrar el poder de la fiscalización ex-post y el bloqueo retroactivo automático en toda la cadena ante la detección de un árbol falso (lavado de madera).
* **Pasos**:
  1. Configura el panel superior PIDE:
     - Rol: `Fiscalizador OSINFOR`
  2. Ve al **Buscador Semántico Institucional** en la parte superior del Dashboard (visible solo para roles estatales).
  3. Selecciona el criterio **GTF / Código de Lote**, escribe `GTF-DEMO-001` y haz clic en **Consultar**.
  4. Muestra la línea de tiempo vertical paso a paso renderizada dinámicamente: `Planificación -> Tala -> Trozado -> Despacho`. Explica que el semáforo está en **Verde (Conforme)**.
  5. **El Efecto Guau (Penalización Retroactiva)**:
     - Abre una pestaña en tu navegador en Swagger Docs (`http://localhost:8000/docs`) o simula la petición HTTP utilizando PowerShell / cURL para declarar el árbol de censo como fraudulento.
     - Ejecuta la petición:
       ```bash
       Invoke-RestMethod -Uri "http://localhost:8000/api/v1/supervision/penalizar-origen" -Method Post -ContentType "application/json" -Body '{"arbol_id":"ARB-DEMO-001","motivo":"El arbol no existe fisicamente en la parcela (tocon inexistente). Fraude por blanqueo."}'
       ```
     - Regresa al Dashboard de OSINFOR y vuelve a consultar la guía `GTF-DEMO-001` en el buscador semántico.
     - **¡EFECTO GUAU!**: El semáforo del lote se ha vuelto **Rojo (Falla Crítica — Posible Fraude)**. Se despliega la alerta retroactiva de OSINFOR:
       `[ALERTA RETROACTIVA OSINFOR]: El árbol origen de este recurso fue declarado FALSO tras supervisión ex-post en bosque. Infracción D.L. 1085.`
     - Explica que el sistema alertó y bloqueó de manera recursiva a todos los lotes y guías asociadas a las trozas de ese árbol falso en toda la cadena de suministro nacional en milisegundos.

---

## 3. Comandos de Inicialización Rápida
Antes de que entre el jurado, ejecuta los siguientes comandos para limpiar el entorno de desarrollo y dejar el sistema en punto cero:

1. **Restablecer Base de Datos**:
   ```bash
   backend\.venv\Scripts\python reset_demo.py
   ```
2. **Levantar Servidor Backend**:
   ```bash
   cd backend
   .venv\Scripts\python -m uvicorn api.main:app --reload --port 8000
   ```
3. **Levantar Servidor Frontend (en otra consola)**:
   ```bash
   cd frontend
   npm run dev
   ```
