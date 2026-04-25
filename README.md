# 🫐 ArandanoIRT-ML — Microservicio RAG

Sistema de Recuperación y Generación Aumentada (RAG) especializado en documentación técnica sobre cultivo de arándanos y termografía infrarroja. Construido como microservicio REST con **FastAPI**, **Google Gemini 2.5**, y **ChromaDB**.

## 📋 Tabla de Contenidos
- [Características](#-características)
- [Requisitos del Sistema](#-requisitos-del-sistema)
- [Instalación Rápida](#-instalación-rápida)
- [Configuración](#️-configuración)
- [Alimentar el RAG (Primera Vez)](#-alimentar-el-rag-primera-vez)
- [Despliegue con Docker](#-despliegue-con-docker)
- [Actualizar Papers desde la UI](#-actualizar-papers-desde-la-ui)
- [Arquitectura](#-arquitectura)

---

## ✨ Características
- 🚀 **API REST (FastAPI)**: Integración directa con el monolito .NET.
- 🤖 **Gemini 2.5 Router**: Decide dinámicamente si usar `gemini-2.5-flash-lite` (consultas simples) o `gemini-2.5-flash` (consultas complejas) para optimizar costos y calidad.
- 💾 **Doble Colección ChromaDB**: Separa **Papers Expertos** (literatura científica) de **Bitácoras de Usuario** (observaciones de campo).
- 🌿 **Contexto IoT Condicional**: Las bitácoras solo se consultan cuando el usuario selecciona una planta en la interfaz, evitando ruido en consultas generales.
- 📦 **Procesamiento en Lote (Batch)**: Vectorización masiva de bitácoras en un solo request vía `POST /ingest-logs`.
- ☁️ **Backups y Actualizaciones**: Endpoints para exportar la BD en `.zip`, actualizar papers y modificar credenciales.
- 🔒 **Seguridad API-KEY**: Todos los endpoints protegidos con verificación de clave en tiempo constante.
- 📝 **Logging Estructurado**: Logs detallados por cada consulta (documentos recuperados, modelo seleccionado, fuentes citadas).

---

## 💻 Requisitos del Sistema
- **Python**: 3.12+
- **Gestor de paquetes**: [uv](https://github.com/astral-sh/uv)
- **Contenedor**: Docker (o Podman como alternativa)
- **Sistema**: Linux (recomendado para despliegue)

---

## 🔧 Instalación Rápida

1. Instala `uv` si aún no lo tienes:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clona el repositorio e instala dependencias:
```bash
git clone <tu-repositorio>
cd ArandanoIRT-ML
uv sync
```

---

## ⚙️ Configuración

Copia `.env.template` a `.env` y configura tus credenciales:
```bash
cp .env.template .env
```

```env
# .env
GOOGLE_API_KEY=tu_api_key_de_google_gemini
X_API_KEY=tu_clave_secreta_para_el_monolito
HF_TOKEN=tu_token_de_huggingface
CHROMA_DB_PAPERS=./chroma_db/papers
CHROMA_DB_LOGS=./chroma_db/logs
```

| Variable | Descripción |
|---|---|
| `GOOGLE_API_KEY` | API Key de Google Gemini para los modelos de IA. Puede actualizarse vía `/update-api-key`. |
| `X_API_KEY` | Clave compartida entre el monolito .NET y este microservicio para autenticación. |
| `HF_TOKEN` | Token de HuggingFace para descargar el modelo de embeddings (`paraphrase-multilingual-MiniLM-L12-v2`). **Requerido** para que el contenedor arranque correctamente. |
| `CHROMA_DB_PAPERS` | Ruta al directorio de la colección de papers vectorizados. |
| `CHROMA_DB_LOGS` | Ruta al directorio de la colección de bitácoras vectorizadas. |

---

## 📚 Alimentar el RAG (Primera Vez)

> **Importante**: Al iniciar el microservicio por primera vez, la colección de papers estará vacía (0 documentos). Es necesario vectorizar los PDFs antes de poder hacer consultas con contexto de literatura científica.

### Paso 1: Colocar los PDFs

Coloca todos los archivos PDF (papers, manuales, guías) en la carpeta `data/` del proyecto:
```
ArandanoIRT-ML/
├── data/
│   ├── Manual de manejo agronómico del arándano.pdf
│   ├── Control de Phytophtora cinnamomi...pdf
│   └── ... (más PDFs)
```

### Paso 2: Vectorizar los PDFs

Ejecuta el script de configuración inicial. Este proceso lee todos los PDFs, los fragmenta en chunks de 1000 caracteres con 200 de overlap, genera embeddings con el modelo multilingüe y los almacena en ChromaDB:

```bash
uv run setup_database.py
```

Verás un progreso similar a:
```
--- 1. Cargando Documentos PDF ---
✅ Cargados: 2600 páginas
--- 2. Fragmentando Texto ---
✅ Fragmentos: 7609
--- 4. Generando Base de Datos en la colección 'papers_expertos' ---
✅ ¡BASE DE DATOS CREADA EXITOSAMENTE!
```

> **Nota sobre volúmenes**: Si ya tienes un contenedor corriendo con la carpeta `chroma_db/` montada como volumen, los cambios realizados por `setup_database.py` en el host **se reflejan automáticamente** en el contenedor al reiniciarlo, ya que comparten el mismo directorio en disco.

### Paso 3 (Opcional): Exportar para respaldo

Empaqueta la base de datos completa en un ZIP para distribución o respaldo:
```bash
bash scripts/export_db.sh
```
Esto genera `chroma_db.zip` que puede subirse desde la UI de administración del monolito .NET (ver sección [Actualizar Papers desde la UI](#-actualizar-papers-desde-la-ui)).

---

## 🐳 Despliegue con Docker

### Construir la imagen

```bash
docker build -t airtml .
```

### Ejecutar el contenedor

El contenedor requiere **dos volúmenes** para persistencia:

```bash
docker run -d \
  --name airtml-server \
  -p 8000:8000 \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/hf_cache:/root/.cache/huggingface \
  --env-file .env \
  airtml
```

> **Nota para Podman**: Si usas Podman en lugar de Docker, agrega el sufijo `:Z` a cada volumen para el etiquetado SELinux (ej. `-v $(pwd)/chroma_db:/app/chroma_db:Z`).

| Volumen | Propósito |
|---|---|
| `chroma_db:/app/chroma_db` | Base de datos vectorial (papers + bitácoras). Persiste entre reinicios. |
| `hf_cache:/root/.cache/huggingface` | Caché del modelo de embeddings (~400MB). Evita re-descargarlo en cada rebuild. |

> **Primer arranque**: La primera vez que el contenedor inicia, descargará el modelo de embeddings desde HuggingFace. Con el `HF_TOKEN` configurado y el volumen de caché, las siguientes veces arrancará en segundos.

### Verificar que está listo

Monitorea los logs hasta ver `Application startup complete`:
```bash
docker logs -f airtml-server
```

Al iniciar verás el conteo de documentos en cada colección:
```
Colección 'papers_expertos' cargada: 7609 documentos
Colección 'bitacoras_usuario' cargada: 10 documentos
Servicios ML inicializados correctamente. Levantando Uvicorn...
```

### Verificar salud

```bash
curl http://localhost:8000/health
# {"status":"ok","message":"API RAG funcionando correctamente."}
```

### Reiniciar el contenedor

```bash
docker stop airtml-server && docker rm airtml-server
# Luego ejecutar el comando `docker run` de arriba nuevamente
```

### Configurar SWAP (servidores con ≤2GB RAM)

```bash
bash scripts/setup_swap.sh
```

---

## 🔄 Actualizar Papers desde la UI

Cuando necesites agregar nuevos PDFs al RAG:

### Opción A: CLI (Recomendada)

1. Agrega los nuevos PDFs a la carpeta `data/`.
2. Ejecuta `uv run setup_database.py` (selecciona "s" para recrear).
3. Reinicia el contenedor.

### Opción B: UI del Monolito .NET

1. Ejecuta `uv run setup_database.py` localmente para generar la DB.
2. Empaqueta con `bash scripts/export_db.sh`.
3. En la plataforma web, navega a **Asistente IA → Configuraciones** (⚙️, solo Admin).
4. Sube el archivo `chroma_db.zip` en la sección **"Actualizar Base de Datos de Expertos"**.
5. El microservicio reemplazará **solo la colección de papers**, sin afectar las bitácoras.

> **Importante**: La subida por UI solo reemplaza la colección `papers_expertos`. Las bitácoras (`bitacoras_usuario`) se mantienen intactas, ya que su vectorización es automática desde el backend .NET.

---

## 🏗️ Arquitectura

```
┌──────────────────┐      POST /chat         ┌──────────────────────┐
│   Monolito .NET  │ ──────────────────────►  │  Microservicio RAG   │
│  (ArandanoIRT)   │ ◄──────────────────────  │  (FastAPI + Python)  │
│                  │      JSON Response       │                      │
│  - Controller    │                          │  - Router (Lite/Flash)│
│  - IoT Context   │      POST /ingest-logs   │  - ChromaDB          │
│  - Background    │ ──────────────────────►  │    ├─ papers_expertos │
│    Workers       │                          │    └─ bitacoras_usuario│
└──────────────────┘                          └──────────────────────┘
        │                                              │
        │ Selección de Planta                          │ Embeddings
        │ + Datos IoT                                  │ (MiniLM-L12-v2)
        ▼                                              ▼
  ┌───────────┐                                ┌──────────────┐
  │ PostgreSQL│                                │  Google       │
  │ (Sensores)│                                │  Gemini 2.5   │
  └───────────┘                                └──────────────┘
```

### Flujo de una consulta

1. El usuario envía un mensaje en el chat del Asistente IA.
2. Si seleccionó una planta, el controlador .NET agrega datos IoT (temperatura, humedad, climas) al contexto.
3. El microservicio enruta la consulta al modelo apropiado (`flash-lite` o `flash`).
4. Se recuperan documentos relevantes de **papers** (siempre) y de **bitácoras** (solo si hay planta seleccionada).
5. El modelo genera una respuesta concisa con las fuentes citadas.
6. Las fuentes se muestran al usuario diferenciando entre PDFs (nombre + página) y bitácoras (Obs ID).

---

## 📖 Referencia API

Ver [API_DOCS.md](./API_DOCS.md) para la documentación completa de todos los endpoints.
