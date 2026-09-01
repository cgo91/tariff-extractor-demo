# Asistente de clasificación arancelaria y pedimento

De la fotografía de un producto a una propuesta de **fracción arancelaria + NICO**
con nivel de confianza y justificación, y de ahí a un **pedimento simulado en PDF**
con el cálculo de contribuciones.

Proyecto de demostración. La clasificación es una *propuesta asistida*: la
determinación final de la fracción y el NICO es responsabilidad del agente
aduanal. El pedimento generado es un **documento simulado con fines de
demostración** y no tiene validez legal.

---

## Estado de la construcción

| Fase | Alcance | Estado |
|---|---|---|
| 1 | Esqueleto de API y UI, autenticación JWT, catálogo TIGIE y su carga inicial | ✅ Completa |
| 2 | Subida de foto, extracción con Claude vision, clasificación en dos pasos | ✅ Completa |
| 3 | Datos de la operación, cálculo de contribuciones, pedimento PDF | ⏳ Pendiente |
| 4 | Historial, casos demo, documentación final | ⏳ Pendiente |

---

## Requisitos

- **Docker Desktop** (levanta la API y MongoDB)
- **Node 20+** y **pnpm** (frontend)
- Una **API key de Anthropic** (necesaria a partir de la fase 2)

---

## Puesta en marcha

### 1. Variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y define al menos:

| Variable | Para qué sirve |
|---|---|
| `ANTHROPIC_API_KEY` | Extracción y clasificación con Claude (fase 2) |
| `JWT_SECRET` | Firma de los tokens; usa 32 caracteres o más |
| `SEED_USER_EMAIL` / `SEED_USER_PASSWORD` | Credenciales del único usuario de la demo |

El resto tiene valores por defecto que funcionan tal cual. Ningún secreto se
versiona: `.env` está en `.gitignore`.

### 2. API y base de datos

```bash
docker compose up -d
```

Levanta MongoDB y la API en `http://localhost:8000` (documentación interactiva
en `http://localhost:8000/docs`).

### 3. Carga inicial del catálogo y del usuario

```bash
docker compose exec api python -m app.seed.seed
```

El script es idempotente: puedes volver a ejecutarlo cuando quieras.

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

### 4. Frontend

```bash
cd apps/web
pnpm install
pnpm dev
```

Abre `http://localhost:5173` e inicia sesión con las credenciales de `.env`
(por defecto `demo@aduana.mx` / `demo1234`). Vite hace proxy de `/api` hacia la
API, así que no necesitas configurar nada más.

---

## Extracción y clasificación

Ambos pasos usan la salida estructurada del SDK (`messages.parse` con un modelo
Pydantic como `output_format`), de modo que un JSON malformado no es un modo de
falla que haya que manejar: la respuesta es una instancia validada o un error.

La clasificación ocurre en dos pasos, como pide RF-05:

1. **Candidatos.** Se buscan en Mongo hasta 15 fracciones usando las palabras
   clave que Claude generó durante la extracción, más el nombre del producto.
2. **Elección.** Claude recibe la mercancía y esa lista cerrada, y devuelve
   fracción, NICO, confianza, justificación y alternativas.

El modelo puede desobedecer, así que la fracción elegida **se verifica** contra
la lista. Si se sale, se reintenta una sola vez con un turno correctivo que
nombra explícitamente la fracción rechazada y enumera las válidas; si insiste,
la operación queda en `error` con el mensaje. El NICO se ajusta al que
efectivamente exista para esa fracción.

Cuando la confianza queda por debajo de `CONFIDENCE_THRESHOLD` (0.6), la
respuesta marca `requires_review` y la interfaz exige confirmación manual.

Cualquier falla del proveedor se persiste en la operación como
`status = "error"` con su mensaje antes de propagarse, que es lo que permite a
la interfaz ofrecer un reintento.

> Estos dos endpoints son los únicos que necesitan `ANTHROPIC_API_KEY`. Sin
> ella responden **502** con un mensaje explicando qué falta.

---

## El catálogo de fracciones

El seed elige la fuente automáticamente:

1. **Excel oficial** — si existen `data/c_FraccionArancelaria.xlsx` (catálogo del
   SAT) y `data/snice_aranceles.xlsx` (aranceles de SNICE), los usa: filtra los
   capítulos 84 y 85 y cruza el IGI por fracción. Las rutas se configuran con
   `SAT_EXCEL_PATH` y `SNICE_EXCEL_PATH`.
2. **JSON curado** — si no están, usa `data/catalog/tariff_items.json`: 63
   fracciones de los capítulos 84 y 85 seleccionadas a mano para cubrir los nueve
   productos de la demo, más dos del capítulo 91 que hacen posible el caso
   ambiguo del smartwatch (reloj de pulsera contra aparato de comunicación).
   Las tasas de IGI de este archivo son valores de referencia para la
   demostración.

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
├── services/         Casos de uso (autenticación, catálogo, …)
├── api/              DTOs y routers HTTP
└── seed/             Carga inicial y sus fuentes de catálogo
```

Cuatro reglas gobiernan el backend:

1. **Los routers no contienen lógica.** Traducen HTTP ↔ DTO y delegan; el manejo
   global de `DomainError` decide el código de estado.
2. **Los servicios dependen de abstracciones**, nunca de PyMongo ni del SDK de
   Anthropic. `core/dependencies.py` es el único módulo que conoce las
   implementaciones concretas.
3. **El dominio ignora HTTP y MongoDB.** Los DTOs de la API viven aparte.
4. **El cálculo de contribuciones es una función pura**, sin estado ni E/S.

Cada repositorio tiene una implementación en memoria, que es lo que permite
probar los servicios sin base de datos.

El código, los métodos, las rutas y los campos JSON están en inglés; la interfaz
se presenta en español. Se conservan sin traducir los términos propios del
régimen aduanero mexicano: *pedimento*, *NICO*, *IGI*, *DTA*, *IVA*, *UMT* y
*RFC*.

---

## API disponible

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
| GET | `/health` | Estado del servicio y número de fracciones cargadas |

`PATCH /operations/{id}/extraction` no aparece en la tabla del PRD, pero RF-04
pide que el usuario pueda corregir el nombre y la función antes de clasificar, y
esa corrección tiene que persistirse en algún lado.

Todos los endpoints salvo `/auth/login` y `/health` exigen la cabecera
`Authorization: Bearer <token>`; sin ella responden **401**.

Ejemplo:

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

La suite corre dentro del contenedor, que ya trae las dependencias de
desarrollo. No necesita MongoDB ni API key: usa los repositorios en memoria.

Si prefieres ejecutarla en tu máquina, instala solo lo necesario para las
pruebas y evita así las dependencias de sistema de WeasyPrint:

```bash
cd apps/api
python -m venv .venv
./.venv/Scripts/pip install fastapi pydantic-settings PyJWT bcrypt email-validator pymongo openpyxl pytest pytest-asyncio
./.venv/Scripts/python -m pytest
```

---

## Fuera de alcance

Regulaciones y restricciones no arancelarias (NOM, permisos, padrones),
preferencias por tratados, integración con VUCEM o con un agente aduanal, firma
electrónica, multiusuario y roles, OCR clásico, capítulos distintos a 84 y 85, y
múltiples partidas por pedimento.
