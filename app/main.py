import os
import shutil
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv, set_key

from app.core.security import get_api_key
from app.schemas import ChatRequest, BatchIngestLogRequest, UpdateApiKeyRequest
from app.services.rag_service import rag_service
from app.services.chroma_service import chroma_service

load_dotenv()

app = FastAPI(title="ArandanoIRT-ML RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "API RAG funcionando correctamente."}

@app.post("/chat", dependencies=[Depends(get_api_key)])
def chat_endpoint(request: ChatRequest):
    try:
        result = rag_service.process_chat(request.question, request.iot_context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest-logs", dependencies=[Depends(get_api_key)])
def ingest_logs_endpoint(request: BatchIngestLogRequest):
    try:
        ids = [log.observation_id for log in request.logs]
        texts = [log.text_content for log in request.logs]
        metadatas = [log.metadata for log in request.logs]
        
        chroma_service.ingest_logs_batch(ids=ids, texts=texts, metadatas=metadatas)
        return {"status": "success", "message": f"{len(request.logs)} logs vectorizados correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-papers", dependencies=[Depends(get_api_key)])
async def update_papers_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .zip")
        
    temp_file = f"/tmp/{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        success = chroma_service.replace_papers_db(temp_file)
        if success:
            return {"status": "success", "message": "Base de datos ChromaDB actualizada exitosamente."}
        else:
            raise HTTPException(status_code=500, detail="Fallo al reemplazar la base de datos.")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

@app.get("/export-db", dependencies=[Depends(get_api_key)])
def export_db_endpoint():
    try:
        zip_path = chroma_service.export_db_zip()
        return FileResponse(
            path=zip_path,
            filename="chroma_db_export.zip",
            media_type="application/zip"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-api-key", dependencies=[Depends(get_api_key)])
def update_api_key_endpoint(request: UpdateApiKeyRequest):
    try:
        # Actualiza en la sesión actual
        os.environ["GOOGLE_API_KEY"] = request.api_key
        # Actualiza el archivo .env para persistencia
        set_key(".env", "GOOGLE_API_KEY", request.api_key)
        
        return {"status": "success", "message": "API Key de Gemini actualizada correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
