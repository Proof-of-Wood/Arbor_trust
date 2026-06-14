# User Flow

## Objetivo del documento

Este documento describe el flujo principal de uso de ArborTrust según los cuatro actores clave de la solución:

1. Productor forestal.
2. Fiscalizador de ruta.
3. Comprador nacional o internacional.
4. Operador de Centro de Transformación Primaria (CTP).

El objetivo es mostrar cómo cada usuario interactúa con el Pasaporte Digital Forestal para verificar la trazabilidad legal de la madera.

---

## 1. Flujo del productor forestal

### Objetivo del productor

Demostrar que la madera que transporta y comercializa proviene de un origen legal, con volumen autorizado y documentación verificable.

### Flujo principal

1. El productor inicia sesión en la plataforma.
2. Ingresa al dashboard de saldos disponibles.
3. Revisa el volumen autorizado, extraído y disponible por especie.
4. Carga el Libro de Operaciones.
5. El sistema valida la información de tala, trozado y despacho.
6. Si los datos son consistentes, el sistema permite generar un Pasaporte Digital Forestal.
7. El productor descarga o imprime el código QR del lote.
8. El QR acompaña al lote durante el transporte y comercialización.

### Resultado esperado

El productor obtiene una evidencia digital verificable que respalda el origen legal de su madera.

---

## 2. Flujo del fiscalizador de ruta

### Objetivo del fiscalizador

Verificar de forma rápida y estandarizada si el producto transportado coincide con la información legal declarada.

### Flujo principal

1. El fiscalizador abre la aplicación móvil o PWA.
2. Selecciona la opción de escanear QR.
3. Escanea el Pasaporte Digital Forestal del lote.
4. El sistema consulta la información asociada al lote.
5. Se muestra un resumen con GTF, especie, volumen, procedencia y estado del lote.
6. El sistema muestra un semáforo de riesgo.

### Estados posibles

* Verde: lote válido, con saldo disponible y documentación consistente.
* Amarillo: lote con observaciones que requieren revisión.
* Rojo: lote con alerta crítica, posible sobreextracción o inconsistencia documental.

### Resultado esperado

El fiscalizador toma una decisión más rápida y con criterios estandarizados.

---

## 3. Flujo del comprador

### Objetivo del comprador

Verificar la procedencia y trazabilidad legal de la madera antes de realizar una compra.

### Flujo principal

1. El comprador ingresa a la vitrina o catálogo de lotes disponibles.
2. Filtra lotes por especie, volumen o procedencia.
3. Selecciona un lote de interés.
4. Consulta el dossier digital del lote.
5. Revisa la información de origen, documentos asociados y trazabilidad.
6. Descarga el dossier como evidencia de debida diligencia.

### Resultado esperado

El comprador obtiene mayor confianza sobre el origen legal del producto maderable.

---

## 4. Flujo del Operador CTP (Transformación Primaria)

### Objetivo del operador

Registrar el ingreso de lotes de madera en rollo, su procesamiento y el despacho de productos semielaborados o madera aserrada, manteniendo la cadena de custodia.

### Flujo principal

1. El operador CTP recibe el lote físico y escanea el Pasaporte Digital Forestal.
2. El sistema valida el estado del lote. Si es Verde, permite el ingreso.
3. El operador registra el volumen ingresado y el tipo de producto a obtener.
4. Tras el aserrío, registra el volumen de salida y emite una nueva GTF de salida.
5. El sistema genera un nuevo Pasaporte Digital o actualiza la línea de tiempo del pasaporte original.

### Resultado esperado

Se asegura la continuidad de la trazabilidad incluso después de la primera transformación industrial.

---

## Flujo general resumido

```txt
Productor
   |
   v
Carga Libro de Operaciones
   |
   v
Sistema valida saldos, especie, volumen y trazabilidad
   |
   v
Generación de Pasaporte Digital Forestal QR
   |
   +------------------> Fiscalizador escanea QR
   |                         |
   |                         v
   |                  Semáforo de validación
   |
   +------------------> Operador CTP escanea QR e Ingresa lote
   |                         |
   |                         v
   |                  Procesamiento y Despacho Aserrado
   |
   +------------------> Comprador consulta dossier digital
                             |
                             v
                    Evidencia de origen legal
```

## Pantallas relacionadas

1. Dashboard de saldos del productor.
2. Carga del Libro de Operaciones.
3. Generación del QR del lote.
4. Escáner móvil del fiscalizador.
5. Resultado con semáforo de riesgo.
6. Dossier digital para comprador.
