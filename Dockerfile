FROM python:3.12-slim

# Instalar dependencias del sistema requeridas
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar uv con versión fijada para builds reproducibles
RUN python -m pip install --no-cache-dir uv==0.5.7

# Copiar archivos de dependencias
COPY pyproject.toml uv.lock ./

# Sincronizar dependencias (esto crea automáticamente un .venv en /app/.venv)
RUN uv sync --no-install-package torch \
    && uv pip install --index-url https://download.pytorch.org/whl/cpu torch==2.11.0

# ¡CRÍTICO! Agregamos el entorno virtual al PATH del contenedor
ENV PATH="/app/.venv/bin:$PATH"

# ¡NUEVO! Evita que Python guarde los logs en el buffer interno
ENV PYTHONUNBUFFERED=1

# Copiar la aplicación
COPY app ./app
COPY .env.template ./

# Exponer el puerto
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]