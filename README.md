# Asistente de clasificación arancelaria y pedimento

De la fotografía de un producto a una propuesta de **fracción arancelaria + NICO**
con nivel de confianza y justificación, y de ahí a un **pedimento simulado en PDF**
con el cálculo de contribuciones.

El sistema propone; la persona decide. Cuando la confianza cae por debajo del
umbral, no hay documento hasta que alguien confirma una fracción.

> **Disclaimer.** Proyecto de demostración. La clasificación es una *propuesta
> asistida*: la determinación final de la fracción y el NICO es responsabilidad
> del agente aduanal. El pedimento generado es un **documento simulado con fines
> de demostración**, no tiene validez legal, no fue transmitido a la VUCEM y no
> está firmado electrónicamente.

---

## El flujo

1. **Acceso** con el usuario que crea el seed.
2. **Nueva operación**: se sube la fotografía del producto (JPG o PNG, hasta 10 MB).
3. **Extracción**: Claude vision lee la imagen y devuelve nombre, marca, modelo,
   material, función, características técnicas, texto visible y palabras clave.
   El nombre y la función son editables antes de continuar.
4. **Clasificación en dos pasos**: se buscan hasta 15 fracciones candidatas en el
   catálogo con esas palabras clave, y Claude elige entre ellas devolviendo
   fracción, NICO, confianza, justificación y alternativas.
5. **Revisión**: se confirma la propuesta, se toma una alternativa, o se busca
   cualquier otra fracción del catálogo.
6. **Datos de la operación**: valor de factura, cantidad, país de origen, tipo de
   cambio, importador y proveedor, precargados desde la configuración.
7. **Pedimento**: se genera el PDF y se descarga.
8. **Historial**: la operación queda listada con su miniatura, fracción, estado y
   acceso al documento.

Capturas del flujo: [`docs/screenshots/`](docs/screenshots/).

---

## Puesta en marcha

### Requisitos

- **Docker Desktop** (levanta la API y MongoDB)
- **Node 20+** y **pnpm** (frontend)
- Una **API key de Anthropic**

### 1. Variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y define al menos:

| Variable | Para qué sirve |
|---|---|
| `ANTHROPIC_API_KEY` | Extracción y clasificación con Claude |
| `JWT_SECRET` | Firma de los tokens; usa 32 caracteres o más |
| `SEED_USER_EMAIL` / `SEED_USER_PASSWORD` | Credenciales del único usuario de la demo |

El resto tiene valores por defecto que funcionan tal cual. Ningún secreto se
versiona: `.env` está en `.gitignore`.

> **Dos detalles que cuestan una hora si se pasan por alto.**
>
> 1. **Guarda `.env` con saltos de línea LF, no CRLF.** Docker Compose no recorta
>    el `\r` final, así que una clave editada en un editor de Windows llega al
>    contenedor con un retorno de carro pegado y la API responde
>    `401 API key is invalid`.
> 2. **Después de cambiar `.env`, recrea el contenedor:**
>    ```bash
>    docker compose up -d --force-recreate api
>    ```
>    `docker compose restart` **no** sirve: reinicia el proceso reutilizando el
>    entorno con el que se creó el contenedor y nunca vuelve a leer `env_file`.

### 2. API y base de datos

```bash
docker compose up -d
```

MongoDB y la API en `http://localhost:8000`; documentación interactiva en
`http://localhost:8000/docs`.

### 3. Carga inicial del catálogo y del usuario

```bash
docker compose exec api python -m app.seed.seed
```

Idempotente: puedes volver a ejecutarlo cuando quieras.

```
INFO Fuente del catálogo: JSON curado (/data/catalog/tariff_items.json)
INFO Catálogo cargado: 63 fracciones
INFO Usuario listo: demo@aduana.mx
```

Comprueba que quedó cargado:

```bash
curl http://localhost:8000/health
# {"status":"ok","database":"connected","catalog_items":63}
```

### 4. Fotografías de demostración

```bash
python scripts/download_demo_images.py
```

Descarga las nueve fotos desde Wikimedia Commons según el manifiesto
`data/demo/sources.json`, que registra archivo, licencia, autoría y enlace de
cada una (todas CC0, CC BY o CC BY-SA). Las imágenes no se versionan.
`--list` muestra el manifiesto; `--force` vuelve a descargar todo.

Puedes sustituirlas por fotos propias conservando los mismos nombres de archivo.

### 5. Frontend

```bash
cd apps/web
pnpm install
pnpm dev
```

Abre `http://localhost:5173` e inicia sesión con las credenciales de `.env`
(por defecto `demo@aduana.mx` / `demo1234`). Vite hace proxy de `/api` hacia la
API, así que no hay nada más que configurar.

---

## Despliegue en un VPS con Dokploy

`docker-compose.prod.yml` describe el stack de producción: nginx sirve el SPA
compilado y hace proxy de `/api` hacia FastAPI en el mismo origen, de modo que
solo el servicio `web` queda publicado. La API y MongoDB no son alcanzables
desde fuera de la red de compose.

### 1. Preparar el servidor

Un VPS con Docker y Dokploy instalado (`curl -sSL https://dokploy.com/install.sh | sh`),
mínimo 2 GB de RAM: la compilación del frontend y WeasyPrint no caben cómodos en 1 GB.
Apunta un registro A del dominio a la IP antes de desplegar, porque Let's Encrypt
valida por HTTP.

### 2. Crear el proyecto

En Dokploy: **Project -> Create Service -> Compose**, conecta el repositorio,
rama `main`, y en *Compose Path* escribe `docker-compose.prod.yml`.

### 3. Variables de entorno

En la pestaña *Environment* pega el contenido de `.env.example` con los valores
reales, más el dominio. Cuatro entradas cambian respecto al entorno local:

```
APP_DOMAIN=tu-dominio.com
JWT_SECRET=<cadena aleatoria de 32+ caracteres>
SEED_USER_PASSWORD=<no dejes demo1234 en una URL pública>
CORS_ORIGINS=https://tu-dominio.com
```

`APP_DOMAIN` alimenta la regla de Traefik, así que el compose no lleva ningún
dominio escrito y el mismo archivo sirve en cualquier host. `MONGO_URI` lo fija
el compose; lo que pongas aquí se ignora. Los nombres de router y servicio de
Traefik (`tariff-web`) sí están en el archivo, y deben ser únicos en todo el
host de Dokploy.

### 4. Desplegar y sembrar

Pulsa **Deploy**. Cuando los tres servicios estén arriba, abre la terminal del
servicio `api` y ejecuta la semilla una vez:

```bash
python -m app.seed.seed
```

Verifica con `curl -s https://tu-dominio.com/api/health`, que debe responder
`{"status":"ok","database":"connected","catalog_items":63}`.

### Persistencia

Las fotografías subidas y los PDFs generados se montan en `../files/`, el
directorio que Dokploy conserva entre despliegues; el directorio del código se
borra en cada build. La base de datos vive en el volumen `mongo_data`.

---

## Resultados medidos

Corrida completa contra la API de Claude con las nueve fotografías de
`data/demo/`, modelo `claude-opus-5`:

| Producto | Fracción propuesta | Confianza | Partida esperada |
|---|---|---|---|
| Audífonos | 8518.30.01 | 0.82 | ✅ 8518 |
| Bocina bluetooth | 8518.22.01 | 0.55 · **revisión** | ✅ 8518 |
| Cargador USB | 8504.40.01 | 0.58 · **revisión** | ✅ 8504 |
| Cable USB | 8544.42.01 | 0.92 | ✅ 8544 |
| Mouse | 8471.60.02 | 0.97 | ✅ 8471 |
| Power bank | 8507.60.01 | 0.94 | ✅ 8507 |
| Smartphone | 8517.13.01 | 0.94 | ✅ 8517 |
| Router | 8517.62.02 | 0.95 | ✅ 8517 |
| Smartwatch | 8517.62.03 | 0.72–0.83 | caso ambiguo |

**8 de 8** productos con partida asignable cayeron en la esperada, en dos
corridas independientes. Las 18 extracciones devolvieron JSON válido. El flujo
completo —subir, extraer, clasificar, confirmar, capturar, generar el PDF—
tarda unos **30 segundos** por producto.

**Latencia.** Extracción 7–10 s; clasificación 10–17 s con
`CLAUDE_CLASSIFICATION_EFFORT=medium`. Con `high` la clasificación sube a
15–21 s y algunas llamadas rebasan el límite de 20 s del PRD. Con la extracción
fija y dos corridas por producto, `medium` y `high` eligieron **la misma
fracción con la misma confianza**, así que el valor por defecto es `medium`.

### Los casos de revisión manual son la bocina y el cargador, no el smartwatch

- La **bocina** es ambigua de forma reproducible (0.55–0.57): alterna entre
  8518.21 —un solo altavoz montado en su caja— y 8518.22 —varios altavoces en
  la misma caja—, una distinción que la fotografía no permite resolver.
- El **cargador** de la foto es un módulo empotrable de doble puerto USB, y el
  modelo razona explícitamente entre la partida 85.04 (convertidor estático) y
  la 85.36 (tomas de corriente) antes de quedarse en 0.58.
- El **smartwatch** clasifica con seguridad en 8517.62 citando la Nota 1 f) del
  Capítulo 91, con 9102.12.01 como primera alternativa en todas las corridas.
  `vision.md` lo anticipaba como el caso ambiguo, pero el tratamiento
  arancelario de los relojes con conectividad está más asentado de lo que ese
  documento suponía.

**La confianza varía ±0.1 entre corridas** con la misma entrada. Cerca del
umbral de 0.6 eso hace que un mismo producto pueda pedir revisión en una
corrida y no en la siguiente; es inherente al modelo, no un defecto del
sistema.

Durante esta medición se corrigió un defecto del catálogo curado: la fracción
del smartwatch describía «incluidos los relojes inteligentes (smartwatch)», lo
que le regalaba la respuesta al modelo. Las descripciones se mantienen ahora
genéricas, como en el texto oficial de la TIGIE.

`prd.md` y `vision.md` fueron actualizados con estos resultados: los criterios
de aceptación ahora piden que **al menos un** producto dispare revisión manual,
en lugar de nombrar al smartwatch.

---

## Cómo funciona

### Extracción y clasificación

Ambos pasos usan la salida estructurada del SDK (`messages.parse` con un modelo
Pydantic como `output_format`), de modo que un JSON malformado no es un modo de
falla que haya que manejar: la respuesta es una instancia validada o un error.

La clasificación ocurre en dos pasos:

1. **Candidatos.** Se buscan en Mongo hasta 15 fracciones usando las palabras
   clave que Claude generó durante la extracción, más el nombre del producto.
2. **Elección.** Claude recibe la mercancía y esa lista cerrada, y devuelve
   fracción, NICO, confianza, justificación y alternativas.

El modelo puede desobedecer, así que la fracción elegida **se verifica** contra
la lista. Si se sale, se reintenta una sola vez con un turno correctivo que
nombra explícitamente la fracción rechazada y enumera las válidas; si insiste,
la operación queda en `error` con el mensaje. El NICO se ajusta al que
efectivamente exista para esa fracción.

Cualquier falla del proveedor se persiste en la operación como
`status = "error"` con su mensaje antes de propagarse, que es lo que permite a
la interfaz ofrecer un reintento.

### Revisión, liquidación y pedimento

**Revisión.** El usuario confirma la propuesta, elige una de las alternativas, o
busca cualquier otra fracción del catálogo. La fracción se valida contra el
catálogo antes de aceptarse, porque de ahí sale el IGI que determina lo que se
paga: un código inventado rompería la liquidación.

Cuando el usuario elige una fracción distinta, la propuesta original se conserva
en `original_tariff_code`. Ese campo no está en el modelo del PRD, pero sin él
el expediente pierde justo lo que la demo quiere mostrar: qué propuso el sistema
y qué decidió la persona. La liquidación previa se descarta, porque se calculó
con el IGI de la fracción anterior.

**Liquidación.** Servicio puro, sin E/S ni estado. La aritmética corre en
`Decimal` porque 0.008 y 0.16 no son representables en punto flotante binario.
Cada importe se redondea a centavos conforme se produce y los siguientes derivan
de los ya redondeados: cuesta una fracción de centavo de precisión y compra algo
que en un documento impreso vale más, que las cifras mostradas sumen exactamente
el total mostrado. La tasa de IGI se toma del catálogo, nunca de la petición.

```
valor_aduana = valor_factura_usd × tipo_cambio
IGI          = igi × valor_aduana
DTA          = 0.008 × valor_aduana          (8 al millar)
IVA          = 0.16 × (valor_aduana + IGI + DTA)
total        = IGI + DTA + IVA
```

**Pedimento.** Plantilla Jinja2 con layout inspirado en el Anexo 22, renderizada
por WeasyPrint detrás de la interfaz `PdfRenderer`. El número de pedimento se
deriva del identificador de la operación, de modo que volver a generar el
documento no cambia el número impreso en él.

Si la clasificación todavía requiere revisión manual, el endpoint responde
**409**: por debajo del umbral no hay documento sin que una persona lo asuma.

### El catálogo de fracciones

El seed elige la fuente automáticamente:

1. **Excel oficial** — si existen `data/c_FraccionArancelaria.xlsx` (catálogo del
   SAT) y `data/snice_aranceles.xlsx` (aranceles de SNICE), los usa: filtra los
   capítulos 84 y 85 y cruza el IGI por fracción. Las rutas se configuran con
   `SAT_EXCEL_PATH` y `SNICE_EXCEL_PATH`.
2. **JSON curado** — si no están, usa `data/catalog/tariff_items.json`: 63
   fracciones de los capítulos 84 y 85 seleccionadas a mano para cubrir los nueve
   productos de la demo, más dos del capítulo 91 que hacen posible el caso
   ambiguo del smartwatch. Las tasas de IGI de este archivo son valores de
   referencia para la demostración.

Ambas fuentes implementan la misma interfaz `CatalogSource`, así que agregar un
tercer origen no obliga a tocar el script de carga.

---

## Arquitectura

```
apps/api/app/
├── main.py           Fábrica de la aplicación, ciclo de vida, manejo de errores
├── core/             Configuración, seguridad (bcrypt + JWT), inyección de dependencias
├── domain/           Modelos, enumeraciones y excepciones de negocio
├── repositories/     Contratos abstractos + implementaciones Mongo y en memoria
├── integrations/llm/ Contratos de extracción y clasificación + cliente de Claude
├── services/         Casos de uso, cálculo de contribuciones, PDF y almacenamiento
├── api/              DTOs y routers HTTP
└── seed/             Carga inicial y sus fuentes de catálogo

apps/web/src/
├── api/              Cliente HTTP y endpoints tipados
├── auth/             Sesión y guardia de rutas
├── hooks/            Configuración del servidor y flujo de la operación
├── components/       Campo de pedimento, medidor de confianza, paneles del flujo
└── pages/            Acceso, nueva operación, detalle e historial
```

Cuatro reglas gobiernan el backend:

1. **Los routers no contienen lógica.** Traducen HTTP ↔ DTO y delegan; el manejo
   global de `DomainError` decide el código de estado.
2. **Los servicios dependen de abstracciones**, nunca de PyMongo ni del SDK de
   Anthropic. `core/dependencies.py` es el único módulo que conoce las
   implementaciones concretas.
3. **El dominio ignora HTTP y MongoDB.** Los DTOs de la API viven aparte.
4. **El cálculo de contribuciones es una función pura**, sin estado ni E/S.

Cada repositorio tiene una implementación en memoria, y tanto el extractor como
el clasificador y el renderizador de PDF tienen dobles: eso es lo que permite
probar los casos de uso sin base de datos, sin API key y sin WeasyPrint.

El código, los métodos, las rutas y los campos JSON están en inglés; la interfaz
se presenta en español. Se conservan sin traducir los términos propios del
régimen aduanero mexicano: *pedimento*, *NICO*, *IGI*, *DTA*, *IVA*, *UMT* y
*RFC*.

### Decisiones que se apartan de lo escrito en el PRD

| Decisión | Motivo |
|---|---|
| PyMongo `AsyncMongoClient` en lugar de Motor | Motor quedó deprecado en 2025; la API es prácticamente idéntica |
| `bcrypt` directo en lugar de passlib | El backend bcrypt de passlib rompe con las versiones modernas |
| `PATCH /operations/{id}/extraction` | RF-04 exige corregir nombre y función; la corrección tiene que persistirse |
| `GET /config` | Para que el umbral y los valores por defecto vivan en `.env` y no repetidos en el frontend |
| Campo `original_tariff_code` | Conserva qué propuso el modelo cuando la persona elige otra fracción |

---

## API

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Devuelve un JWT válido 8 horas |
| GET | `/auth/me` | Identidad del portador del token |
| GET | `/catalog/search?q=` | Busca hasta 15 fracciones por relevancia |
| POST | `/operations` | Sube la fotografía y abre la operación |
| GET | `/operations` | Historial de operaciones |
| GET | `/operations/{id}` | Detalle completo |
| GET | `/operations/{id}/image` | Devuelve la fotografía almacenada |
| POST | `/operations/{id}/extract` | Extracción con Claude vision |
| PATCH | `/operations/{id}/extraction` | Corrige el nombre y la función |
| POST | `/operations/{id}/classify` | Busca candidatos y clasifica |
| PATCH | `/operations/{id}/classification` | Confirma o corrige la fracción |
| PATCH | `/operations/{id}/details` | Datos de la operación y liquidación |
| POST | `/operations/{id}/pedimento` | Genera el PDF |
| GET | `/operations/{id}/pedimento` | Descarga el PDF |
| GET | `/config` | Umbral de revisión y valores por defecto del formulario |
| GET | `/health` | Estado del servicio y número de fracciones cargadas |

Todos los endpoints salvo `/auth/login` y `/health` exigen la cabecera
`Authorization: Bearer <token>`; sin ella responden **401**.

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@aduana.mx","password":"demo1234"}' | jq -r .access_token)

curl -s -G -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "q=audífonos" http://localhost:8000/catalog/search
```

---

## Pruebas

```bash
docker compose exec api pytest
```

119 pruebas. Corren dentro del contenedor, que ya trae las dependencias de
desarrollo, y no necesitan MongoDB, API key ni WeasyPrint: usan los repositorios
en memoria y los dobles del extractor, el clasificador y el renderizador.

Si prefieres ejecutarlas en tu máquina, instala solo lo necesario y evita así las
dependencias de sistema de WeasyPrint:

```bash
cd apps/api
python -m venv .venv
./.venv/Scripts/pip install fastapi pydantic-settings PyJWT bcrypt email-validator pymongo openpyxl pillow jinja2 anthropic pytest pytest-asyncio
./.venv/Scripts/python -m pytest
```

---

## Alcance

**Incluido:** autenticación con un usuario sembrado, subida de foto, extracción
con Claude vision, clasificación asistida sobre el catálogo de los capítulos 84 y
85, revisión y corrección humana, captura de los datos de la operación, cálculo
simplificado de contribuciones, pedimento simulado en PDF e historial.

**Fuera de alcance:** regulaciones y restricciones no arancelarias (NOM,
permisos, padrones), preferencias arancelarias por tratados, integración con
VUCEM o con un agente aduanal, firma electrónica, multiusuario y roles, OCR
clásico, capítulos distintos a 84 y 85, múltiples partidas por pedimento, cupos y
cuotas compensatorias.
