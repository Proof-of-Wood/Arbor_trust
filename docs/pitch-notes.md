# Pitch Notes

## Project Name

**ArborTrust**

## Tagline

**Pasaporte Digital Forestal para acreditar el origen legal de la madera.**

---

## 1. Elevator Pitch

ArborTrust es una plataforma digital que permite verificar la trazabilidad legal de un lote de madera desde el árbol autorizado hasta su despacho comercial.

La solución consolida información del censo forestal, libro de operaciones, balance de extracción y guía de transporte para generar un **Pasaporte Digital Forestal** asociado a un código QR.

Este pasaporte puede ser consultado por productores, fiscalizadores y compradores para verificar si un lote tiene origen legal, saldo disponible y trazabilidad documentada.

---

## 2. Problema

Hoy, muchos productores forestales tienen dificultades para demostrar de forma rápida y confiable el origen legal de la madera que comercializan.

Aunque existe información en documentos y sistemas institucionales, esta suele estar dispersa, no siempre es fácil de consultar y no está presentada en un formato simple para quienes toman decisiones en campo o en el mercado.

Esto genera tres problemas principales:

1. El productor tiene que invertir tiempo y recursos para demostrar legalidad.
2. El fiscalizador no siempre cuenta con información clara y oportuna para verificar un lote.
3. El comprador nacional o internacional puede desconfiar del origen de la madera.

---

## 3. Usuarios principales

### Productor forestal

Necesita demostrar que su madera proviene de un origen autorizado y que cuenta con respaldo documental.

### Fiscalizador de ruta

Necesita verificar rápidamente si el lote transportado coincide con la información legal declarada.

### Comprador nacional o internacional

Necesita evidencia clara para confiar en el origen legal del producto maderable.

---

## 4. Solución propuesta

ArborTrust propone una capa digital de confianza que organiza y valida la información forestal existente.

La solución permite:

* Cargar o simular datos forestales relevantes.
* Validar existencia del árbol en el censo.
* Validar especie declarada.
* Validar volumen disponible.
* Validar trazabilidad entre tala, trozado, despacho y GTF.
* Generar un Pasaporte Digital Forestal.
* Asociar el pasaporte a un código QR.
* Mostrar un semáforo de riesgo.
* Entregar un dossier digital para compradores.

---

## 5. Cómo funciona

El flujo principal es:

```txt
Censo Forestal
      ↓
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
Centro de Transformación Primaria (CTP)
      ↓
Producto Final / Pasaporte Digital Forestal
```

ArborTrust toma estos datos, los cruza mediante reglas de validación y genera un resultado simple:

```txt
Verde    → lote válido
Amarillo → lote observado
Rojo     → lote con alerta crítica
```

---

## 6. Demo del prototipo

La demo puede presentarse en tres momentos:

### Paso 1: Productor

El productor ingresa a la plataforma y carga información del Libro de Operaciones.

El sistema identifica el lote, la especie, el volumen, la parcela de corta y la guía de transporte asociada.

### Paso 2: Motor de validación

ArborTrust cruza los datos con el censo forestal, el balance de extracción y la muestra supervisada.

El sistema verifica:

* Si el árbol existe.
* Si la especie coincide.
* Si el volumen está dentro del saldo disponible.
* Si la troza tiene trazabilidad.
* Si el despacho tiene GTF asociada.

### Paso 3: Resultado

Si el lote cumple las reglas principales, se genera un Pasaporte Digital Forestal con QR.

El fiscalizador puede escanear el QR y ver el semáforo de riesgo.

El comprador puede acceder al dossier digital del lote para revisar la evidencia de trazabilidad.

---

## 7. Valor diferencial

ArborTrust no busca reemplazar los sistemas oficiales existentes.

Su valor está en convertir información dispersa en una evidencia digital clara, verificable y fácil de consultar.

La propuesta aporta valor porque:

* Reduce la fricción para demostrar legalidad.
* Facilita la verificación en ruta.
* Mejora la confianza del comprador.
* Ordena la información forestal en una cadena trazable.
* Permite identificar alertas de riesgo antes de la comercialización.
* Puede funcionar inicialmente como prototipo sin depender de interoperabilidad real.

---

## 8. Impacto esperado

### Para productores

Mayor capacidad para demostrar el origen legal de su madera y acceder a mercados más exigentes.

### Para fiscalizadores

Menor dependencia de revisión manual dispersa y mayor rapidez para tomar decisiones en campo.

### Para compradores

Mayor confianza en el producto adquirido mediante evidencia digital verificable.

### Para el Estado

Mejor uso de información existente y posibilidad de fortalecer la trazabilidad forestal sin crear un sistema desde cero.

---

## 9. MVP

El MVP de ArborTrust incluye:

1. Modelo de datos normalizado.
2. Validación de trazabilidad básica.
3. Validación de saldo disponible.
4. Generación de semáforo de riesgo.
5. Generación de Pasaporte Digital Forestal.
6. Código QR asociado al lote.
7. Dossier digital simple.

---

## 10. Fuera del alcance inicial

El prototipo no incluye todavía:

* Interoperabilidad real con sistemas estatales.
* Despliegue productivo en nube.
* Blockchain productiva.
* Aplicación móvil nativa.
* Piloto en campo.
* Escalamiento nacional.
* Automatización completa de documentos oficiales.


Como resultado, ArborTrust genera un código QR y un semáforo de riesgo: verde para lotes válidos, amarillo para lotes observados y rojo para lotes con alerta crítica.

Esto permite que el productor demuestre legalidad, que el fiscalizador verifique rápidamente en ruta y que el comprador acceda a un dossier digital con evidencia de origen legal.

ArborTrust no busca reemplazar los sistemas oficiales existentes. Propone una capa digital de confianza que organiza, valida y presenta la información de manera clara para todos los actores de la cadena forestal.
