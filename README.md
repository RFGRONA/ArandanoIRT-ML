# ArandanoIRT-ML — Microservicio de Inteligencia Artificial con RAG

> **Componente de IA del sistema AIRT (Arándano Infrarrojo Térmico)**
>
> Microservicio REST especializado en recuperación y generación aumentada de conocimiento (RAG) para el diagnóstico agronómico de arándano mediante termografía infrarroja. Desarrollado como proyecto de grado de Ingeniería de Sistemas.

---

## Descripción General

Este repositorio contiene el microservicio de Inteligencia Artificial del sistema **AIRT**, una plataforma integral de monitoreo de estrés hídrico en cultivos de arándano (*Vaccinium corymbosum*) que combina sensores IoT, termografía infrarroja y modelos de lenguaje de gran escala (LLMs).

El microservicio implementa la arquitectura **RAG (Retrieval-Augmented Generation)** para proporcionar un asistente de IA especializado que:

- Consulta un corpus de literatura científica vectorizada (papers, manuales agronómicos).
- Incorpora dinámicamente observaciones de campo registradas por los agricultores.
- Integra datos en tiempo real de sensores IoT para contextualizar las recomendaciones.
- Genera respuestas fundamentadas y trazables, con citas a las fuentes originales.

El servicio se integra como componente externo al monolito principal **ArandanoIRT** (ASP.NET Core), comunicándose a través de una API REST autenticada.

---

## Tabla de Contenidos

- [Contexto del Proyecto](#contexto-del-proyecto)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Stack Tecnológico](#stack-tecnológico)
- [Estructura del Repositorio](#estructura-del-repositorio)
- [Requisitos del Sistema](#requisitos-del-sistema)
- [Configuración del Entorno](#configuración-del-entorno)
- [Inicialización de la Base de Datos Vectorial](#inicialización-de-la-base-de-datos-vectorial)
- [Despliegue con Docker](#despliegue-con-docker)
- [Referencia de la API](#referencia-de-la-api)
- [Flujo de Consulta RAG](#flujo-de-consulta-rag)
- [Mantenimiento y Administración](#mantenimiento-y-administración)
- [Licencia](#licencia)

---

## Contexto del Proyecto

El sistema AIRT fue concebido para abordar la detección temprana del estrés hídrico en arándanos, una problemática crítica que afecta directamente la productividad y calidad de los cultivos. La arquitectura global del sistema comprende tres repositorios complementarios:

| Repositorio | Descripción |
|---|---|
| `ArandanoIRT` *(monolito)* | Aplicación web ASP.NET Core con módulos de gestión de cultivos, dispositivos IoT y visualización de datos |
| **`ArandanoIRT-ML`** *(este repositorio)* | Microservicio Python de IA con RAG, vectorización de documentos y enrutamiento inteligente de modelos |
| `ArandanoIRT-Firmware` | Firmware ESP32/ESP32-S3 para adquisición de imágenes térmicas y datos ambientales |

El presente microservicio constituye la capa de inteligencia del ecosistema, habilitando la consulta semántica de conocimiento experto y la incorporación de datos operativos del campo.

---

## Arquitectura del Sistema

```
┌──────────────────────┐         POST /chat          ┌────────────────────────────┐
│    Monolito .NET      │ ──────────────────────────► │   Microservicio RAG (Python)│
│    (ArandanoIRT)      │ ◄──────────────────────────  │   FastAPI + Uvicorn         │
│                       │       JSON Response         │                            │
│  ┌─────────────────┐  │                             │  ┌──────────────────────┐  │
│  │ AiAssistant     │  │   POST /ingest-logs         │  │  Router de Modelos   │  │
│  │ Controller      │  │ ──────────────────────────► │  │  (Gemini 2.5)        │  │
│  └─────────────────┘  │                             │  └──────────┬───────────┘  │
│  ┌─────────────────┐  │                             │             │              │
│  │ Background      │  │                             │  ┌──────────▼───────────┐  │
│  │ Vectorization   │  │                             │  │  ChromaDB (Vector DB)│  │
│  │ Service         │  │                             │  │  ├─ papers_expertos  │  │
│  └─────────────────┘  │                             │  │  └─ bitacoras_usuario│  │
└──────────┬────────────┘                             └──────────────────────────┘
           │                                                         │
           │ Sensores IoT                                            │ Embeddings
           ▼                                                         ▼
    ┌─────────────┐                                         ┌──────────────────┐
    │ PostgreSQL  │                                         │ HuggingFace      │
    │ (Datos      │                                         │ MiniLM-L12-v2    │
    │  Térmicos)  │                                         │ (Multilingüe)    │
    └─────────────┘                                         └──────────────────┘
```

### Principios de Diseño

| Principio | Implementación |
|---|---|
| **Enrutamiento inteligente** | Un modelo ligero (`gemini-2.5-flash-lite`) clasifica la complejidad de cada consulta antes de derivarla al modelo apropiado, optimizando costo y latencia |
| **Doble colección vectorial** | Separación estricta entre conocimiento estático (literatura científica) y conocimiento dinámico (observaciones de campo) |
| **Contexto IoT condicional** | Las bitácoras se incluyen en la recuperación *solo* cuando el usuario selecciona una planta específica en la interfaz, evitando ruido semántico en consultas generales |
| **Seguridad perimetral** | Autenticación por API Key con verificación en tiempo constante en todos los endpoints; validaciones anti-Zip Slip en carga de archivos |
| **Trazabilidad de fuentes** | Cada respuesta incluye las fuentes exactas (nombre de PDF + número de página, o ID de observación) que fundamentaron la respuesta generada |

---

## Stack Tecnológico

| Categoría | Tecnología | Versión |
|---|---|---|
| Framework web | [FastAPI](https://fastapi.tiangolo.com/) | ≥ 0.136 |
| Servidor ASGI | [Uvicorn](https://www.uvicorn.org/) | ≥ 0.45 |
| Modelos de lenguaje | [Google Gemini 2.5](https://ai.google.dev/) | gemini-2.5-flash / flash-lite |
| Base de datos vectorial | [ChromaDB](https://www.trychroma.com/) | ≥ 1.5 |
| Modelo de embeddings | [paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) | — |
| Orquestación de cadenas | [LangChain](https://www.langchain.com/) | ≥ 0.4 |
| Procesamiento de PDFs | [PyPDF](https://pypdf.readthedocs.io/) | ≥ 6.10 |
| Validación de datos | [Pydantic](https://docs.pydantic.dev/) | v2 |
| Gestión de dependencias | [uv](https://github.com/astral-sh/uv) | — |
| Contenedorización | Docker / Podman | — |
| Lenguaje | Python | 3.12+ |

---

## Estructura del Repositorio

```
ArandanoIRT-ML/
├── app/
│   ├── main.py                  # Punto de entrada de FastAPI; definición de rutas
│   ├── schemas.py               # Modelos de datos Pydantic (request/response)
│   ├── core/
│   │   └── security.py          # Verificación de API Key en tiempo constante
│   ├── services/
│   │   ├── chroma_service.py    # Gestión de las colecciones ChromaDB
│   │   └── rag_service.py       # Lógica RAG: recuperación, enrutamiento y generación
│   └── prompts/                 # Plantillas de prompts para los modelos Gemini
├── scripts/
│   ├── export_db.sh             # Empaqueta chroma_db/ en un .zip para distribución
│   ├── run_dev.sh               # Servidor de desarrollo con recarga automática
│   └── setup_swap.sh            # Configura SWAP para servidores con ≤ 2 GB RAM
├── data/                        # Directorio para los PDFs fuente (no versionado)
├── chroma_db/                   # Base de datos vectorial persistida (no versionada)
├── setup_database.py            # Script de inicialización y vectorización de PDFs
├── Dockerfile                   # Imagen de producción basada en python:3.12-slim
├── pyproject.toml               # Metadatos del proyecto y dependencias (PEP 517)
├── uv.lock                      # Lockfile determinista para builds reproducibles
├── .env.template                # Plantilla de variables de entorno
├── API_DOCS.md                  # Referencia completa de todos los endpoints
└── README.md                    # Este documento
```

---

## Requisitos del Sistema

| Requisito | Especificación |
|---|---|
| **Sistema operativo** | Linux (recomendado para despliegue en producción) |
| **Python** | 3.12 o superior |
| **Gestor de paquetes** | [`uv`](https://github.com/astral-sh/uv) |
| **Contenedor** | Docker ≥ 24 o Podman (como alternativa) |
| **RAM** | ≥ 2 GB (se recomienda configurar SWAP en servidores ajustados; ver `scripts/setup_swap.sh`) |
| **Disco** | ≥ 2 GB libres (modelo de embeddings ~400 MB + base de datos vectorial) |

---

## Configuración del Entorno

### 1. Instalar `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clonar e instalar dependencias

```bash
git clone <url-del-repositorio>
cd ArandanoIRT-ML
uv sync
```

### 3. Configurar variables de entorno

Copia la plantilla y edita el archivo con tus credenciales:

```bash
cp .env.template .env
```

```env
# .env — No versionado. Mantener en secreto.
GOOGLE_API_KEY=tu_api_key_de_google_gemini
X_API_KEY=tu_clave_secreta_compartida_con_el_monolito
HF_TOKEN=tu_token_de_huggingface
CHROMA_DB_PAPERS=./chroma_db/papers
CHROMA_DB_LOGS=./chroma_db/logs
```

| Variable | Descripción |
|---|---|
| `GOOGLE_API_KEY` | Clave de la API de Google AI Studio para los modelos Gemini 2.5. Puede actualizarse en caliente vía `POST /update-api-key`. |
| `X_API_KEY` | Secreto compartido entre el monolito .NET y este microservicio. Se usa para autenticar todas las peticiones entrantes. |
| `HF_TOKEN` | Token de HuggingFace para la descarga del modelo de embeddings multilingüe. Requerido para el primer arranque del contenedor. |
| `CHROMA_DB_PAPERS` | Ruta al directorio de la colección vectorial de literatura científica. |
| `CHROMA_DB_LOGS` | Ruta al directorio de la colección vectorial de bitácoras de usuario. |

---

## Inicialización de la Base de Datos Vectorial

> **Requisito previo**: Al arrancar por primera vez, la colección de papers estará vacía. Es necesario vectorizar la literatura científica antes de realizar consultas con contexto experto.

### Paso 1 — Colocar los documentos PDF

Deposita todos los archivos PDF (papers, manuales, guías técnicas) en la carpeta `data/` del proyecto:

```
ArandanoIRT-ML/
└── data/
    ├── Manual de manejo agronómico del arándano.pdf
    ├── Control de Phytophthora cinnamomi en arándano.pdf
    └── ... (demás documentos fuente)
```

### Paso 2 — Ejecutar el script de vectorización

El siguiente comando procesa todos los PDFs: los fragmenta en *chunks* de 1 000 caracteres con 200 de solapamiento, genera los embeddings con el modelo multilingüe y los persiste en ChromaDB:

```bash
uv run setup_database.py
```

Salida esperada:

```
--- 1. Cargando Documentos PDF ---
✅ Cargados: 2600 páginas
--- 2. Fragmentando Texto ---
✅ Fragmentos: 7609
--- 4. Generando Base de Datos en la colección 'papers_expertos' ---
✅ ¡BASE DE DATOS CREADA EXITOSAMENTE!
```

### Paso 3 (Opcional) — Exportar para respaldo o distribución

```bash
bash scripts/export_db.sh
```

Genera `chroma_db.zip`, que puede subirse desde la UI de administración del monolito .NET (**Asistente IA → Configuraciones → Actualizar Base de Datos de Expertos**).

> **Nota sobre volúmenes Docker**: Si el contenedor ya está en ejecución con `chroma_db/` montado como volumen, los cambios realizados por `setup_database.py` en el host se reflejan automáticamente en el contenedor al reiniciarlo.

---

## Despliegue con Docker

### Construir la imagen

```bash
docker build -t airtml .
```

### Ejecutar el contenedor

El contenedor requiere **dos volúmenes** para garantizar la persistencia de datos entre reinicios:

```bash
docker run -d \
  --name airtml-server \
  -p 8000:8000 \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/hf_cache:/root/.cache/huggingface \
  --env-file .env \
  airtml
```

| Volumen | Propósito |
|---|---|
| `chroma_db:/app/chroma_db` | Base de datos vectorial (papers + bitácoras). Persiste entre reinicios y rebuilds. |
| `hf_cache:/root/.cache/huggingface` | Caché del modelo de embeddings (~400 MB). Evita la re-descarga en cada rebuild. |

> **Usuarios de Podman**: Agrega el sufijo `:Z` a cada volumen para el etiquetado SELinux correcto (p. ej., `-v $(pwd)/chroma_db:/app/chroma_db:Z`).

### Verificar el estado del servicio

Monitorea los logs hasta confirmar el arranque completo:

```bash
docker logs -f airtml-server
```

Salida esperada al arranque exitoso:

```
Colección 'papers_expertos' cargada: 7609 documentos
Colección 'bitacoras_usuario' cargada: 10 documentos
Servicios ML inicializados correctamente. Levantando Uvicorn...
INFO:     Application startup complete.
```

Verificación de salud del servicio:

```bash
curl http://localhost:8000/health
# {"status":"ok","message":"API RAG funcionando correctamente."}
```

### Mantenimiento del contenedor

```bash
# Detener y eliminar el contenedor
docker stop airtml-server && docker rm airtml-server

# Reiniciar (tras detención)
docker start airtml-server

# Servidores con RAM limitada (≤ 2 GB): configurar SWAP
bash scripts/setup_swap.sh
```

---

## Referencia de la API

La documentación interactiva (Swagger UI) está disponible en `http://localhost:8000/docs` cuando el servicio está en ejecución.

Para la referencia completa de todos los endpoints, parámetros, esquemas de request/response y ejemplos de integración con .NET, consulta [API_DOCS.md](./API_DOCS.md).

### Resumen de Endpoints

| Método | Endpoint | Autenticación | Descripción |
|---|---|---|---|
| `GET` | `/health` | No requerida | Verificación de disponibilidad del servicio |
| `POST` | `/chat` | API Key | Consulta RAG con enrutamiento inteligente de modelos |
| `POST` | `/ingest-logs` | API Key | Vectorización en lote de bitácoras de observación |
| `POST` | `/update-papers` | API Key | Actualiza la colección de papers desde un archivo `.zip` |
| `GET` | `/export-db` | API Key | Descarga la base de datos vectorial completa en `.zip` |
| `POST` | `/update-api-key` | API Key | Actualiza y persiste la clave de Google Gemini |

> **Autenticación**: Todos los endpoints (excepto `/health`) requieren el header `X-API-KEY: <secreto>`.

---

## Flujo de Consulta RAG

El siguiente diagrama describe el ciclo de vida completo de una consulta al asistente de IA:

```
Usuario                  Monolito .NET               Microservicio RAG
   │                          │                              │
   │── Envía mensaje ────────►│                              │
   │                          │── (Si hay planta)            │
   │                          │   Consulta datos IoT         │
   │                          │   (térm., ambient., climas)  │
   │                          │                              │
   │                          │── POST /chat ───────────────►│
   │                          │   {question, iot_context,    │
   │                          │    expertise_level}          │
   │                          │                              │
   │                          │                 ┌────────────┤
   │                          │                 │ Router:    │
   │                          │                 │ ¿Simple o  │
   │                          │                 │ compleja?  │
   │                          │                 └────────────┤
   │                          │                              │
   │                          │                 ┌────────────┤
   │                          │                 │ Recupera:  │
   │                          │                 │ papers (5) │
   │                          │                 │ + bitácoras│
   │                          │                 │ (3, cond.) │
   │                          │                 └────────────┤
   │                          │                              │
   │                          │                 ┌────────────┤
   │                          │                 │ Genera con │
   │                          │                 │ Gemini 2.5 │
   │                          │                 └────────────┤
   │                          │                              │
   │                          │◄── JSON {answer, sources} ───│
   │                          │                              │
   │◄── Respuesta con fuentes─│                              │
```

**Reglas de enrutamiento de modelos:**

- Consultas **simples** → `gemini-2.5-flash-lite` (respuesta rápida, menor costo).
- Consultas **complejas** → `gemini-2.5-flash` (mayor capacidad de razonamiento).

**Reglas de recuperación de documentos:**

- **Sin contexto de planta**: Se consultan únicamente los `papers_expertos` (5 documentos más relevantes).
- **Con contexto de planta**: Se consultan `papers_expertos` (5 docs) **y** `bitacoras_usuario` (3 docs más relevantes), combinando conocimiento académico y experiencia de campo.

---

## Mantenimiento y Administración

### Actualizar el corpus de literatura científica

**Vía CLI (recomendada para desarrollo):**

1. Agrega los nuevos PDFs a la carpeta `data/`.
2. Ejecuta `uv run setup_database.py` (selecciona `s` para recrear la colección).
3. Reinicia el contenedor.

**Vía UI del monolito (recomendada para producción):**

1. Genera la base de datos localmente con `uv run setup_database.py`.
2. Empaqueta con `bash scripts/export_db.sh`.
3. En la plataforma web, navega a **Asistente IA → Configuraciones** (solo rol Administrador).
4. Sube el archivo `chroma_db.zip` en la sección **"Actualizar Base de Datos de Expertos"**.
5. El endpoint `POST /update-papers` reemplaza **solo** la colección `papers_expertos`; las bitácoras no se ven afectadas.

### Vectorización automática de observaciones

El monolito .NET incorpora un `BackgroundService` que:

1. Consulta periódicamente las observaciones con `IsVectorized = false` en la base de datos SQL.
2. Agrupa las observaciones en lotes (máx. 50 por petición).
3. Envía el lote al endpoint `POST /ingest-logs`.
4. Marca las observaciones como `IsVectorized = true` al recibir HTTP 200.

Este flujo es completamente transparente para el usuario final y garantiza que el conocimiento operativo del campo esté siempre disponible para el asistente de IA.

---

## Licencia

Este proyecto está distribuido bajo los términos de la licencia incluida en el archivo [LICENSE](./LICENSE).

---

*Proyecto de Grado — Ingeniería de Sistemas · Repositorio parte del ecosistema AIRT.*
