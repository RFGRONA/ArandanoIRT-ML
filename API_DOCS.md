# 📖 Documentación de la API — ArandanoIRT-ML

Este documento describe los endpoints disponibles en el microservicio RAG y cómo el monolito de .NET se integra con ellos.

## Base URL

El servicio se expone típicamente en `http://localhost:8000` o donde se decida desplegar (ej. `http://ai-service:8000`).

Documentación interactiva Swagger: `http://localhost:8000/docs`.

## Autenticación

Todas las peticiones a la API (excepto `/health`) deben incluir el header:
```
X-API-KEY: <tu_clave_secreta>
```
Esta clave debe coincidir con la definida en el `.env` del microservicio (`X_API_KEY`).

---

## Endpoints

### 1. `GET /health`

Verifica que el microservicio esté activo y listo para recibir consultas.

**Autenticación**: No requerida.

**Respuesta (200 OK):**
```json
{
  "status": "ok",
  "message": "API RAG funcionando correctamente."
}
```

> **Uso desde .NET**: El monolito llama a este endpoint desde `RagService.IsAliveAsync()` para mostrar el estado del microservicio en la pantalla de Configuraciones del Asistente IA.

---

### 2. `POST /chat`

Realiza una consulta a la IA usando Retrieval-Augmented Generation (RAG). El sistema enruta automáticamente la consulta al modelo más adecuado según su complejidad.

**Headers:**
- `X-API-KEY: <secret>`
- `Content-Type: application/json`

**Body:**
```json
{
  "question": "¿Cuáles son los niveles óptimos de humedad para arándanos biloxi?",
  "iot_context": "Datos térmicos (últimas 24h): Mín=18.2°C, Máx=32.5°C, Prom=24.1°C ...",
  "expertise_level": "AGRONOMO"
}
```

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `question` | String | ✅ | Pregunta del usuario. |
| `iot_context` | String | ❌ | Contexto de sensores IoT generado por el controlador .NET cuando el usuario selecciona una planta. Si está vacío, **no se consultan las bitácoras**, solo los papers. |
| `expertise_level` | String | ❌ | Nivel de tecnicismo: `"AGRICULTOR"` (sencillo) o `"AGRONOMO"` (experto). Default: `"AGRONOMO"`. |

**Comportamiento del Router:**
- El router (`gemini-2.5-flash-lite`) evalúa la complejidad de la pregunta.
- Consultas simples → `gemini-2.5-flash-lite` (más rápido, menor costo).
- Consultas complejas → `gemini-2.5-flash` (mayor capacidad de razonamiento).

**Comportamiento de la Recuperación:**
- **Sin `iot_context`**: Solo busca en la colección `papers_expertos` (PDFs/literatura).
- **Con `iot_context`**: Busca en `papers_expertos` (5 docs) **y** en `bitacoras_usuario` (3 docs).

**Respuesta Exitosa (200 OK):**
```json
{
  "answer": "El rango óptimo de humedad para arándanos biloxi...",
  "model_used": "gemini-2.5-flash",
  "complexity": "COMPLEJA",
  "sources": [
    {
      "source": "Manual de manejo agronómico del arándano.pdf",
      "page": 45,
      "observation_id": null
    },
    {
      "source": "Bitácora",
      "page": null,
      "observation_id": "7"
    }
  ]
}
```

| Campo de respuesta | Descripción |
|---|---|
| `answer` | Respuesta generada por el modelo de IA. |
| `model_used` | Modelo de Gemini utilizado (`gemini-2.5-flash` o `gemini-2.5-flash-lite`). |
| `complexity` | Clasificación del router (`SIMPLE` o `COMPLEJA`). |
| `sources` | Lista de fuentes citadas. Para PDFs: `source` = nombre del archivo, `page` = número de página. Para bitácoras: `source` = "Bitácora", `observation_id` = ID de la observación en la BD de .NET. |

> **Nota**: Las fuentes se deduplican automáticamente. Si un PDF aparece en múltiples chunks recuperados, solo se lista una vez por página.

---

### 3. `POST /ingest-logs`

Envía una o más observaciones (bitácoras de usuario) al microservicio para ser vectorizadas en lote e integradas en el conocimiento del RAG.

**Headers:**
- `X-API-KEY: <secret>`
- `Content-Type: application/json`

**Body:**
```json
{
  "logs": [
    {
      "observation_id": "7",
      "text_content": "El lote 4 presenta hojas marchitas en las puntas. Se aplicó riego de emergencia.",
      "metadata": {
        "user_id": "123",
        "crop_id": "Lote-4"
      }
    },
    {
      "observation_id": "8",
      "text_content": "Las hojas empezaron a tener un color verde claro en los bordes.",
      "metadata": {
        "user_id": "123",
        "crop_id": "Lote-4"
      }
    }
  ]
}
```

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `logs` | Array | ✅ | Lista de bitácoras a vectorizar. |
| `logs[].observation_id` | String | ✅ | ID único de la observación (coincide con el GUID de la BD SQL de .NET). |
| `logs[].text_content` | String | ✅ | Texto completo de la observación/bitácora. |
| `logs[].metadata` | Object | ❌ | Metadatos adicionales (user_id, crop_id, etc.). Se almacenan junto al embedding. |

**Respuesta Exitosa (200 OK):**
```json
{
  "status": "success",
  "message": "2 logs vectorizados correctamente."
}
```

> **Flujo automático**: El monolito .NET ejecuta un `BackgroundService` que revisa periódicamente las observaciones con `IsVectorized = false`, las agrupa en lotes y las envía a este endpoint. Una vez vectorizadas, se marcan como `IsVectorized = true` en la BD SQL.

---

### 4. `POST /update-papers`

Reemplaza la colección de `papers_expertos` subiendo un archivo `.zip` que contiene la base de datos ChromaDB generada por `setup_database.py` y empaquetada con `export_db.sh`.

> **Importante**: Este endpoint **solo reemplaza la colección de papers**. Las bitácoras (`bitacoras_usuario`) no se ven afectadas.

**Headers:**
- `X-API-KEY: <secret>`
- `Content-Type: multipart/form-data`

**Body:**
- Form-data key: `file`
- Form-data value: `chroma_db.zip` (Archivo)

**Estructura esperada del ZIP:**
```
chroma_db.zip
└── chroma_db/
    └── papers/
        ├── chroma.sqlite3
        └── <uuid>/
            ├── data_level0.bin
            ├── header.bin
            ├── length.bin
            ├── link_lists.bin
            └── index_metadata.pickle
```

El endpoint acepta dos estructuras válidas:
- `chroma_db/papers/chroma.sqlite3` (resultado de `export_db.sh`)
- `papers/chroma.sqlite3` (si se zipeó solo la carpeta papers)

**Validaciones de seguridad:**
- Rechaza archivos que no sean `.zip`.
- Detecta y bloquea symlinks en el ZIP (prevención de ataques).
- Detecta y bloquea path traversal / Zip Slip.

**Respuesta Exitosa (200 OK):**
```json
{
  "status": "success",
  "message": "Base de datos de papers actualizada exitosamente."
}
```

---

### 5. `GET /export-db`

Descarga la base de datos ChromaDB completa (papers + bitácoras) en formato `.zip` para respaldos.

**Headers:**
- `X-API-KEY: <secret>`

**Respuesta Exitosa (200 OK):**
Descarga un archivo binario `chroma_db_export.zip`.

---

### 6. `POST /update-api-key`

Actualiza y persiste la clave de la API de Google Gemini en el archivo `.env`.

> **Nota de Seguridad**: Este endpoint sobrescribe las credenciales globales en disco. Se **requiere reiniciar el servicio** para que la nueva llave tome efecto de forma segura.

**Headers:**
- `X-API-KEY: <secret>`
- `Content-Type: application/json`

**Body:**
```json
{
  "api_key": "AIzaSyAZ..."
}
```

**Respuesta (200 OK):**
```json
{
  "status": "success",
  "message": "API Key de Gemini actualizada y persistida correctamente. Reinicie el servicio para aplicar el cambio de forma segura."
}
```

---

## Flujo de Integración con .NET

### Vectorización automática de bitácoras

```
┌──────────────────────────────────────────────────────────────────┐
│ BackgroundService (.NET)                                         │
│                                                                  │
│ 1. Consulta observaciones WHERE IsVectorized = false             │
│ 2. Agrupa en lotes (máx. 50 por request)                        │
│ 3. Envía POST /ingest-logs con el lote                          │
│ 4. Si HTTP 200 → Marca IsVectorized = true en BD SQL            │
│ 5. Ejecuta periódicamente (configurable)                        │
└──────────────────────────────────────────────────────────────────┘
```

### Consulta con contexto IoT

```
┌──────────────────────────────────────────────────────────────────┐
│ AiAssistantController (.NET)                                     │
│                                                                  │
│ 1. Usuario envía mensaje en el chat                              │
│ 2. Si hay planta seleccionada:                                   │
│    a. Consulta datos térmicos (mín, máx, promedio)               │
│    b. Consulta datos ambientales (luz, temp ciudad, hum ciudad)  │
│    c. Calcula climas predominantes                               │
│    d. Agrupa datos en intervalos (2h o 4-6h según el periodo)    │
│    e. Construye string iot_context                               │
│ 3. Envía POST /chat con question + iot_context + expertise_level │
│ 4. Renderiza respuesta con fuentes en el frontend                │
└──────────────────────────────────────────────────────────────────┘
```

### Actualización de papers desde la UI

```
┌──────────────────────────────────────────────────────────────────┐
│ Settings (Admin Only)                                            │
│                                                                  │
│ 1. Admin sube chroma_db.zip desde Configuraciones del Asistente  │
│ 2. .NET valida archivo y reenvía a POST /update-papers           │
│ 3. Microservicio extrae, valida y reemplaza solo papers          │
│ 4. Recarga colecciones en memoria                                │
│ 5. Bitácoras NO se afectan                                       │
└──────────────────────────────────────────────────────────────────┘
```
