# Data

Esta carpeta contiene los datos utilizados por el prototipo de ArborTrust.

El objetivo de esta sección no es publicar la data original completa, sino organizar datos reducidos, procesados o anonimizados que permitan demostrar el funcionamiento del sistema.

---

## Estructura de la carpeta

```txt
data/
├── README.md
├── sample/
└── processed/
```

---

## sample/

La carpeta `sample/` contiene datos de ejemplo, reducidos o anonimizados.

Estos archivos sirven para probar el prototipo sin exponer información sensible o documentos originales completos.

Ejemplos de archivos esperados:

```txt
sample/
├── arboles_sample.csv
├── supervisiones_sample.csv
├── operaciones_tala_sample.csv
├── operaciones_trozado_sample.csv
├── operaciones_despacho_sample.csv
├── balances_extraccion_sample.csv
└── lotes_sample.csv
```

Uso principal:

* Mostrar una demo funcional.
* Probar reglas de validación.
* Evitar subir archivos pesados o sensibles.
* Facilitar que otros entiendan el flujo de datos.

---

## processed/

La carpeta `processed/` contiene datos ya transformados al modelo normalizado de ArborTrust.

Estos archivos son generados a partir de las fuentes originales o de muestras reducidas.

Ejemplos de archivos esperados:

```txt
processed/
├── arboles.csv
├── supervisiones.csv
├── operaciones_tala.csv
├── operaciones_trozado.csv
├── operaciones_despacho.csv
├── balances_extraccion.csv
├── lotes.csv
├── validaciones.csv
└── pasaportes.csv
```

Uso principal:

* Alimentar el backend del prototipo.
* Ejecutar reglas de validación.
* Generar estados de semáforo.
* Generar pasaportes digitales forestales.
* Probar scripts de QR y hash.

---

## Datos originales

Los datos originales del reto no deben subirse completos a este repositorio si contienen información sensible, archivos pesados o documentos no autorizados para publicación.

En caso se trabaje localmente con datos originales, se recomienda mantenerlos fuera del repositorio o en una carpeta local ignorada por Git.

Ejemplo de carpeta local no versionada:

```txt
data/raw/
```

La carpeta `raw/` puede usarse localmente para guardar archivos originales, pero no debe publicarse en el repositorio si contiene información sensible o pesada.

---

## Relación con el modelo de datos

El diseño lógico de las entidades se encuentra documentado en:

```txt
docs/data-model.md
```

Ese documento explica cómo ArborTrust organiza la información en entidades como:

* arboles
* supervisiones
* operaciones_tala
* operaciones_trozado
* operaciones_despacho
* balances_extraccion
* lotes
* validaciones
* pasaportes

---

## Flujo esperado de datos

```txt
Datos originales o de muestra
        ↓
Limpieza y normalización
        ↓
Archivos procesados
        ↓
Motor de validación
        ↓
Semáforo de riesgo
        ↓
Pasaporte Digital Forestal
```

---

## Reglas generales

1. No subir archivos originales completos si contienen información sensible.
2. No subir archivos muy pesados al repositorio.
3. Usar `sample/` para datos pequeños y demostrativos.
4. Usar `processed/` para datos ya normalizados.
5. Documentar cualquier transformación importante en scripts o notas técnicas.
6. Mantener nombres de archivos claros y consistentes.

---

## Estado actual

La estructura de datos se encuentra en fase inicial. Durante el desarrollo del prototipo se agregarán archivos de muestra y archivos procesados según las necesidades del motor de validación.
