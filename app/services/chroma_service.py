import os
import shutil
import zipfile
import tempfile
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

class ChromaService:
    def __init__(self):
        self.papers_persist_directory = os.getenv("CHROMA_DB_PAPERS", "./chroma_db/papers")
        self.logs_persist_directory = os.getenv("CHROMA_DB_LOGS", "./chroma_db/logs")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
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
            
        base_dir = os.path.dirname(self.papers_persist_directory)
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', base_dir)
        return zip_path

    def replace_papers_db(self, zip_filepath: str):
        """
        Reemplaza la colección de papers con el contenido de un archivo ZIP.
        """
        import uuid
        temp_extract_dir = f"/tmp/temp_extract_{uuid.uuid4().hex}"
        
        try:
            with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    target_path = os.path.abspath(os.path.join(temp_extract_dir, member))
                    if not target_path.startswith(os.path.abspath(temp_extract_dir)):
                        raise ValueError(f"Zip slip vulnerability detected in file: {member}")
                    zip_ref.extract(member, temp_extract_dir)
            
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
            
            if os.path.exists(self.papers_persist_directory):
                shutil.rmtree(self.papers_persist_directory)
                
            shutil.copytree(db_source_dir, self.papers_persist_directory)
            
            self.reload_collections()
            return True
            
        finally:
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)

# Singleton instance
chroma_service = ChromaService()
