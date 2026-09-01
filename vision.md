# Visión del MVP — Asistente de clasificación arancelaria y pedimento

## 1. Propósito

Demostrar, de punta a punta, que a partir de la **foto de un producto físico** se puede:

1. Extraer sus características con un LLM (Claude vision).
2. Proponer la **fracción arancelaria + NICO** correspondiente en la TIGIE, con nivel de confianza y justificación.
3. Generar un **pedimento simulado en PDF** con layout inspirado en el Anexo 22 y cálculo de contribuciones.

Es un proyecto de demostración para entrevista, de uso interno. La prioridad es que el flujo completo funcione y se entienda, no la cobertura ni la exactitud legal.

**Disclaimer del producto:** la clasificación es una *propuesta asistida*. La determinación final de fracción y NICO es responsabilidad del agente aduanal.

## 2. Contexto de datos públicos

No existe una API pública oficial para clasificar mercancías ni para generar pedimentos. Lo que sí existe y se usa como semilla:

| Fuente | Qué aporta | Uso en el MVP |
|---|---|---|
| Catálogo SAT `c_FraccionArancelaria` (Excel + XSD) | Fracciones de 8 dígitos, NICO, descripción, vigencias | Semilla principal de la colección `fracciones` |
| SNICE (Secretaría de Economía) — descarga de LIGIE 2022 | Aranceles (IGI), cupos, niveles arancelarios | Cruce para obtener el arancel por fracción |
| VUCEM Clasificador | Herramienta web interactiva | Solo referencia manual; sin API |
| SIAVI Data | Datos abiertos de comercio exterior por fracción | Referencia, no se integra |
| Anexo 22 de las RGCE | Instructivo de llenado del pedimento | Base para el layout del PDF |

Todo lo que no es descargable se **simula** con datos mock en MongoDB.

## 3. Giro elegido

**Electrónica de consumo y periféricos de cómputo — capítulos 84 y 85 de la TIGIE.**

Razones:
- Los productos se pueden fotografiar en casa.
- Las fracciones están bien diferenciadas y tienen NICO reales.
- Hay casos genuinamente ambiguos que obligan a la revisión humana (ver más
  abajo: se anticipó el smartwatch y resultaron ser la bocina y el cargador).

### Productos demo

Subpartida SA de 6 dígitos como referencia; la fracción de 8 dígitos y el NICO se obtienen del catálogo cargado.

| Producto | Subpartida SA | Nota |
|---|---|---|
| Audífonos bluetooth | 8518.30 | |
| Bocina bluetooth | 8518.21 / 8518.22 | **Caso ambiguo confirmado**: un altavoz contra varios en la misma caja |
| Cargador USB de pared | 8504.40 | **Caso ambiguo confirmado**: convertidor estático contra toma de corriente (85.36) |
| Cable USB con conectores | 8544.42 | |
| Mouse / teclado | 8471.60 | |
| Power bank | 8507.60 | |
| Smartphone | 8517.13 | |
| Router | 8517.62 | |
| Smartwatch | 8517.62 | Se anticipó ambiguo; resultó ser el caso seguro |

### Casos ambiguos: lo previsto y lo medido

Este documento anticipaba el **smartwatch** como el caso que dispararía la
revisión humana, por la competencia entre la partida 85.17 y el capítulo 91.
La medición contra el sistema construido dice otra cosa.

El smartwatch clasifica **con seguridad** en 8517.62 (confianza 0.72–0.83 en
todas las corridas), citando la Nota 1 f) del Capítulo 91, que excluye de ese
capítulo los aparatos que, aunque indiquen la hora, son aparatos de
telecomunicación. El argumento es correcto: el tratamiento de los relojes con
conectividad está más asentado de lo que este documento suponía. La fracción
9102.12.01 aparece como primera alternativa en todas las corridas, así que la
competencia se muestra, pero no está reñida.

Los casos que sí obligan a revisión aparecieron solos, y son mejores porque la
ambigüedad es visual y no jurídica:

- **Bocina bluetooth** (confianza 0.55–0.57, reproducible): la fotografía no
  permite saber si la caja lleva un solo altavoz —8518.21— o varios —8518.22—.
  El modelo alterna entre ambas entre corridas.
- **Cargador USB** (confianza 0.58–0.62): la fotografía es un módulo empotrable
  de doble puerto USB, y el modelo razona explícitamente entre la partida 85.04
  como convertidor estático y la 85.36 como toma de corriente.

La confianza varía ±0.1 entre corridas con la misma entrada, así que cerca del
umbral de 0.6 un producto puede pedir revisión en una corrida y no en la
siguiente. Es una propiedad del modelo, no un defecto del sistema.

### Cómo obtener las imágenes

- Fotografiar con celular sobre fondo liso y buena luz.
- Tomar una segunda foto de la etiqueta o caja con marca y modelo (mejora la extracción).
- Complemento con licencia libre: Unsplash, Pexels, Pixabay (`headphones product photo`, `usb charger`, etc.).

## 4. Catálogo en MongoDB

Script `seed.py`:

1. Lee el Excel `c_FraccionArancelaria` del SAT.
2. Filtra capítulos 84 y 85.
3. Cruza con el Excel de aranceles de SNICE para obtener el IGI.
4. Inserta en la colección `fracciones` y crea índice de texto sobre `descripcion`.

Documento:

```json
{
  "fraccion": "85183001",
  "nico": "00",
  "descripcion": "...",
  "descripcion_partida": "...",
  "capitulo": "85",
  "umt": "Pza",
  "igi": 0.15,
  "iva": 0.16,
  "vigente": true
}
```

**Fallback:** si el parseo del Excel se complica, JSON mock de ~50 fracciones de los capítulos 84 y 85, curado a mano.

## 5. Alcance funcional

### In scope

1. **Auth JWT básico** — un usuario sembrado, login, token en header `Authorization`. Sin registro ni refresh tokens.
2. **Subida de foto** — JPG/PNG (convertir HEIC). Archivo en disco, referencia en Mongo.
3. **Extracción con Claude vision** — salida JSON estructurada: `nombre`, `marca`, `modelo`, `material`, `funcion`, `caracteristicas_tecnicas`, `texto_visible`.
4. **Clasificación en dos pasos**
   - Búsqueda de candidatos en Mongo (índice de texto + keywords generadas por Claude) → top 10–15.
   - Claude elige `fraccion` + `nico` y devuelve `confianza` (0–1) y `justificacion` citando Reglas Generales 1 y 6.
   - Structured outputs / tool use para garantizar JSON válido.
5. **Pantalla de revisión** — producto, candidatos, confianza, justificación. El usuario confirma o corrige manualmente.
6. **Formulario mínimo de operación** — valor factura (USD), cantidad, país de origen, tipo de cambio, importador (RFC mock).
7. **Pedimento PDF** — layout inspirado en Anexo 22 generado con WeasyPrint desde plantilla HTML:
   - Encabezado (aduana, tipo de operación, clave de pedimento)
   - Datos del importador y del proveedor
   - Partida(s): fracción, NICO, descripción, UMT, cantidad, valor
   - Liquidación
8. **Historial de operaciones** con estado: `extraida` → `clasificada` → `pedimento_generado`.

### Cálculo de contribuciones (simplificado)

```
valor_aduana = valor_factura_usd × tipo_cambio
IGI          = igi × valor_aduana
DTA          = 0.008 × valor_aduana          (8 al millar)
IVA          = 0.16 × (valor_aduana + IGI + DTA)
total        = IGI + DTA + IVA
```

### Out of scope

- Regulaciones y restricciones no arancelarias (NOMs, permisos, padrones)
- Preferencias arancelarias por tratados (T-MEC u otros)
- Integración con VUCEM, agente aduanal o firma electrónica
- Multiusuario, roles, registro de cuentas
- OCR clásico (Tesseract u otros)
- Capítulos de la TIGIE distintos a 84 y 85
- Múltiples partidas complejas, cupos, cuotas compensatorias

## 6. Stack y arquitectura

| Capa | Tecnología |
|---|---|
| Frontend | React + Vite + Tailwind |
| Backend | FastAPI (Python) |
| Base de datos | MongoDB (Motor o Beanie) |
| LLM | Claude API (SDK `anthropic`), modelo con visión |
| PDF | WeasyPrint desde plantilla HTML |
| Auth | JWT (`python-jose` o `PyJWT`) |
| Infra local | Docker Compose (api + mongo); front con Vite dev server |

### Estructura del repo

```
/
├── apps/
│   ├── web/          # React + Vite + Tailwind
│   └── api/          # FastAPI
│       ├── routers/  # auth, operations, classification, pedimentos
│       ├── services/ # claude, catalog_search, pedimento_pdf
│       ├── models/
│       └── seed.py
├── data/             # excel SAT/SNICE, mock JSON
├── docker-compose.yml
└── README.md
```

### Vistas del frontend

1. Login
2. Nueva operación (subir foto → ver extracción)
3. Revisión de clasificación + formulario de operación
4. Historial

### Colecciones

- `users` — `{ email, password_hash }`
- `fracciones` — ver sección 4
- `operations` — `{ status, image_path, extraccion, candidatos[], clasificacion, datos_operacion, pedimento_pdf_path, created_at }`

## 7. Plan de construcción

| Fase | Entregable |
|---|---|
| 1 | Seed del catálogo, auth JWT, esqueleto de UI y API |
| 2 | Upload + extracción con Claude vision + clasificación con candidatos (núcleo, mayor esfuerzo) |
| 3 | Formulario de operación + generación del pedimento PDF |
| 4 | Casos demo con fotos reales (incluido el ambiguo), README con capturas, limpieza |

## 8. Qué debe lucir en la demo

- Seed con **datos reales del SAT/SNICE**, no inventados.
- Salida **estructurada y validada** de Claude (JSON garantizado).
- **Confianza + revisión humana**: el sistema propone, la persona decide. Y la
  ambigüedad no está guionada: la bocina y el cargador caen bajo el umbral por
  sí solos, y el expediente conserva qué propuso el modelo y qué decidió la
  persona.
- Pedimento con **cálculos correctos** aunque el layout sea aproximado.
- Alcance y disclaimer claramente documentados.
