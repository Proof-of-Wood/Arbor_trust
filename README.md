# ArborTrust - Pasaporte Digital Forestal

**ArborTrust** es un MVP desarrollado para la **Hackatón TransformaGob 2026 (OSINFOR)**. 
Su objetivo es acreditar de manera confiable el origen legal de la madera en el Perú mediante un Pasaporte Digital Forestal.

## 🚀 Arquitectura del Proyecto

El proyecto está dividido en dos componentes principales: un backend robusto basado en **FastAPI** y **SQLite**, y un frontend dinámico construido con **React** y **Vite**.

### 💻 Frontend (React + Vite)
- Interfaz moderna e institucional (modo claro/oscuro).
- Integración de iconografía formal con `lucide-react`.
- Vistas principales:
  1. **Registro Operativo**: Formulario para registrar eventos de tala, trozado, despacho y transformación en la cadena de custodia.
  2. **Pasaporte Digital (Línea de Tiempo)**: Verificador visual del origen de la madera mediante un ID de lote (ej. `LOT-001`, `LOT-002`).
  3. **Control en Ruta (Panel del Fiscalizador)**: Dashboard en tiempo real que aplica un semáforo de riesgo (Verde, Amarillo, Rojo) para alertar sobre inconsistencias y posibles fraudes.

### ⚙️ Backend (FastAPI + SQLite)
- **Base de Datos Relacional**: SQLite (`arbortrust.db`) para almacenar árboles, lotes, balances de extracción y operaciones. 
- **Motor de Integridad (Hashing)**: Registra cada evento en la cadena (tala, transporte, etc.) generando una firma SHA-256 única para garantizar la inmutabilidad y auditoría de los datos (simulación de tecnología blockchain).
- **Motor de Validación (Reglas de Negocio)**: Verifica la existencia de los árboles, saldos volumétricos y cronología de operaciones de acuerdo a la normativa forestal peruana (D.L. N° 1085).
- **API REST**: Expone los endpoints de registro, consulta de trazabilidad y reportes de alertas para el dashboard del fiscalizador, configurado correctamente con CORS.

## 🛠️ Requisitos Previos

- **Node.js** (v18 o superior)
- **Python** (3.10 o superior)

## 🏃 Instrucciones de Ejecución Local

Para levantar el entorno de desarrollo y probar el flujo completo:

### 1. Iniciar el Backend
Abre una terminal y ejecuta los siguientes comandos:
```bash
cd backend
pip install -r requirements.txt
python database.py  # Inicializa la base de datos y carga los datos de prueba
python -m uvicorn api.main:app --port 8000
```
El API de backend estará disponible en `http://localhost:8000`.

### 2. Iniciar el Frontend
Abre una segunda terminal y ejecuta:
```bash
cd frontend
npm install
npm run dev
```
La aplicación web interactiva estará disponible en `http://localhost:5173`.

## 📂 Estructura del Repositorio

- `/frontend/`: Código fuente de la aplicación web con React y Vite.
- `/backend/`: Código fuente del API (FastAPI) y la lógica central (validación e integridad).
- `/docs/`: Documentación detallada sobre la arquitectura, flujo de usuario, modelo de datos y notas clave para el pitch.
- `/data/sample/`: Datos de prueba (archivos CSV) utilizados para poblar la base de datos de manera inicial para la demostración.

## 👥 Equipo
* Integrante 1 - Rol
* Integrante 2 - Rol
* Integrante 3 - Rol
* Integrante 4 - Rol
