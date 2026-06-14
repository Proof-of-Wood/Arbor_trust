# Data Model

## Objetivo

Este documento describe cómo ArborTrust organiza la información necesaria para validar la trazabilidad legal de un lote de madera y generar un Pasaporte Digital Forestal.

El modelo no busca exponer la data original del reto ni replicar una base institucional completa. Su propósito es definir una estructura clara, simplificada y segura para que el prototipo pueda trabajar con datos normalizados.

---

## Principio del modelo

ArborTrust conecta cuatro bloques principales de información:

```txt
Censo Forestal + Muestra Supervisada + Libro de Operaciones + Balance de Extracción
```

Estos bloques permiten reconstruir la cadena de trazabilidad:

```txt
Árbol autorizado
      ↓
Tala
      ↓
Trozado
      ↓
Despacho
      ↓
Guía de Transporte Forestal
      ↓
Lote comercial
      ↓
Pasaporte Digital Forestal
```

El objetivo es asociar el flujo físico de la madera con evidencia documental verificable.

---

## Fuentes lógicas de información

### 1. Censo Forestal

Representa la línea base del aprovechamiento. Contiene información de los árboles autorizados dentro de un título habilitante, plan operativo o parcela de corta.

Uso dentro de ArborTrust:

* Verificar que el árbol declarado existe.
* Identificar especie, volumen y ubicación del árbol.
* Relacionar el árbol con una parcela de corta.
* Validar que el origen del lote corresponde a un recurso autorizado.

Campos conceptuales relevantes:

* Identificador del árbol.
* Título habilitante.
* Titular o productor.
* Plan operativo.
* Parcela de corta.
* Especie.
* Volumen estimado.
* Diámetro.
* Altura.
* Coordenadas.
* Estado o condición del árbol.
* Observaciones.

---

### 2. Libro de Operaciones

Registra el proceso operativo de aprovechamiento de la madera.

Se organiza en tres etapas:

```txt
Tala → Trozado → Despacho
```

Uso dentro de ArborTrust:

* Verificar que un árbol autorizado fue talado.
* Relacionar el árbol con sus trozas.
* Relacionar las trozas con un despacho.
* Asociar el despacho con una Guía de Transporte Forestal.
* Reconstruir la trazabilidad física del producto.

Campos conceptuales relevantes:

* Identificador del árbol.
* Identificador de troza.
* Fecha de operación.
* Especie declarada.
* Dimensiones.
* Volumen declarado.
* Código de despacho.
* Número de GTF.
* Observaciones.

---

### 3. Balance de Extracción

Permite controlar el volumen autorizado, movilizado y disponible por especie, parcela o plan operativo.

Uso dentro de ArborTrust:

* Validar si existe saldo disponible.
* Detectar posible sobreextracción.
* Comparar volumen declarado contra volumen autorizado.
* Alimentar el semáforo de riesgo.

Campos conceptuales relevantes:

* Título habilitante.
* Plan operativo.
* Parcela de corta.
* Especie.
* Producto.
* Volumen autorizado.
* Volumen movilizado.
* Saldo disponible.
* Estado del saldo.
* Observaciones.

---

### 4. Muestra Supervisada

Contiene información verificada durante supervisiones o controles.

Uso dentro de ArborTrust:

* Contrastar información declarada con información observada.
* Detectar diferencias de especie, estado, condición o ubicación.
* Identificar alertas de riesgo.
* Reforzar el dossier de trazabilidad.

Campos conceptuales relevantes:

* Identificador del árbol declarado.
* Identificador del árbol verificado.
* Título habilitante.
* Informe de supervisión.
* Especie declarada.
* Especie verificada.
* Coincidencia de especie.
* Coordenadas declaradas.
* Coordenadas verificadas.
* Diámetro declarado.
* Diámetro verificado.
* Estado declarado.
* Estado verificado.
* Condición declarada.
* Condición verificada.
* Observaciones.

---

## Modelo normalizado del prototipo

Para que ArborTrust pueda validar la trazabilidad, las fuentes originales se transforman en tablas simples y normalizadas.

La estructura sugerida es:

```txt
data/
├── README.md
├── raw/
│   └── datos_originales_no_publicables/
├── sample/
│   └── datos_reducidos_o_anonimizados/
└── processed/
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

---

## Entidades principales

### arboles

Representa los árboles autorizados para aprovechamiento.

Campos mínimos:

```txt
arbol_id
titulo_habilitante_id
titular
plan_operativo
parcela_corta
especie
volumen_censado
diametro
altura
coordenada_este
coordenada_norte
estado
condicion
observacion
```

---

### supervisiones

Representa información verificada en campo o durante supervisión.

Campos mínimos:

```txt
supervision_id
arbol_id_declarado
arbol_id_verificado
titulo_habilitante_id
informe_numero
especie_declarada
especie_verificada
coincide_especie
estado_declarado
estado_verificado
condicion_declarada
condicion_verificada
observacion
```

---

### operaciones_tala

Representa el registro de tala de árboles.

Campos mínimos:

```txt
tala_id
arbol_id
parcela_corta
fecha_tala
especie_declarada
volumen_talado
observacion
```

---

### operaciones_trozado

Representa las trozas generadas a partir de un árbol talado.

Campos mínimos:

```txt
troza_id
arbol_id
parcela_corta
fecha_trozado
especie_declarada
volumen_troza
observacion
```

---

### operaciones_despacho

Representa la salida de trozas asociadas a una guía de transporte.

Campos mínimos:

```txt
despacho_id
troza_id
codigo_despacho
numero_gtf
parcela_corta
fecha_despacho
observacion
```

---

### balances_extraccion

Representa el control de volumen autorizado, movilizado y disponible.

Campos mínimos:

```txt
balance_id
titulo_habilitante_id
plan_operativo
parcela_corta
especie
volumen_autorizado
volumen_movilizado
saldo_disponible
estado_saldo
observacion
```

---

### lotes

Representa el conjunto de madera que será validado, transportado o comercializado.

Campos mínimos:

```txt
lote_id
numero_gtf
titulo_habilitante_id
titular
parcela_corta
especie_principal
volumen_total
fecha_creacion
estado_validacion
```

---

### validaciones

Representa el resultado de las reglas aplicadas a un lote.

Campos mínimos:

```txt
validacion_id
lote_id
regla
resultado
severidad
mensaje
fecha_validacion
```

---

### pasaportes

Representa el Pasaporte Digital Forestal generado para un lote.

Campos mínimos:

```txt
pasaporte_id
lote_id
numero_gtf
qr_url
hash_integridad
estado
fecha_generacion
```

---

## Relaciones principales

La relación principal del modelo sigue la trazabilidad física y documental de la madera:

```txt
arboles.arbol_id
      ↓
operaciones_tala.arbol_id
      ↓
operaciones_trozado.arbol_id
      ↓
operaciones_despacho.troza_id
      ↓
lotes.numero_gtf
      ↓
pasaportes.lote_id
```

Relaciones complementarias:

```txt
balances_extraccion.titulo_habilitante_id
balances_extraccion.parcela_corta
balances_extraccion.especie

supervisiones.arbol_id_declarado
supervisiones.arbol_id_verificado
```

---

## Reglas de validación

### Regla 1: existencia del árbol

Todo árbol declarado en operaciones debe existir en el censo normalizado.

```txt
operaciones_tala.arbol_id debe existir en arboles.arbol_id
```

### Regla 2: trazabilidad de troza

Toda troza debe poder asociarse a un árbol talado.

```txt
operaciones_trozado.arbol_id debe existir en operaciones_tala.arbol_id
```

### Regla 3: despacho válido

Toda troza despachada debe existir previamente en trozado.

```txt
operaciones_despacho.troza_id debe existir en operaciones_trozado.troza_id
```

### Regla 4: GTF obligatoria

Todo despacho debe estar asociado a una Guía de Transporte Forestal.

```txt
operaciones_despacho.numero_gtf no debe estar vacío
```

### Regla 5: especie consistente

La especie declarada durante las operaciones debe ser consistente con la especie del censo.

```txt
operaciones_tala.especie_declarada debe coincidir con arboles.especie
```

### Regla 6: volumen disponible

El volumen del lote no debe superar el saldo disponible en el balance de extracción.

```txt
lotes.volumen_total <= balances_extraccion.saldo_disponible
```

### Regla 7: alerta por supervisión

Si la muestra supervisada reporta inconsistencias relevantes, el lote debe ser observado o bloqueado.

```txt
supervisiones.coincide_especie = false → estado_validacion = amarillo o rojo
```

---

## Estados del semáforo

### Verde

El lote cumple las reglas principales:

* Árbol existente.
* Especie consistente.
* Troza trazable.
* GTF asociada.
* Volumen dentro del saldo disponible.
* Sin observaciones críticas.

### Amarillo

El lote tiene observaciones que requieren revisión:

* Datos incompletos.
* Diferencias menores.
* Observaciones no críticas.
* Revisión manual recomendada.

### Rojo

El lote presenta una inconsistencia crítica:

* Árbol inexistente.
* Troza no trazable.
* Despacho sin GTF.
* Especie inconsistente.
* Volumen mayor al saldo disponible.
* Saldo negativo.
* Observación crítica en supervisión.

---

## Nota sobre datos originales

Este documento describe el modelo conceptual y normalizado de ArborTrust. No expone la data original completa del reto ni replica los archivos fuente.

Para el prototipo se trabajará con datos reducidos, simulados, procesados o anonimizados según corresponda.

---

## Resumen

El modelo de datos de ArborTrust organiza la información en una cadena verificable:

```txt
Censo → Tala → Trozado → Despacho → GTF → Lote → Pasaporte
```

Esta estructura permite validar el origen legal de la madera, calcular el riesgo del lote y generar evidencia digital para productores, fiscalizadores y compradores.
