import os
import shutil
import zipfile
import tempfile
import logging
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

logger = logging.getLogger(__name__)

class ChromaService:
    def __init__(self):
        self.base_directory = os.getenv("CHROMA_DB_BASE", "./chroma_db")
        self.papers_persist_directory = os.getenv("CHROMA_DB_PAPERS", os.path.join(self.base_directory, "papers"))
        self.logs_persist_directory = os.getenv("CHROMA_DB_LOGS", os.path.join(self.base_directory, "logs"))
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        logger.info(f"Directorio base ChromaDB: {self.base_directory}")
        logger.info(f"Directorio papers: {self.papers_persist_directory} (existe: {os.path.exists(self.papers_persist_directory)})")
        logger.info(f"Directorio logs: {self.logs_persist_directory} (existe: {os.path.exists(self.logs_persist_directory)})")
        
        # Listar archivos en papers para verificar que el DB existe
        if os.path.exists(self.papers_persist_directory):
            papers_files = os.listdir(self.papers_persist_directory)
            logger.info(f"Archivos en papers/: {papers_files}")
        else:
            logger.warning(f"¡ADVERTENCIA! El directorio de papers NO existe: {self.papers_persist_directory}")
        
        logger.info(f"Dispositivo para embeddings: {self.device}")
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': self.device},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Load clients/collections
        self.papers_collection_name = "papers_expertos"
        self.logs_collection_name = "bitacoras_usuario"
        self._load_collections()

    def _load_collections(self):
        self.papers_store = Chroma(
            collection_name=self.papers_collection_name,
            persist_directory=self.papers_persist_directory,
            embedding_function=self.embeddings
        )
        
        self.logs_store = Chroma(
            collection_name=self.logs_collection_name,
            persist_directory=self.logs_persist_directory,
            embedding_function=self.embeddings
        )
        
        # Contar documentos en cada colección
        try:
            papers_count = self.papers_store._collection.count()
            logger.info(f"Colección '{self.papers_collection_name}' cargada: {papers_count} documentos")
        except Exception as e:
            logger.error(f"Error contando documentos de papers: {e}")
            
        try:
            logs_count = self.logs_store._collection.count()
            logger.info(f"Colección '{self.logs_collection_name}' cargada: {logs_count} documentos")
        except Exception as e:
            logger.error(f"Error contando documentos de logs: {e}")

    def reload_collections(self):
        """Force reload of the collections after an update"""
        self._load_collections()

    def get_papers_retriever(self, k=5):
        return self.papers_store.as_retriever(search_kwargs={"k": k})

    def get_logs_retriever(self, k=3):
        return self.logs_store.as_retriever(search_kwargs={"k": k})

    def ingest_logs_batch(self, ids: list[str], texts: list[str], metadatas: list[dict | None]):
        if not (len(ids) == len(texts) == len(metadatas)):
            raise ValueError("Las listas ids, texts y metadatas deben tener exactamente la misma longitud.")
            
        for i, meta in enumerate(metadatas):
            if meta is None:
                metadatas[i] = {}
            metadatas[i]["observation_id"] = ids[i]
        
        self.logs_store.add_texts(
            texts=texts,
            metadatas=metadatas,
            ids=ids
        )
        if hasattr(self.logs_store, 'persist'):
            self.logs_store.persist()

    def export_db_zip(self) -> str:
        """
        Comprime el directorio padre (chroma_db) en un archivo temporal .zip y retorna la ruta.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            zip_path = tmp.name
            
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', self.base_directory)
        return zip_path

    def replace_papers_db(self, zip_filepath: str):
        """
        Reemplaza la colección de papers con el contenido de un archivo ZIP.
        """
        import uuid
        import sqlite3
        temp_extract_dir = f"/tmp/temp_extract_{uuid.uuid4().hex}"
        
        try:
            with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
                for member in zip_ref.infolist():
                    # Check for symlinks (file type mask 0o170000, symlink type 0o120000)
                    unix_mode = member.external_attr >> 16
                    if unix_mode != 0 and (unix_mode & 0o170000) == 0o120000:
                        raise ValueError(f"Enlaces simbólicos (symlinks) no permitidos en el ZIP: {member.filename}")
                    
                    target_path = os.path.abspath(os.path.join(temp_extract_dir, member.filename))
                    if not target_path.startswith(os.path.abspath(temp_extract_dir)):
                        raise ValueError(f"Vulnerabilidad Zip Slip detectada en archivo: {member.filename}")
                    zip_ref.extract(member, temp_extract_dir)
            
            logger.info(f"Archivos extraídos en temp: {os.listdir(temp_extract_dir)}")
            
            candidate_dirs = [
                os.path.join(temp_extract_dir, "papers"),
                os.path.join(temp_extract_dir, "chroma_db", "papers"),
            ]
            matching_dirs = [
                candidate_dir
                for candidate_dir in candidate_dirs
                if os.path.isfile(os.path.join(candidate_dir, "chroma.sqlite3"))
            ]
            if not matching_dirs:
                raise ValueError(
                    "Invalid papers DB ZIP structure. Expected 'papers/chroma.sqlite3' "
                    "or 'chroma_db/papers/chroma.sqlite3'."
                )
            if len(matching_dirs) > 1:
                raise ValueError(
                    "Ambiguous papers DB ZIP structure. Multiple valid papers DB "
                    "directories were found."
                )
            db_source_dir = matching_dirs[0]
            logger.info(f"Directorio fuente encontrado: {db_source_dir}")
            logger.info(f"Archivos en fuente: {os.listdir(db_source_dir)}")
            
            # Diagnóstico: consultar directamente el sqlite de la fuente
            src_sqlite = os.path.join(db_source_dir, "chroma.sqlite3")
            try:
                conn = sqlite3.connect(src_sqlite)
                tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                logger.info(f"Tablas en sqlite fuente: {tables}")
                if "collections" in tables:
                    cols = conn.execute("SELECT id, name FROM collections").fetchall()
                    logger.info(f"Colecciones en sqlite fuente: {cols}")
                if "embeddings" in tables:
                    count = conn.execute("SELECT count(*) FROM embeddings").fetchone()[0]
                    logger.info(f"Embeddings en sqlite fuente: {count}")
                elif "embedding_fulltext_search" in tables:
                    # Chroma v0.4+ uses different table names
                    for t in tables:
                        try:
                            count = conn.execute(f"SELECT count(*) FROM [{t}]").fetchone()[0]
                            if count > 0:
                                logger.info(f"Tabla '{t}': {count} filas")
                        except Exception:
                            pass
                conn.close()
            except Exception as e:
                logger.error(f"Error al inspeccionar sqlite fuente: {e}")
            
            if os.path.exists(self.papers_persist_directory):
                shutil.rmtree(self.papers_persist_directory)
                
            shutil.copytree(db_source_dir, self.papers_persist_directory)
            logger.info(f"Archivos copiados a destino: {os.listdir(self.papers_persist_directory)}")
            
            self.reload_collections()
            return True
            
        finally:
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)

# Singleton instance
chroma_service = ChromaService()
