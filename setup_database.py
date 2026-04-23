import os
import torch
import shutil
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

"""
SCRIPT DE CONFIGURACIÓN INICIAL
Ejecuta este script UNA SOLA VEZ localmente para crear la base de datos vectorial de papers.
Luego, usa scripts/export_db.sh para generar un ZIP que subirás a producción.
"""

def main():
    print("=" * 60)
    print("  CONFIGURACIÓN INICIAL - BASE DE DATOS VECTORIAL")
    print("=" * 60)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\n🖥️  Dispositivo: {device.upper()}")
    
    persist_directory = "./chroma_db/papers"
    collection_name = "papers_expertos"
    
    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        respuesta = input(f"\n⚠️  Ya existe una base de datos en '{persist_directory}'.\n¿Deseas recrearla? (s/n): ")
        if respuesta.lower() != 's':
            print("❌ Operación cancelada.")
            return
        print("🗑️  Eliminando base de datos anterior...")
        shutil.rmtree(persist_directory)
    
    print("\n--- 1. Cargando Documentos PDF ---")
    loader = PyPDFDirectoryLoader("./data")
    docs = loader.load()
    print(f"✅ Cargados: {len(docs)} páginas")

    print("\n--- 2. Fragmentando Texto ---")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(docs)
    print(f"✅ Fragmentos: {len(splits)}")

    print(f"\n--- 3. Creando Embeddings con {device.upper()} ---")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': device},
        encode_kwargs={'normalize_embeddings': True}
    )
    print("✅ Modelo cargado")

    print(f"\n--- 4. Generando Base de Datos en la colección '{collection_name}' ---")
    print("⏳ Esto puede tardar varios minutos...")
    
    vectorstore = Chroma.from_documents(
        collection_name=collection_name,
        documents=splits, 
        embedding=embeddings,
        persist_directory=persist_directory
    )
    
    print(f"\n{'=' * 60}")
    print("  ✅ ¡BASE DE DATOS CREADA EXITOSAMENTE!")
    print(f"{'=' * 60}")
    print(f"\n📦 Ubicación: {persist_directory}")
    print(f"📊 Total de fragmentos: {len(splits)}")
    print(f"\n▶️  Ahora puedes usar: bash scripts/export_db.sh")

if __name__ == "__main__":
    main()
