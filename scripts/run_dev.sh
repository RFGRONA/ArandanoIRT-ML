#!/bin/bash
# script para levantar el servidor de desarrollo local

echo "Iniciando servidor FastAPI en modo desarrollo..."
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
