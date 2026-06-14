# Architecture

## Nombre del proyecto

**ArborTrust: Pasaporte Digital Forestal para acreditar madera legal**

## Objetivo de la arquitectura

La arquitectura de ArborTrust describe cómo una capa digital de confianza puede consolidar información forestal existente, validar la trazabilidad de un lote de madera y generar evidencia verificable para productores, fiscalizadores y compradores.

El sistema no busca reemplazar los sistemas oficiales existentes. ArborTrust funciona como una plataforma complementaria que toma información proveniente de documentos y sistemas forestales, la cruza mediante reglas de validación y genera un Pasaporte Digital Forestal asociado a un lote de madera.

---

## Principio de diseño

ArborTrust se diseña bajo el siguiente principio:

```txt
Flujo físico de la madera + Flujo documental verificable = Trazabilidad legal confiable
```

Es decir, cada lote de madera debe poder relacionarse con:

* Un título habilitante.
* Un plan operativo o instrumento de gestión aprobado.
* Un censo forestal.
* Un libro de operaciones.
* Un balance de extracción.
* Una guía de transporte forestal.
* Un estado de validación.

---

## Alcance del MVP

El MVP de ArborTrust busca demostrar el flujo funcional principal de la solución:

1. Cargar o simular datos forestales del kit.
2. Validar información de árboles, especies, volúmenes y documentos.
3. Generar un Pasaporte Digital Forestal por lote.
4. Asociar el pasaporte a un código QR.
5. Permitir que un fiscalizador consulte el lote mediante QR.
6. Mostrar un semáforo de riesgo.
7. Generar un dossier digital para el comprador.

El MVP no implementa todavía:

* Interoperabilidad real con SIGOSFC u otros sistemas estatales.
* Despliegue productivo en nube.
* Blockchain productiva.
* Aplicación móvil nativa.
* Piloto en campo.
* Escalamiento nacional.
* Compra de equipos.
* Automatización completa de documentos oficiales.

---

## Sistemas externos de referencia

ArborTrust considera como fuentes conceptuales de información los siguientes sistemas y documentos:

### SIGOSFC / OSINFOR

Sistema de Información Gerencial del OSINFOR (alineado al D.L. N° 1085) usado como referencia para información relacionada con supervisión, fiscalización, títulos habilitantes, planes de manejo, balances y antecedentes.

En el MVP, la conexión con SIGOSFC será simulada mediante archivos de muestra o datos precargados para asegurar el cumplimiento sin requerir interoperabilidad real.

### SNIFFS / SERFOR

Sistema relacionado con información forestal, libro de operaciones electrónico y guías de transporte forestal.

En el MVP, la información será representada mediante archivos Excel, CSV o JSON simulados.

### ARFFS / Gobiernos Regionales

Autoridades regionales vinculadas a la aprobación de planes operativos, resoluciones y control forestal.

En el MVP, esta información se representa como datos de referencia asociados al título habilitante y al plan operativo.

---

## Datos de entrada

El sistema se alimenta de cuatro tipos principales de información.

### 1. Censo Forestal

Contiene los árboles autorizados para aprovechamiento.

Campos esperados:

* Código del árbol.
* Especie.
* Coordenada Este.
* Coordenada Norte.
* DAP.
* Altura.
* Volumen estimado.
* Parcela de corta.
* Título habilitante.
* Estado del árbol.

### 2. Libro de Operaciones

Registra las operaciones realizadas sobre la madera.

Se divide en:

* Tala.
* Trozado.
* Despacho.

Campos esperados:

* Código del árbol.
* Código de troza.
* Especie declarada.
* Diámetros.
* Longitud.
* Volumen.
* Fecha de operación.
* Número de GTF.
* Observaciones.

### 3. Balance de Extracción

Permite verificar el volumen autorizado, movilizado y disponible.

Campos esperados:

* Título habilitante.
* Plan operativo.
* Parcela de corta.
* Especie.
* Volumen autorizado.
* Volumen movilizado.
* Saldo disponible.
* Observaciones.

### 4. Guía de Transporte Forestal

Documento asociado al traslado del producto forestal.

Campos esperados:

* Número de GTF.
* Fecha de emisión.
* Titular.
* Transportista.
* Origen.
* Destino.
* Especie.
* Volumen transportado.
* Lote asociado.

---

## Vista general de arquitectura

```txt
[Datos oficiales / Kit de datos]
        |
        v
[Censo Forestal] [Libro de Operaciones] [Balance de Extracción] [GTF]
        |
        v
[Ingesta y normalización de datos]
        |
        v
[Motor de Validación ArborTrust]
        |
        +--> Validación de título habilitante
        +--> Validación de existencia del árbol
        +--> Validación de especie
        +--> Validación de volumen
        +--> Validación de trazabilidad tala-trozado-despacho
        +--> Validación de GTF
        |
        v
[Pasaporte Digital Forestal]
        |
        +--> Código QR
        +--> Semáforo de riesgo
        +--> Dossier digital
        +--> Hash de integridad
```

---

## Arquitectura por capas

### 1. Capa de presentación

Es la capa con la que interactúan los usuarios.

Componentes:

* Dashboard del productor.
* Pantalla de carga del Libro de Operaciones.
* Pantalla de generación del QR.
* Escáner QR para fiscalizador.
* Pantalla de semáforo de riesgo.
* Dossier digital para comprador.

Usuarios:

* Productor forestal.
* Fiscalizador de ruta.
* Comprador nacional o internacional.

---

### 2. Capa de aplicación

Contiene la lógica funcional del sistema.

Componentes:

* Servicio de carga de archivos.
* Servicio de normalización de datos.
* Servicio de validación de lotes.
* Servicio de generación de QR.
* Servicio de generación de hash.
* Servicio de consulta del dossier.
* Servicio de semáforo de riesgo.

---

### 3. Capa de validación

Es el núcleo de ArborTrust.

Reglas principales:

#### Validación de existencia

Verifica que el árbol o troza declarada exista en el censo forestal.

#### Validación de especie

Compara la especie declarada en el Libro de Operaciones contra la especie registrada en el censo y balance.

#### Validación de volumen

Verifica que el volumen declarado no exceda el volumen autorizado ni el saldo disponible.

#### Validación de trazabilidad

Comprueba que exista una cadena coherente:

```txt
Árbol censado
    |
    v
Tala
    |
    v
Trozado
    |
    v
Despacho
    |
    v
GTF
    |
    v
Lote comercial
    |
    v
Centro de Transformación Primaria (CTP)
    |
    v
Producto Semielaborado / Madera Aserrada
```

#### Validación documental

Verifica que el lote tenga una GTF asociada y que los datos principales coincidan con los registros cargados.

---

### 4. Capa de datos

Almacena los datos usados por el prototipo.

Entidades principales:

* Productor.
* Título habilitante.
* Plan operativo.
* Parcela de corta.
* Árbol censado.
* Troza.
* Lote.
* Balance de extracción.
* GTF.
* Validación.
* Pasaporte digital.
* Dossier.

---

### 5. Capa de integridad

Permite verificar que la información del lote no haya sido alterada.

Componentes:

* Identificador único del lote.
* Hash SHA-256 del expediente.
* Fecha de generación.
* Estado de validación.
* Registro de eventos del lote.

El hash se calcula a partir de los datos principales del lote:

```txt
Código de lote + GTF + especie + volumen + origen + fecha + estado de validación
```

Si alguno de estos datos cambia, el hash resultante también cambia.

---

## Motor de Validación ArborTrust

El Motor de Validación ArborTrust recibe los datos normalizados y genera un resultado de riesgo.

### Entrada del motor

```txt
{
  "codigo_lote": "LOT-001",
  "gtf": "017-0001271",
  "codigo_arbol": "3403",
  "especie": "Shihuahuaco",
  "volumen_lote": 12.5,
  "parcela_corta": "PC-01",
  "titulo_habilitante": "TH-001"
}
```

### Proceso

1. Buscar el árbol en el censo forestal.
2. Validar que la especie coincida.
3. Verificar volumen disponible en el balance de extracción.
4. Verificar relación entre tala, trozado y despacho.
5. Asociar el lote con una GTF.
6. Calcular el estado de riesgo.
7. Generar el Pasaporte Digital Forestal.

### Salida del motor

```txt
{
  "codigo_lote": "LOT-001",
  "estado": "VERDE",
  "mensaje": "Lote válido con saldo disponible y trazabilidad consistente",
  "hash": "SHA256_HASH",
  "qr_url": "/passport/LOT-001"
}
```

---

## Semáforo de riesgo

El sistema clasifica cada lote en tres estados:

### Verde

El lote es consistente.

Condiciones:

* Árbol registrado.
* Especie coincidente.
* Volumen dentro del saldo disponible.
* GTF asociada.
* Trazabilidad completa.

### Amarillo

El lote requiere revisión.

Condiciones posibles:

* Datos incompletos.
* Observaciones menores.
* Diferencias menores entre documentos.
* Falta de algún dato no crítico.

### Rojo

El lote presenta alerta crítica.

Condiciones posibles:

* Árbol inexistente.
* Especie inconsistente.
* Volumen mayor al saldo disponible.
* GTF no asociada.
* Posible sobreextracción.
* Ruptura de trazabilidad.

---

## Artefactos generados

### 1. Pasaporte Digital Forestal

Documento digital que resume la trazabilidad del lote.

Contiene:

* Código del lote.
* Número de GTF.
* Productor.
* Título habilitante.
* Especie.
* Volumen.
* Origen.
* Estado de validación.
* Hash de integridad.
* Enlace al dossier.

### 2. Código QR

Permite consultar rápidamente el estado del lote.

Uso:

* Control en ruta.
* Consulta pública.
* Acceso al dossier del lote.

### 3. Dossier digital

Vista o documento descargable para compradores.

Contiene:

* Información del productor.
* Información del lote.
* Procedencia.
* Especie.
* Volumen.
* Trazabilidad tala-trozado-despacho.
* GTF asociada.
* Estado de validación.
* Hash de integridad.

### 4. Registro de validación

Guarda el resultado de las reglas aplicadas.

Contiene:

* Fecha de validación.
* Reglas ejecutadas.
* Resultado de cada regla.
* Estado final.
* Observaciones.

---

## Flujo técnico principal

```txt
1. Productor carga Libro de Operaciones
        |
        v
2. Sistema normaliza datos de tala, trozado y despacho
        |
        v
3. Sistema cruza datos con censo forestal y balance de extracción
        |
        v
4. Motor valida especie, volumen, árbol, saldo y GTF
        |
        v
5. Sistema asigna estado de riesgo
        |
        v
6. Si el lote es válido, se genera Pasaporte Digital Forestal
        |
        v
7. Se genera QR del lote
        |
        v
8. Fiscalizador escanea QR en ruta
        |
        v
9. Comprador consulta dossier digital
```

---

## Modelo conceptual de entidades

```txt
Productor
   |
   v
Título Habilitante
   |
   v
Plan Operativo
   |
   v
Parcela de Corta
   |
   v
Árbol Censado
   |
   v
Tala
   |
   v
Trozado
   |
   v
Despacho
   |
   v
GTF
   |
   v
Lote
   |
   v
Pasaporte Digital Forestal
```

---

## Decisiones de prototipo

Para mantener el alcance realista durante la hackatón, se tomarán estas decisiones:

1. Las integraciones con sistemas oficiales serán simuladas.
2. Los datos del kit se usarán como fuente de prueba.
3. El procesamiento de PDF puede simularse con datos previamente estructurados.
4. El QR apuntará a una vista interna del prototipo.
5. El hash SHA-256 se usará como mecanismo simple de integridad.
6. El semáforo de riesgo será calculado mediante reglas determinísticas.
7. La visualización geográfica será opcional para el MVP inicial.

---

## Stack tecnológico tentativo

### Frontend

* React.
* Vite.
* Tailwind CSS.

### Backend

* Python con FastAPI o Node.js con Express.

### Procesamiento de datos

* Python.
* Pandas.
* OpenPyXL.
* CSV/JSON para datos normalizados.

### Base de datos

* SQLite para prototipo local.
* PostgreSQL como opción futura.

### Utilidades

* Librería de generación de QR.
* Hash SHA-256.
* Leaflet para mapas si se implementa visualización geográfica.

---

## Componentes mínimos del MVP

El MVP debe incluir:

1. Carga de archivo o datos simulados.
2. Validación de volumen.
3. Validación de especie.
4. Validación de existencia del árbol.
5. Validación básica de trazabilidad.
6. Generación de QR.
7. Pantalla de consulta del lote.
8. Semáforo de riesgo.
9. Dossier digital simple.
10. Hash de integridad.

---

## Componentes futuros

En una versión posterior se podrían incluir:

* Integración real con SIGOSFC.
* Integración con SNIFFS/SERFOR.
* Integración con ARFFS.
* Firma digital institucional.
* Blockchain productiva.
* Modo offline avanzado para fiscalizadores.
* Validación anatómica de especies.
* Monitoreo satelital.
* Aplicación móvil nativa.
* Despliegue en nube.
* Piloto en campo.

---

## Resumen

ArborTrust se plantea como una capa digital de confianza sobre la información forestal existente.

La arquitectura permite conectar el flujo físico de la madera con el flujo documental requerido para demostrar legalidad. El resultado es un Pasaporte Digital Forestal que puede ser consultado por productores, fiscalizadores y compradores mediante QR, semáforo de riesgo y dossier digital.
