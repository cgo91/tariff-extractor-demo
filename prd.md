# PRD — Asistente de clasificación arancelaria y pedimento (MVP)

Documento derivado de `vision.md`. Define las funcionalidades **mínimas indispensables** para completar el flujo: foto de producto → extracción → fracción/NICO → pedimento PDF.

## 1. Objetivo del MVP

Un usuario autenticado sube la foto de un producto de electrónica de consumo, el sistema extrae sus características, propone una fracción arancelaria + NICO con confianza y justificación, el usuario la confirma o corrige, captura los datos mínimos de la operación y descarga un pedimento simulado en PDF.

## 2. Usuario y flujo principal

**Usuario:** una sola persona (rol único), quien opera la demo.

**Flujo (happy path):**

1. Inicia sesión.
2. Crea una operación subiendo una foto.
3. Ve la extracción de características.
4. Ve la fracción/NICO propuesta, confianza, justificación y candidatos alternos.
5. Confirma la propuesta o selecciona otro candidato.
6. Captura valor, cantidad, país de origen y tipo de cambio.
7. Genera y descarga el pedimento PDF.
8. Consulta la operación en el historial.

**Flujo alterno:** confianza baja (< 0.6) → la UI marca la operación como "requiere revisión" y no permite generar pedimento hasta que el usuario confirme manualmente una fracción.

## 3. Requerimientos funcionales

Prioridad: **P0** = indispensable para el flujo; **P1** = necesario para que la demo sea creíble.

### RF-01 Autenticación (P0)

- Endpoint `POST /auth/login` con email y contraseña; responde JWT (HS256, expiración 8 h).
- Un usuario creado por el seed. Sin registro, sin refresh, sin recuperación.
- Todos los endpoints excepto login requieren `Authorization: Bearer <token>`.
- Frontend: vista de login; guarda el token en memoria/localStorage y redirige a "Nueva operación".

**Aceptación:** con credenciales válidas se obtiene token; sin token cualquier endpoint protegido responde 401.

### RF-02 Catálogo de fracciones (P0)

- Script `seed.py` que carga la colección `fracciones` a partir del Excel SAT `c_FraccionArancelaria` filtrado a capítulos 84 y 85, cruzado con aranceles de SNICE.
- Fallback: JSON mock de ~50 fracciones si el Excel no se puede procesar.
- Índice de texto en `descripcion` y `descripcion_partida`.
- Endpoint `GET /catalog/search?q=` que devuelve hasta 15 fracciones por relevancia.

**Aceptación:** el seed corre en un solo comando; una búsqueda por "audífonos" devuelve fracciones de la partida 8518.

### RF-03 Subida de imagen y creación de operación (P0)

- Endpoint `POST /operations` (multipart) que acepta JPG/PNG hasta 10 MB; convierte HEIC si se recibe.
- Guarda el archivo en disco (`/data/uploads/<operation_id>.<ext>`) y crea el documento en `operations` con `status = "creada"`.
- Frontend: selector de archivo con vista previa antes de enviar.

**Aceptación:** al subir una imagen válida se obtiene un `operation_id`; formatos inválidos responden 422.

### RF-04 Extracción de características con Claude vision (P0)

- Endpoint `POST /operations/{id}/extract`.
- Envía la imagen a Claude con un prompt que exige JSON con el esquema:

```json
{
  "nombre": "string",
  "marca": "string | null",
  "modelo": "string | null",
  "material": "string | null",
  "funcion": "string",
  "caracteristicas_tecnicas": ["string"],
  "texto_visible": "string | null",
  "keywords_busqueda": ["string"]
}
```

- Usa tool use / structured outputs para garantizar JSON válido; valida con Pydantic.
- Persiste el resultado en `operations.extraccion` y cambia `status = "extraida"`.
- Frontend: muestra los campos extraídos en tarjeta; permite editar `nombre` y `funcion` antes de clasificar.

**Aceptación:** con las fotos demo se obtiene JSON válido en ≥ 9 de 10 intentos; el error de Claude se muestra al usuario sin romper la UI.

### RF-05 Clasificación arancelaria (P0)

- Endpoint `POST /operations/{id}/classify`.
- Paso 1: búsqueda de candidatos en Mongo usando `keywords_busqueda` + `nombre`; máximo 15 resultados.
- Paso 2: Claude recibe la extracción y la lista de candidatos, y devuelve:

```json
{
  "fraccion": "string(8)",
  "nico": "string(2)",
  "confianza": 0.0,
  "justificacion": "string",
  "alternativas": [{ "fraccion": "string", "nico": "string", "razon": "string" }]
}
```

- La fracción elegida debe pertenecer a la lista de candidatos; si no, se reintenta una vez y luego se marca error.
- Persiste `candidatos`, `clasificacion`, `status = "clasificada"`.

**Aceptación:** para los 9 productos demo devuelve una fracción de la partida esperada; el smartwatch devuelve `confianza < 0.6`.

### RF-06 Revisión y confirmación (P0)

- Endpoint `PATCH /operations/{id}/classification` con `{ fraccion, nico, confirmada_por_usuario: true }`.
- Frontend: vista con la propuesta destacada, confianza como barra/porcentaje, justificación, lista de alternativas y buscador manual del catálogo (`GET /catalog/search`).
- Si `confianza < 0.6` se muestra alerta "Requiere revisión" y el botón "Continuar" queda deshabilitado hasta confirmar.

**Aceptación:** el usuario puede cambiar la fracción por cualquiera del catálogo y el cambio queda persistido con `confirmada_por_usuario = true`.

### RF-07 Datos de la operación (P0)

- Endpoint `PATCH /operations/{id}/details` con:

```json
{
  "valor_factura_usd": 0.0,
  "cantidad": 0,
  "pais_origen": "ISO-2",
  "tipo_cambio": 0.0,
  "importador": { "rfc": "string", "razon_social": "string" },
  "proveedor": { "nombre": "string", "pais": "ISO-2" }
}
```

- Valores por defecto precargados en el formulario (importador y proveedor mock, tipo de cambio fijo) para agilizar la demo.
- Validación: valor y cantidad > 0, país de origen requerido.

**Aceptación:** con los valores por defecto el formulario se completa en un clic.

### RF-08 Cálculo de contribuciones (P0)

- Servicio puro `calcular_contribuciones(valor_factura_usd, tipo_cambio, igi)`:

```
valor_aduana = valor_factura_usd × tipo_cambio
IGI          = igi × valor_aduana
DTA          = 0.008 × valor_aduana
IVA          = 0.16 × (valor_aduana + IGI + DTA)
total        = IGI + DTA + IVA
```

- Redondeo a 2 decimales; resultado persistido en `operations.liquidacion`.

**Aceptación:** pruebas unitarias con 3 casos conocidos.

### RF-09 Generación de pedimento PDF (P0)

- Endpoint `POST /operations/{id}/pedimento` genera el PDF con WeasyPrint desde plantilla HTML y lo guarda en `/data/pedimentos/<operation_id>.pdf`; `status = "pedimento_generado"`.
- Endpoint `GET /operations/{id}/pedimento` descarga el archivo.
- Contenido mínimo, inspirado en Anexo 22:
  - Encabezado: número de pedimento (mock), tipo de operación (IMP), clave (A1), aduana (mock), fecha.
  - Importador: RFC, razón social.
  - Proveedor: nombre, país.
  - Partida: fracción, NICO, descripción, UMT, cantidad, país de origen, valor aduana.
  - Liquidación: IGI, DTA, IVA, total.
  - Leyenda: "Documento simulado con fines de demostración".
- Frontend: botón "Generar pedimento" y vista previa/descarga.

**Aceptación:** el PDF se abre correctamente y refleja los mismos valores que la liquidación persistida.

### RF-10 Historial de operaciones (P1)

- Endpoint `GET /operations` con lista ordenada por fecha: miniatura, nombre extraído, fracción, estado, fecha.
- Endpoint `GET /operations/{id}` con el detalle completo.
- Frontend: tabla con acceso al detalle y descarga del PDF si existe.

**Aceptación:** una operación completada aparece en la lista con estado `pedimento_generado`.

### RF-11 Casos demo y README (P1)

- Carpeta `data/demo/` con las fotos de los productos listados en `vision.md`.
- README con instalación, variables de entorno (`ANTHROPIC_API_KEY`, `MONGO_URI`, `JWT_SECRET`), comando de seed, capturas del flujo y sección de alcance/disclaimer.

## 4. Modelo de datos

### `users`
```json
{ "_id": "", "email": "", "password_hash": "", "created_at": "" }
```

### `fracciones`
```json
{
  "fraccion": "85183001", "nico": "00",
  "descripcion": "", "descripcion_partida": "",
  "capitulo": "85", "umt": "Pza",
  "igi": 0.15, "iva": 0.16, "vigente": true
}
```

### `operations`
```json
{
  "_id": "", "user_id": "",
  "status": "creada | extraida | clasificada | pedimento_generado | error",
  "image_path": "",
  "extraccion": {},
  "candidatos": [],
  "clasificacion": { "fraccion": "", "nico": "", "confianza": 0, "justificacion": "", "alternativas": [], "confirmada_por_usuario": false },
  "datos_operacion": {},
  "liquidacion": {},
  "pedimento_pdf_path": null,
  "created_at": "", "updated_at": ""
}
```

## 5. API resumen

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Login, devuelve JWT |
| GET | `/catalog/search?q=` | Búsqueda de fracciones |
| POST | `/operations` | Subir imagen, crear operación |
| GET | `/operations` | Lista de operaciones |
| GET | `/operations/{id}` | Detalle |
| POST | `/operations/{id}/extract` | Extracción con Claude vision |
| POST | `/operations/{id}/classify` | Clasificación |
| PATCH | `/operations/{id}/classification` | Confirmar/corregir fracción |
| PATCH | `/operations/{id}/details` | Datos de la operación |
| POST | `/operations/{id}/pedimento` | Generar PDF |
| GET | `/operations/{id}/pedimento` | Descargar PDF |

## 6. Requerimientos no funcionales

- **Tiempo de respuesta:** extracción y clasificación < 20 s cada una; mostrar indicador de carga.
- **Configuración:** todo por variables de entorno; sin secretos en el repo.
- **Ejecución local:** `docker compose up` levanta api + mongo; `pnpm dev` levanta el frontend.
- **Manejo de errores:** los fallos del LLM se registran en `operations.status = "error"` con mensaje, y la UI permite reintentar.
- **Pruebas mínimas:** unitarias para cálculo de contribuciones y validación de esquemas de Claude.

## 7. Fuera de alcance

Regulaciones no arancelarias, tratados/preferencias, integración VUCEM o agente aduanal, firma electrónica, multiusuario y roles, OCR clásico, capítulos distintos a 84 y 85, múltiples partidas por pedimento, cupos y cuotas compensatorias.

## 8. Criterios de éxito del MVP

1. El flujo completo se ejecuta sin intervención técnica en menos de 2 minutos por producto.
2. Los 9 productos demo obtienen una fracción de la partida esperada y el smartwatch dispara revisión manual.
3. El pedimento PDF muestra fracción, NICO y liquidación consistentes con los datos capturados.
4. Un tercero puede levantar el proyecto siguiendo el README.

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El Excel del SAT cambia de formato | Fallback a JSON mock de ~50 fracciones |
| Claude devuelve una fracción fuera de candidatos | Validación + un reintento; luego estado error |
| Fotos ambiguas producen extracciones pobres | Segunda foto de etiqueta/caja; edición manual de nombre y función |
| WeasyPrint difícil de instalar en Docker | Imagen base con dependencias del sistema; alternativa `reportlab` |
