#!/bin/bash
# script para exportar la base de datos a un archivo ZIP

echo "Exportando la base de datos chroma_db..."

if [ ! -d "chroma_db" ]; then
    echo "La carpeta chroma_db no existe. Debes ejecutar setup_database.py primero."
    exit 1
fi

zip -r chroma_db.zip chroma_db/

echo "¡Base de datos exportada en chroma_db.zip!"
