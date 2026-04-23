# 🫐 Sistema RAG - Experto en Arándanos y Termografía (Microservicio API)

Sistema de Recuperación y Generación Aumentada (RAG) especializado en documentación sobre cultivo de arándanos, refactorizado como un microservicio REST utilizando **FastAPI**, **Google Gemini 2.5 Flash**, y **ChromaDB**.

## 📋 Tabla de Contenidos
- [Características](#-características)
- [Requisitos del Sistema](#-requisitos-del-sistema)
- [Instalación Rápida con `uv`](#-instalación-rápida-con-uv)
- [Configuración](#️-configuración)
- [Uso y Ejecución](#-uso-y-ejecución)
- [Base de Datos Vectorial](#-base-de-datos-vectorial)
- [Despliegue (Docker)](#-despliegue-docker)

---

## ✨ Características
- 🚀 **API REST (FastAPI)**: Comunicación fácil para el monolito .NET y otros clientes.
- 🤖 **Gemini 2.5 Router**: Decide dinámicamente si usar `Gemini-Flash-Lite` o `Gemini-Flash` según la complejidad de la consulta.
- 💾 **Doble Colección ChromaDB**: Separa "Papers Expertos" inmutables de "Bitácoras".
- 📦 **Procesamiento en Lote (Batch)**: Vectorización masiva de bitácoras en un solo request.
- ☁️ **Backups y Actualizaciones API**: Endpoints para descargar la BD en `.zip` y actualizar credenciales en caliente.
- 🔒 **Seguridad API-KEY**: Protege todos los endpoints de accesos no autorizados.
- ⚡ **Gestión con `uv`**: Tiempos de instalación de dependencias en milisegundos.

---

## 💻 Requisitos del Sistema
- **Python**: 3.12+
- **Gestor**: [uv](https://github.com/astral-sh/uv) (Extremadamente recomendado)
- **Sistema**: Ubuntu / Linux (Recomendado para despliegue).

---

## 🔧 Instalación Rápida con `uv`

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

Copia el archivo `.env.template` a `.env` y configura tus credenciales:
```bash
cp .env.template .env
```

```env
# .env
GOOGLE_API_KEY=tu_api_key_de_google_aqui
X_API_KEY=tu_clave_secreta_para_el_monolito_aqui
CHROMA_DB_PAPERS=./chroma_db/papers
CHROMA_DB_LOGS=./chroma_db/logs
```
*(Nota: La `GOOGLE_API_KEY` puede ser modificada a través del endpoint `/update-api-key`, pero **requerirá reiniciar el servidor** para aplicarse de forma segura).*

---

## 🚀 Uso y Ejecución

Para iniciar el servidor de desarrollo en local:

```bash
bash scripts/run_dev.sh
```
La API estará disponible en `http://localhost:8000`.
Documentación interactiva Swagger: `http://localhost:8000/docs`.

*(Ver `API_DOCS.md` para detalles de cómo interactuar con los endpoints).*

---

## 📚 Base de Datos Vectorial

### 1. Inicializar la DB Localmente (Solo la primera vez)
Para vectorizar los PDFs que están en la carpeta `data/` y crear la colección `papers_expertos`:
```bash
uv run setup_database.py
```

### 2. Exportar la DB para Producción
Empaqueta la base de datos para subirla al entorno de producción:
```bash
bash scripts/export_db.sh
```
Esto genera `chroma_db.zip`.

---

## 🐳 Despliegue (Docker)

Para desplegar en el servidor (Ej: Ubuntu VM):

1. **(Opcional pero Recomendado)** Configura el SWAP en servidores de 2GB RAM:
```bash
bash scripts/setup_swap.sh
```

2. Construye y corre la imagen:
```bash
docker build -t arandano-rag-api .
docker run -d -p 8000:8000 --env-file .env arandano-rag-api
```
