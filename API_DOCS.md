# Documentación de la API del Microservicio RAG (Python/FastAPI)

Este documento describe los endpoints disponibles en el microservicio Python de RAG y cómo el monolito de .NET debe integrarse con ellos.

## Base URL
El servicio se expone típicamente en `http://ai-service:8000` o donde se decida desplegar.

## Autenticación
Todas las peticiones a la API deben incluir el header:
`X-API-KEY: <tu_clave_secreta>`

Esta clave debe coincidir con la definida en el `.env` del microservicio (`X_API_KEY`).

---

## Endpoints

### 1. `POST /chat`
Realiza una consulta a la Inteligencia Artificial usando Retrieval-Augmented Generation (RAG).

**Headers:**
- `X-API-KEY: <secret>`
- `Content-Type: application/json`

**Body:**
```json
{
  "question": "¿Cuáles son los síntomas del estrés hídrico en arándanos?",
  "iot_context": "Los sensores indican una humedad del suelo del 15% y temperatura foliar de 32°C."
}
```

**Respuesta Exitosa (200 OK):**
```json
{
  "answer": "El estrés hídrico en arándanos se presenta...",
  "model_used": "gemini-2.5-flash",
  "complexity": "COMPLEJA",
  "sources": [
    {
      "source": "manual_arandanos.pdf",
      "page": 45,
      "observation_id": null
    },
    {
      "source": "Bitácora",
      "page": "?",
      "observation_id": "b123-abc-456"
    }
  ]
}
```

---

### 2. `POST /ingest-logs`
Envía una o más observaciones (bitácoras de usuario) al microservicio para que sean vectorizadas en lote e integradas en el conocimiento del RAG.

**Headers:**
- `X-API-KEY: <secret>`
- `Content-Type: application/json`

**Body:**
```json
{
  "logs": [
    {
      "observation_id": "guid-unico-de-la-db-sql",
      "text_content": "El lote 4 presenta hojas marchitas en las puntas. Se aplicó riego de emergencia.",
      "metadata": {
        "user_id": "123",
        "crop_id": "Lote-4"
      }
    },
    {
      "observation_id": "guid-unico-2",
      "text_content": "Recolección terminada en lote 5, buen calibre.",
      "metadata": {
        "user_id": "123",
        "crop_id": "Lote-5"
      }
    }
  ]
}
```

**Respuesta Exitosa (200 OK):**
```json
{
  "status": "success",
  "message": "2 logs vectorizados correctamente."
}
```

---

### 3. `POST /update-papers`
Reemplaza la colección de `papers_expertos` subiendo un archivo `.zip` que contiene la carpeta `chroma_db` generada previamente mediante el script local `setup_database.py` y empaquetado con `export_db.sh`.

**Headers:**
- `X-API-KEY: <secret>`
- `Content-Type: multipart/form-data`

**Body:**
- Form-data key: `file`
- Form-data value: `chroma_db.zip` (Archivo)

**Respuesta Exitosa (200 OK):**
```json
{
  "status": "success",
  "message": "Base de datos ChromaDB actualizada exitosamente."
}
```

---

### 4. `GET /export-db`
Descarga la base de datos ChromaDB actual (incluye papers y bitácoras) en formato `.zip` para copias de seguridad.

**Headers:**
- `X-API-KEY: <secret>`

**Respuesta Exitosa (200 OK):**
Descarga un archivo binario `chroma_db_export.zip`.

---

### 4. `POST /update-api-key`
Actualiza y persiste la clave de la API de Google Gemini en el archivo `.env`.
*(Nota de Seguridad: Este endpoint sobrescribe las credenciales globales en disco. Por diseño de concurrencia y seguridad, **se requiere reiniciar el servicio** para que la nueva llave tome efecto de manera segura en todos los workers).*

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

## Flujo Recomendado para el Background Worker en .NET
1. El monolito revisa en SQL Server las observaciones con `IsVectorized = false`.
2. Se procesan por lotes (ej. 50 a la vez), enviando el arreglo a `POST /ingest-logs`.
3. Si la respuesta es exitosa (HTTP 200), se marcan en SQL como `IsVectorized = true`.
4. El worker debería ejecutarse en horas de poco tráfico (e.g. 2:00 AM).
