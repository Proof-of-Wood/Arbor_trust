# Guía de Pruebas de Extremo a Extremo (E2E) - ArborTrust

Esta guía detalla los pasos para levantar el entorno de ArborTrust y ejecutar todas las pruebas de extremo a extremo, validando la arquitectura **Identity-First** y el **RBAC Dinámico** a nivel de interfaz y base de datos.

---

## 1. Levantamiento del Entorno

Sigue estos pasos en orden para limpiar la base de datos, levantar el backend (FastAPI) y ejecutar el frontend (React/Vite).

### Paso 1: Limpieza e Inicialización de la Base de Datos (Punto Cero)
Abre una consola en la raíz del proyecto y ejecuta:
```powershell
# Activa el entorno virtual del backend y ejecuta el script de restablecimiento
backend\.venv\Scripts\python reset_demo.py
```
*Este comando borrará la base de datos previa y sembrará las tablas y los usuarios iniciales de demostración.*

### Paso 2: Ejecutar el Servidor Backend (FastAPI)
En la misma consola (o en una pestaña nueva):
```powershell
cd backend
# Levantar el servidor Uvicorn en el puerto 8000
..\backend\.venv\Scripts\python -m uvicorn api.main:app --reload --port 8000
```
*El backend estará disponible en `http://localhost:8000` y la documentación interactiva en `http://localhost:8000/docs`.*

### Paso 3: Ejecutar el Servidor Frontend (React/Vite)
Abre otra consola en la raíz del proyecto:
```powershell
cd frontend
# Iniciar el servidor de desarrollo de Vite
npm run dev
```
*El frontend estará disponible en `http://localhost:5173`.*

---

## 2. Matriz de Credenciales de Prueba

En la nueva arquitectura **Identity-First**, no existen selectores manuales dentro de los formularios. Al entrar a la aplicación, se redirige automáticamente a la pantalla de `/login`. Selecciona el actor y completa los campos oficiales:

| Actor en la Demo | Rol en Login | Campo de Identificación | Valor de Prueba |
| :--- | :--- | :--- | :--- |
| **Regente Forestal** | `Regente` | Registro SERFOR y DNI | SERFOR: `REG-SER-2026-0001` / DNI: `12345678` |
| **Titular Concesionario** | `Titular` | RUC del Concesionario | RUC: `20123456789` |
| **Fiscalizador OSINFOR** | `OSINFOR` | Ninguno (Acceso de Autoridad) | *Acceso global preconfigurado* |

---

## 3. Flujos de Pruebas E2E Paso a Paso

### Flujo I: Planificación e Ingesta de Censo (Rol: Regente)
* **Objetivo**: Subir y versionar un Plan de Aprovechamiento Forestal de forma segura.
1. Abre un navegador e ingresa a `http://localhost:5173`. Serás redirigido a `/login`.
2. Selecciona **Regente**, ingresa el Registro SERFOR `REG-SER-2026-0001` y el DNI `12345678`. Haz clic en **Iniciar Sesión**.
3. El sistema te redirigirá automáticamente a `/panel-regente` (única ruta accesible para tu rol).
4. En el panel de **Carga de Archivos (Excel / XLSX)**, arrastra o selecciona el archivo:
   `demo_data/plan_demo.xlsx`
5. El sistema detectará automáticamente la categoría como **Plan de Aprovechamiento**.
6. Haz clic en **Subir y Procesar**.
7. En la cola inferior de procesamiento verás el estado `SUBIENDO` -> `PROCESANDO` -> `COMPLETADO`. El plan se habrá guardado en su **Versión 1**.
8. Cierra sesión haciendo clic en **Salir** en el Navbar.

---

### Flujo II: Registro de Operaciones y Control de Saldos (Rol: Titular)
* **Objetivo**: Registrar eventos de Tala (aprovechamiento) y verificar el bloqueo ante excesos de volumen.
1. Ingresa a `http://localhost:5173/login`.
2. Selecciona **Titular**, ingresa el RUC `20123456789` y haz clic en **Iniciar Sesión**.
3. Serás redirigido a `/panel-titular`.
4. **Prueba A: Registro Individual de Tala**:
   * Selecciona el botón **Tala de Árbol** (Punto 2).
   * En el formulario, completa los siguientes datos exactos:
     * **ID Árbol**: `ARB-DEMO-001` (Volumen autorizado original en censo: `8.5` m³)
     * **Parcela de Corta**: `PC1`
     * **Especie**: `Shihuahuaco`
     * **Volumen**: `4.50`
     * **Fecha**: Deja la fecha actual.
     * **Observaciones**: `Primera tala autorizada.`
   * Haz clic en **Registrar y Validar**.
   * *Resultado*: El sistema lo registrará con éxito, mostrando el hash SHA-256 generado para la bitácora.
5. **Prueba B: Validation en Tiempo Real (Bloqueo por sobre-extracción)**:
   * En la misma pantalla, intenta registrar otra Tala para el mismo árbol:
     * **ID Árbol**: `ARB-DEMO-001`
     * **Volumen**: `5.00` (El acumulado sería `4.50 + 5.00 = 9.50` m³, excediendo los `8.5` m³ autorizados).
   * Haz clic en **Registrar y Validar**.
   * *Resultado*: El backend rechazará la operación y la interfaz mostrará la alerta en rojo:
     `El volumen ingresado excede el saldo de su Plan de Aprovechamiento vigente.`
6. **Prueba C: Carga Masiva de Operaciones (Libro de Operaciones - LOE)**:
   * Haz clic en la pestaña **Carga Masiva (Excel / XLSX)**.
   * Selecciona el archivo:
     `demo_data/operaciones_demo.xlsx`
   * Haz clic en **Cargar Archivos** y confirma que se procese con éxito (`COMPLETADO`).
7. Cierra sesión en el botón **Salir**.

---

### Flujo III: Control en Ruta y Trazabilidad Semántica (Rol: OSINFOR)
* **Objetivo**: Fiscalizar cargamentos forestales, auditar orígenes y aplicar bloqueos retroactivos.
1. Ingresa a `http://localhost:5173/login`.
2. Selecciona **OSINFOR** y haz clic en **Iniciar Sesión**.
3. Serás redirigido a `/dashboard-fiscalizador`.
4. **Prueba A: Buscador Semántico Institucional**:
   * En el panel superior, selecciona el criterio **GTF / Código de Lote**.
   * Escribe el lote de prueba: `LOT-DEMO-001` (o la guía `GTF-DEMO-001`) y haz clic en **Consultar**.
   * *Resultado*: Se desplegará la línea de tiempo interactiva mostrando todo el flujo: `Planificación -> Tala -> Trozado -> Despacho`.
   * El semáforo estará en **Verde (Conforme)**.
5. **Prueba B: Aplicación del "Efecto Guau" (Supervisión Ex-Post y Bloqueo)**:
   * Declara el árbol `ARB-DEMO-001` como fraudulento. Abre la documentación interactiva en `http://localhost:8000/docs`.
   * Ve al endpoint `POST /api/v1/supervision/penalizar-origen`, haz clic en **Try it out** y envía el siguiente JSON:
     ```json
     {
       "arbol_id": "ARB-DEMO-001",
       "motivo": "Árbol fantasma. Supervisión ex-post determinó tocón inexistente en bosque."
     }
     ```
   * Regresa al Dashboard de OSINFOR (`http://localhost:5173/dashboard-fiscalizador`).
   * Vuelve a buscar el lote `LOT-DEMO-001` en el Buscador Semántico.
   * *Resultado (Efecto Guau)*: El semáforo del lote habrá cambiado a **Rojo** y se mostrará la alerta del sistema:
     `[ALERTA RETROACTIVA OSINFOR]: El árbol origen de este recurso fue declarado FALSO tras supervisión ex-post en bosque. Infracción D.L. 1085.`
   * La alerta de fraude también figurará de inmediato en el panel de **Reportes de Inconsistencias y Alertas** del Dashboard de OSINFOR.

---

## 4. Resolución de Problemas (Troubleshooting)

* **¿Problemas de CORS?**: El backend tiene habilitado el middleware de CORS para todos los orígenes (`*`). Asegúrate de que el backend corra en el puerto `8000` y el frontend en el `5173`.
* **¿Base de datos bloqueada (Locked)?**: Si realizas pruebas masivas simultáneas extremas y SQLite arroja un error de bloqueo, el sistema reintentará automáticamente gracias al modo WAL configurado en `database.py`. Si deseas forzar un reinicio limpio, vuelve a ejecutar `reset_demo.py`.
