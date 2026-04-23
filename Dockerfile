FROM python:3.12-slim

# Instalar dependencias del sistema requeridas
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copiar archivos de dependencias
COPY pyproject.toml uv.lock ./

# Sincronizar dependencias globales usando uv
RUN uv sync --system

# Copiar la aplicación
COPY app ./app
COPY .env.template ./

# Exponer el puerto
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
